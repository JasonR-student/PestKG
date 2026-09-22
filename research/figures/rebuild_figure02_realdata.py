"""Redraw figure_02 (single-site APVMA) from the REAL released sample data.

Goals vs the shipped figure:
  * use the real labels / properties from sample/nodes.csv + edges.csv (no invented
    "Approved use pattern" label; show the real registration dates);
  * stop drawing 48 anonymous decorative dots -- group them into real categories and
    render a stacked composition + a tight 6x8 dot grid so the right side is filled;
  * remove the large blank bottom-right.
Outputs figure_02_single_site_apvma_redrawn.{png,svg,pdf} beside the original.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = PROJECT_ROOT / "data" / "releases" / "2026.08.3_federated" / "sample"
OUTPUT = PROJECT_ROOT / "artifacts" / "research" / "figures" / "output"
FORTIN_ID = "AU:PRODUCT:7feed95ebf8a4d6f19180bcc"

INK = "#17212B"
MUTED = "#627080"
PAPER = "#FFFFFF"
PANEL = "#F4F7F8"

C_SOURCE = "#6F8192"
C_COUNTRY = "#4E8D7C"
C_REG = "#7867A8"
C_PRODUCT = "#D88945"
C_USE = "#C85C5C"
C_AI = "#2C8E9E"

# real crop-category colours (harmonious greens / ochre / steel)
CAT_COLORS = ["#3E7C4F", "#86A84E", "#C2A85E", "#5F8FA3"]
CAT_NAMES = [
    "Perennial fruit & nut crops",
    "Field & row crops",
    "Non-agricultural & land areas",
    "Application methods",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def neighborhood(product_id: str):
    nodes = read_csv(SAMPLE / "nodes.csv")
    edges = read_csv(SAMPLE / "edges.csv")
    by_id = {n["id"]: n for n in nodes}
    seen = {product_id}
    frontier = {product_id}
    kept = []
    for _ in range(3):
        nxt = set()
        for e in edges:
            if e["start_id"] in frontier or e["end_id"] in frontier:
                kept.append(e)
                for nid in (e["start_id"], e["end_id"]):
                    if nid not in seen:
                        seen.add(nid)
                        nxt.add(nid)
        frontier = nxt
    return by_id, kept


def classify(label: str) -> int:
    u = label.upper()
    if "OVER 3 YEARS OLD" in u or "VINEYARD" in u:
        return 0
    if any(k in u for k in ("COTTON", "CHICKPEA", "BEAN", "PEANUT", "SOYBEAN",
                            "ONION", "SUGAR CANE", "PASTURE")):
        return 1
    if any(k in u for k in ("FOLIAR", "STEM INJECTION", "CUT STUMP")):
        return 3
    return 2  # non-agricultural / land / forest / buildings / nursery


def node_box(ax, xy, title, subtitle_lines, color, width=1.9, height=0.78, title_size=9.0):
    x, y = xy
    ax.add_patch(FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.09",
        facecolor=PAPER, edgecolor=color, linewidth=1.3, zorder=3))
    ax.add_patch(Rectangle((x - width / 2, y + height / 2 - 0.14), width, 0.14,
                           color=color, zorder=4))
    ax.text(x, y + 0.07, title, ha="center", va="center", fontsize=title_size,
            fontweight="bold", color=INK, zorder=5)
    n = len(subtitle_lines)
    for i, line in enumerate(subtitle_lines):
        dy = -0.13 - i * 0.16
        ax.text(x, y + dy, line, ha="center", va="center", fontsize=7.2,
                color=MUTED, zorder=5)


def arrow(ax, a, b, color="#9AA7B2", label=None, label_xy=None, dashed=False, lw=1.1):
    ls = (0, (3, 2)) if dashed else "-"
    ax.add_patch(FancyArrowPatch(
        a, b, arrowstyle="-|>", mutation_scale=11, linewidth=lw, color=color,
        linestyle=ls, shrinkA=9, shrinkB=9, zorder=2,
        connectionstyle="arc3,rad=0.0"))
    if label:
        lx, ly = label_xy or ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        ax.text(lx, ly, label, fontsize=7.0, color=MUTED, ha="center", va="center",
                bbox=dict(facecolor=PAPER, edgecolor="none", pad=1.2), zorder=6)


def main():
    by_id, edges = neighborhood(FORTIN_ID)
    reg = next(n for n in by_id.values() if n["type"] == "Registration" and n["label_en"] == "84962")
    country = next(n for n in by_id.values() if n["type"] == "CountryJurisdiction")
    product = by_id[FORTIN_ID]
    use = next(n for n in by_id.values() if n["type"] == "RegistrationUse")
    ai = next(
        by_id[e["end_id"]]
        for e in edges
        if e["predicate"] == "hasActiveIngredient" and e["start_id"] == use["id"]
    )
    crops = sorted({
        by_id[e["end_id"]]["label_en"]
        for e in edges
        if e["predicate"] == "registeredForCrop" and e["start_id"] == use["id"]
    })
    assert len(crops) == 48, len(crops)

    # real registration dates from properties_json
    props = json.loads(reg.get("properties_json") or "{}")
    reg_date = props.get("registration_date", "")
    exp_date = props.get("expiry_date", "")
    # sibling registration 56708 (real row under Australia; not linked to Fortin in this sample)
    reg56 = next(n for n in by_id.values() if n["type"] == "Registration" and n["label_en"] == "56708")
    props56 = json.loads(reg56.get("properties_json") or "{}")

    buckets = [[] for _ in range(4)]
    for c in crops:
        buckets[classify(c)].append(c)
    counts = [len(b) for b in buckets]
    assert sum(counts) == 48, counts

    fig = plt.figure(figsize=(12.6, 6.7))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_facecolor(PAPER)

    # ---------- left: ingestion chain ----------
    ax.text(0.25, 6.78, "One official website to a jurisdictional knowledge graph",
            fontsize=12.5, fontweight="bold", color=INK, ha="left", va="center")
    ax.text(-0.12, 6.9, "a", fontsize=13, fontweight="bold", color=INK, ha="right")

    apvma = (1.75, 6.0)
    aus = (4.55, 6.0)
    regc = (4.55, 4.35)
    reg56_xy = (2.15, 4.35)
    fortin = (7.35, 5.25)
    use_c = (7.35, 3.85)
    ai_c = (7.35, 2.25)

    node_box(ax, apvma, "APVMA / PubCRIS", ["official source system"], C_SOURCE, width=2.15)
    node_box(ax, aus, country["label_en"], ["CountryJurisdiction"], C_COUNTRY, width=1.8)
    node_box(ax, regc, "Registration 84962",
             [f"Registered {reg_date} · expires {exp_date}", "Registered – Current"],
             C_REG, width=2.35, height=1.0)
    node_box(ax, reg56_xy, "Registration 56708",
             [f"Registered {props56.get('registration_date','')} · expires {props56.get('expiry_date','')}",
              "sibling registration"],
             C_REG, width=2.0, height=0.95)
    node_box(ax, fortin, product["label_en"], ["PesticideProduct"], C_PRODUCT, width=2.0)
    node_box(ax, use_c, "Approved use", ["official pair asserted", "RegistrationUse"],
             C_USE, width=2.0, height=0.95)
    node_box(ax, ai_c, ai["label_en"], ["ActiveIngredientLocal"], C_AI, width=2.0)

    arrow(ax, apvma, aus, color="#9AA7B2", label="source provenance", dashed=True, lw=1.0)
    arrow(ax, aus, regc, label="hasRegistration", label_xy=(4.55, 5.18))
    arrow(ax, aus, reg56_xy, color="#B9C2CB", dashed=True, lw=0.9)
    arrow(ax, regc, fortin, label="hasProduct", label_xy=(5.95, 4.95))
    arrow(ax, regc, use_c, label="hasRegistrationUse", label_xy=(5.95, 3.95))
    arrow(ax, use_c, fortin, label="usesProduct", label_xy=(7.35, 4.55))
    arrow(ax, use_c, ai_c, label="hasActiveIngredient", label_xy=(7.35, 3.05))

    # ---------- right: crop-context panel (fills the former blank area) ----------
    ax.add_patch(FancyBboxPatch((8.25, 0.95), 4.75, 5.75,
                               boxstyle="round,pad=0.02,rounding_size=0.12",
                               facecolor=PANEL, edgecolor="none", zorder=0))
    ax.text(8.5, 6.42, "48 registered crop contexts", fontsize=10.5,
            fontweight="bold", color=INK, ha="left", va="center")
    ax.text(8.5, 6.12, "per the approved use of registration 84962",
            fontsize=7.6, color=MUTED, ha="left", va="center")

    # stacked composition bar
    bx0, bx1, by, bh = 8.5, 12.75, 5.55, 0.3
    total = sum(counts)
    cx = bx0
    for i, n in enumerate(counts):
        w = (bx1 - bx0) * n / total
        ax.add_patch(Rectangle((cx, by), w, bh, facecolor=CAT_COLORS[i],
                               edgecolor=PAPER, linewidth=1.2, zorder=2))
        ax.text(cx + w / 2, by + bh / 2, f"{n}", ha="center", va="center",
                color=PAPER, fontsize=8.5, fontweight="bold", zorder=3)
        cx += w

    # tight 6x8 dot grid = 48 glyphs, coloured by category (grouped by bucket)
    order = sorted(range(48), key=lambda k: classify(crops[k]))
    cols, rows = 8, 6
    gx0, gy0, gdx, gdy = 8.62, 4.85, 0.53, 0.5
    pos_of = {k: pos for pos, k in enumerate(order)}
    for pos, k in enumerate(order):
        r = pos // cols
        c = pos % cols
        x = gx0 + c * gdx
        y = gy0 - r * gdy
        cat = classify(crops[k])
        ax.scatter([x], [y], s=120, color=CAT_COLORS[cat], edgecolor=PAPER,
                   linewidth=1.0, zorder=3)

    # name a handful of representative crops (real labels) on their dots
    named_crops = {
        "BANANA, OVER 3 YEARS OLD": "Banana",
        "CITRUS OVER 3 YEARS OLD": "Citrus",
        "MANGO, OVER 3 YEARS OLD": "Mango",
        "COTTON": "Cotton",
        "SOYBEAN": "Soybean",
        "SUGAR CANE": "Sugar cane",
        "NAVY BEAN": "Navy bean",
        "PASTURE": "Pasture",
    }
    for full, short in named_crops.items():
        if full not in crops:
            continue
        k = crops.index(full)
        pos = pos_of[k]
        c = pos % cols
        x = gx0 + c * gdx
        y = gy0 - (pos // cols) * gdy
        halign = "left" if c <= 4 else "right"
        tx = x + 0.16 if halign == "left" else x - 0.16
        ax.text(tx, y, short, fontsize=6.6, va="center", ha=halign,
                color=INK, zorder=6,
                bbox=dict(facecolor=PAPER, edgecolor="none", pad=0.8))

    # legend (bottom of panel)
    lx, ly = 8.55, 1.55
    for i in range(4):
        row = i // 2
        col = i % 2
        xx = lx + col * 2.25
        yy = ly - row * 0.42
        ax.scatter([xx], [yy], s=70, color=CAT_COLORS[i], edgecolor=PAPER, linewidth=0.8, zorder=3)
        short = CAT_NAMES[i] + f"  ({counts[i]})"
        ax.text(xx + 0.18, yy, short, fontsize=7.6, color=INK, va="center", ha="left")

    # ---------- bottom provenance strip ----------
    ax.text(0.35, 0.35,
            "APVMA PubCRIS  →  PestKG release 2026.08.3_federated    source_record_id retained    official pair asserted",
            fontsize=7.6, color=MUTED, ha="left", va="center")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = "figure_02_single_site_apvma_redrawn"
    for ext in ("svg", "pdf"):
        fig.savefig(OUTPUT / f"{stem}.{ext}", bbox_inches="tight")
    fig.savefig(OUTPUT / f"{stem}.png", dpi=600, bbox_inches="tight")
    print("wrote", stem, "| crops by category:", dict(zip(CAT_NAMES, counts)),
          "| total", total)


if __name__ == "__main__":
    main()
