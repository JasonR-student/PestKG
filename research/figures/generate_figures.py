from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from neo4j import GraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASE_ID = "2026.08.3_federated"
RELEASE_ROOT = PROJECT_ROOT / "data" / "releases" / RELEASE_ID
SAMPLE_ROOT = RELEASE_ROOT / "sample"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "research" / "figures" / "output"
FORTIN_PRODUCT_ID = "AU:PRODUCT:7feed95ebf8a4d6f19180bcc"

INK = "#17212B"
MUTED = "#627080"
GRID = "#D9E0E6"
PAPER = "#FFFFFF"
PALETTE = {
    "RegulatoryAgency": "#3A6EA5",
    "CountryJurisdiction": "#4E8D7C",
    "Registration": "#7867A8",
    "PesticideProduct": "#D88945",
    "RegistrationUse": "#C85C5C",
    "ActiveIngredientLocal": "#2C8E9E",
    "CropLocal": "#86A84E",
    "TargetLocal": "#C49A3A",
    "FormulationLocal": "#8D6B5D",
    "CHEBI": "#2C8E9E",
    "AGROVOC": "#86A84E",
}


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Noto Sans SC",
                "Noto Sans CJK SC",
                "Microsoft YaHei",
                "Microsoft JhengHei",
                "Yu Gothic",
                "Malgun Gothic",
                "Arial",
                "DejaVu Sans",
            ],
            "font.size": 8,
            "axes.titlesize": 10,
            "axes.labelsize": 8,
            "axes.edgecolor": GRID,
            "axes.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "savefig.facecolor": PAPER,
        }
    )


def jurisdiction_font(jurisdiction: str) -> str:
    available = {font.name for font in font_manager.fontManager.ttflist}
    candidates = {
        "TW": ["Noto Sans SC", "Noto Sans CJK SC", "Microsoft JhengHei"],
        "CN": ["Noto Sans SC", "Noto Sans CJK SC", "Microsoft YaHei"],
        "KR": ["Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK SC"],
        "JP": ["Yu Gothic", "Noto Sans CJK JP", "Noto Sans CJK SC"],
    }
    return next((name for name in candidates[jurisdiction] if name in available), "DejaVu Sans")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for suffix in ("svg", "pdf"):
        fig.savefig(OUTPUT_ROOT / f"{stem}.{suffix}", bbox_inches="tight")
    fig.savefig(OUTPUT_ROOT / f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.03,
        1.03,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="bottom",
        ha="right",
    )


def short_label(value: str, width: int = 24) -> str:
    value = " ".join(value.split())
    return "\n".join(textwrap.wrap(value, width=width, break_long_words=False))


def draw_dataset_landscape(axs: Iterable[plt.Axes], compact: bool = False) -> None:
    countries = json.loads((RELEASE_ROOT / "countries.json").read_text(encoding="utf-8"))
    release = json.loads((RELEASE_ROOT / "release.json").read_text(encoding="utf-8"))
    ax_records, ax_scale, ax_coverage = list(axs)
    ordered = sorted(countries, key=lambda row: row["source_rows"], reverse=True)
    labels = [row["jurisdiction"] for row in ordered]
    records = np.array([row["source_rows"] for row in ordered])
    colors = ["#2C8E9E" if code in {"CN", "TW", "JP", "KR"} else "#6F8192" for code in labels]
    y = np.arange(len(labels))
    ax_records.barh(y, records / 1000, color=colors, height=0.66)
    ax_records.set_yticks(y, labels)
    ax_records.invert_yaxis()
    ax_records.set_xlabel("Source records (thousands)")
    ax_records.set_title("Official-source coverage", loc="left", fontweight="bold")
    ax_records.grid(axis="x", color=GRID, linewidth=0.5)
    ax_records.set_axisbelow(True)
    for index, value in enumerate(records):
        if index < (5 if compact else len(records)):
            ax_records.text(value / 1000 + 3, index, f"{value:,}", va="center", fontsize=6.5, color=MUTED)

    nodes = np.array([row["nodes"] for row in countries])
    edges = np.array([row["edges"] for row in countries])
    sizes = np.clip(np.sqrt(np.array([row["source_rows"] for row in countries])) * 1.4, 22, 230)
    ax_scale.scatter(nodes, edges, s=sizes, color="#D88945", alpha=0.82, edgecolor=PAPER, linewidth=0.7)
    label_offsets = {
        "US": (-15, 8),
        "TW": (7, 5),
        "JP": (-17, 7),
        "KR": (7, 5),
        "CN": (7, 5),
        "AU": (6, 5),
        "NZ": (6, -10),
        "NL": (6, 6),
        "IE": (5, 5),
        "GB": (5, -9),
        "GB-NI": (6, 5),
        "HU": (-16, 5),
    }
    for row in countries:
        ax_scale.annotate(
            row["jurisdiction"],
            (row["nodes"], row["edges"]),
            xytext=label_offsets[row["jurisdiction"]],
            textcoords="offset points",
            fontsize=6.5,
            color=INK,
        )
    ax_scale.set_xscale("log")
    ax_scale.set_yscale("log")
    ax_scale.set_xlabel("Country graph nodes")
    ax_scale.set_ylabel("Country graph relationships")
    ax_scale.set_title("Graph scale", loc="left", fontweight="bold")
    ax_scale.grid(color=GRID, linewidth=0.5, which="both")
    ax_scale.set_axisbelow(True)

    fields = ["crop_source", "target_source", "active_source", "formulation_source"]
    field_labels = ["Crop", "Target", "Active ingredient", "Formulation"]
    matrix = np.array(
        [[float(row["coverage"].get(field) or 0) for field in fields] for row in ordered]
    )
    image = ax_coverage.imshow(matrix, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax_coverage.set_yticks(np.arange(len(labels)), labels)
    ax_coverage.set_xticks(np.arange(len(fields)), field_labels, rotation=35, ha="right")
    ax_coverage.set_title("Source-field completeness", loc="left", fontweight="bold")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if not compact or i < 6:
                ax_coverage.text(
                    j,
                    i,
                    f"{matrix[i, j] * 100:.0f}",
                    ha="center",
                    va="center",
                    fontsize=5.5,
                    color=PAPER if matrix[i, j] > 0.58 else INK,
                )
    colorbar = ax_coverage.figure.colorbar(image, ax=ax_coverage, fraction=0.045, pad=0.03)
    colorbar.set_label("Completeness")
    inventory = release["inventory"]
    ax_scale.text(
        0.02,
        0.98,
        f"{inventory['jurisdictions']} jurisdictions\n{inventory['country_nodes']:,} nodes\n{inventory['country_edges']:,} relationships",
        transform=ax_scale.transAxes,
        va="top",
        fontsize=6.8,
        color=MUTED,
        bbox={"facecolor": PAPER, "edgecolor": GRID, "boxstyle": "round,pad=0.35"},
    )


def file_neighborhood(product_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = read_csv(SAMPLE_ROOT / "nodes.csv")
    edges = read_csv(SAMPLE_ROOT / "edges.csv")
    node_by_id = {node["id"]: node for node in nodes}
    seen = {product_id}
    frontier = {product_id}
    selected_edges: list[dict[str, Any]] = []
    for _ in range(3):
        next_frontier: set[str] = set()
        for edge in edges:
            if edge["start_id"] in frontier or edge["end_id"] in frontier:
                if edge not in selected_edges:
                    selected_edges.append(edge)
                for node_id in (edge["start_id"], edge["end_id"]):
                    if node_id not in seen:
                        seen.add(node_id)
                        next_frontier.add(node_id)
        frontier = next_frontier
    return [node_by_id[node_id] for node_id in seen if node_id in node_by_id], selected_edges


def neo4j_neighborhood(
    uri: str, user: str, password: str, product_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    query = """
    MATCH p=(root:Entity {nodeId: $product_id})-[*1..3]-(neighbor:Entity)
    WITH p LIMIT 400
    UNWIND nodes(p) AS node
    UNWIND relationships(p) AS rel
    RETURN collect(DISTINCT node) AS nodes, collect(DISTINCT rel) AS relationships
    """
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        record = driver.execute_query(query, product_id=product_id).records[0]
    nodes = []
    for node in record["nodes"]:
        properties = dict(node)
        nodes.append(
            {
                "id": properties.get("nodeId", ""),
                "type": next((label for label in node.labels if label not in {"Entity", "PaperSample"}), "Entity"),
                "label_en": properties.get("labelEnglish", ""),
                "label_original": properties.get("labelOriginal", ""),
                "jurisdiction": properties.get("jurisdiction", ""),
                "source_url": properties.get("sourceUrl", ""),
            }
        )
    edges = []
    for rel in record["relationships"]:
        edges.append(
            {
                "id": rel.get("relationshipId", rel.element_id),
                "start_id": rel.start_node.get("nodeId", ""),
                "predicate": rel.type,
                "end_id": rel.end_node.get("nodeId", ""),
            }
        )
    return nodes, edges


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], **kwargs: Any) -> None:
    defaults = {
        "arrowstyle": "-|>",
        "mutation_scale": 7,
        "linewidth": 0.75,
        "color": "#9AA7B2",
        "zorder": 1,
        "shrinkA": 6,
        "shrinkB": 6,
    }
    defaults.update(kwargs)
    ax.add_patch(FancyArrowPatch(start, end, **defaults))


def node_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    title: str,
    subtitle: str,
    color: str,
    width: float = 1.65,
    height: float = 0.7,
    fontsize: float = 7,
    fontfamily: str | None = None,
) -> None:
    x, y = xy
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=PAPER,
        edgecolor=color,
        linewidth=1.15,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.add_patch(Rectangle((x - width / 2, y + height / 2 - 0.12), width, 0.12, color=color, zorder=4))
    ax.text(
        x,
        y + 0.10,
        title,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        fontfamily=fontfamily,
        zorder=5,
    )
    ax.text(x, y - 0.13, subtitle, ha="center", va="center", fontsize=fontsize - 1.3, color=MUTED, zorder=5)


def draw_single_site(
    ax: plt.Axes,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    compact: bool = False,
) -> None:
    ax.set_xlim(-0.3, 10.2)
    ax.set_ylim(-3.0, 3.2)
    ax.axis("off")
    ax.set_title("One official website to a jurisdictional knowledge graph", loc="left", fontweight="bold")
    by_id = {node["id"]: node for node in nodes}
    types = defaultdict(list)
    for node in nodes:
        types[node["type"]].append(node)
    country = next(node for node in types["CountryJurisdiction"] if node["jurisdiction"] == "AU")
    registration = next(node for node in types["Registration"] if node["label_en"] == "84962")
    product = by_id[FORTIN_PRODUCT_ID]
    use = next(
        by_id[edge["start_id"]]
        for edge in edges
        if edge["predicate"] == "usesProduct" and edge["end_id"] == FORTIN_PRODUCT_ID
    )
    ingredient = next(
        by_id[edge["end_id"]]
        for edge in edges
        if edge["predicate"] == "hasActiveIngredient" and edge["start_id"] == use["id"]
    )
    crop_nodes = [
        by_id[edge["end_id"]]
        for edge in edges
        if edge["predicate"] == "registeredForCrop" and edge["start_id"] == use["id"]
    ]
    crop_nodes = sorted(crop_nodes, key=lambda node: node["label_en"])

    website_xy = (1.25, 2.35)
    country_xy = (3.65, 2.35)
    reg_xy = (3.65, 0.85)
    product_xy = (6.15, 1.5)
    use_xy = (6.15, 0.1)
    ingredient_xy = (6.15, -1.55)
    node_box(ax, website_xy, "APVMA / PubCRIS", "official source system", "#6F8192", width=1.9)
    node_box(ax, country_xy, country["label_en"], "CountryJurisdiction", PALETTE["CountryJurisdiction"], width=1.6)
    node_box(ax, reg_xy, f"Registration {registration['label_en']}", "Registered - Current", PALETTE["Registration"], width=1.7)
    node_box(ax, product_xy, product["label_en"], "PesticideProduct", PALETTE["PesticideProduct"], width=1.75)
    node_box(ax, use_xy, "Approved use pattern", "RegistrationUse", PALETTE["RegistrationUse"], width=1.75)
    node_box(ax, ingredient_xy, ingredient["label_en"], "ActiveIngredientLocal", PALETTE["ActiveIngredientLocal"], width=1.75)

    arrow(ax, website_xy, country_xy, linestyle=(0, (2, 2)), color="#7D8994")
    arrow(ax, country_xy, reg_xy)
    arrow(ax, reg_xy, product_xy)
    arrow(ax, reg_xy, use_xy)
    arrow(ax, use_xy, product_xy)
    arrow(ax, use_xy, ingredient_xy)
    if not compact:
        edge_labels = [
            ((2.45, 2.02), "source provenance"),
            ((3.88, 1.60), "hasRegistration"),
            ((5.02, 1.18), "hasProduct"),
            ((5.00, 0.34), "hasRegistrationUse"),
            ((6.48, 0.84), "usesProduct"),
            ((6.48, -0.75), "hasActiveIngredient"),
        ]
        for (x, y), label in edge_labels:
            ax.text(
                x,
                y,
                label,
                fontsize=5.8,
                color=MUTED,
                ha="center",
                bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 0.2},
                zorder=6,
            )

    angles = np.linspace(-1.22, 1.22, len(crop_nodes))
    crop_positions: dict[str, tuple[float, float]] = {}
    for node, angle_value in zip(crop_nodes, angles):
        position = (8.55 + 1.05 * math.cos(angle_value), 0.08 + 2.45 * math.sin(angle_value))
        crop_positions[node["id"]] = position
        arrow(ax, use_xy, position, linewidth=0.35, color="#C9D2D9", mutation_scale=4, shrinkB=3)
        ax.scatter(*position, s=13 if compact else 17, color=PALETTE["CropLocal"], edgecolor=PAPER, linewidth=0.4, zorder=3)

    priority = {
        "BANANA, OVER 3 YEARS OLD": "Banana",
        "CITRUS OVER 3 YEARS OLD": "Citrus",
        "COTTON": "Cotton",
        "MANGO, OVER 3 YEARS OLD": "Mango",
        "NAVY BEAN": "Navy bean",
        "PASTURE": "Pasture",
        "SOYBEAN": "Soybean",
        "SUGAR CANE": "Sugar cane",
    }
    if not compact:
        for node in crop_nodes:
            if node["label_en"] not in priority:
                continue
            x, y = crop_positions[node["id"]]
            ax.text(x + 0.12, y, priority[node["label_en"]], fontsize=5.6, va="center", color=INK)
    ax.text(9.04, 2.78, f"{len(crop_nodes)} registered crop contexts", ha="center", fontsize=6.6, color=MUTED)
    ax.text(
        0.35,
        -2.65,
        "Release 2026.08.3_federated  |  source_record_id retained  |  official_pair_asserted",
        fontsize=5.8,
        color=MUTED,
        ha="left",
    )


def select_alignment_rows() -> tuple[list[dict[str, str]], list[str]]:
    rows = read_csv(SAMPLE_ROOT / "comparisons" / "q1.csv")
    selected_ids = ["CHEBI:52492", "CHEBI:81760", "CHEBI:78780", "CHEBI:40909"]
    jurisdictions = ["TW", "CN", "KR", "JP"]
    selected = [
        row
        for row in rows
        if row["active_shared_id"] in selected_ids and row["jurisdiction"] in jurisdictions
    ]
    return selected, jurisdictions


def draw_federated(ax: plt.Axes, compact: bool = False) -> None:
    rows, jurisdictions = select_alignment_rows()
    ax.set_xlim(-0.3, 11.0)
    ax.set_ylim(-3.2, 3.25)
    ax.axis("off")
    ax.set_title("Federated projection through ChEBI and AGROVOC", loc="left", fontweight="bold")
    country_colors = {"TW": "#486F9C", "CN": "#93624C", "KR": "#75639A", "JP": "#4E8D7C"}
    y_by_country = {code: 2.15 - index * 1.42 for index, code in enumerate(jurisdictions)}
    crop_shared_id = rows[0]["crop_shared_id"]
    crop_shared_label = rows[0]["crop_label_en"]
    by_country_ai: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["jurisdiction"], row["active_shared_id"])
        if key not in by_country_ai or int(row["registration_use_count"]) > int(by_country_ai[key]["registration_use_count"]):
            by_country_ai[key] = row

    ax.add_patch(Rectangle((7.65, -3.0), 3.05, 5.95, facecolor="#F5F7F8", edgecolor="none", zorder=0))
    ax.text(7.9, 2.62, "EXTERNAL SEMANTIC LAYER", fontsize=6.5, fontweight="bold", color=MUTED)
    ax.text(0.05, 2.87, "JURISDICTION", fontsize=6.2, fontweight="bold", color=MUTED)
    ax.text(1.45, 2.87, "LOCAL REGULATORY ENTITIES", fontsize=6.2, fontweight="bold", color=MUTED)
    ax.text(5.25, 2.87, "SHARED IDENTIFIERS", fontsize=6.2, fontweight="bold", color=MUTED)

    crop_xy = (8.95, 2.0)
    node_box(ax, crop_xy, crop_shared_label.title(), crop_shared_id.rsplit("/", 1)[-1], PALETTE["AGROVOC"], width=2.15)
    ax.text(10.05, 2.55, "AGROVOC", fontsize=7.3, fontweight="bold", color=PALETTE["AGROVOC"], ha="right")

    active_ids = ["CHEBI:52492", "CHEBI:81760", "CHEBI:78780", "CHEBI:40909"]
    active_labels = {}
    for row in rows:
        active_labels.setdefault(row["active_shared_id"], row["active_ingredient_label_en"].title())
    active_y = {node_id: 0.72 - index * 0.9 for index, node_id in enumerate(active_ids)}
    for node_id in active_ids:
        node_box(ax, (8.95, active_y[node_id]), active_labels[node_id], node_id, PALETTE["CHEBI"], width=2.15, height=0.62, fontsize=6.5)
    ax.text(10.05, 1.18, "ChEBI", fontsize=7.3, fontweight="bold", color=PALETTE["CHEBI"], ha="right")

    for jurisdiction in jurisdictions:
        y = y_by_country[jurisdiction]
        ax.scatter(0.55, y, s=230 if not compact else 150, color=country_colors[jurisdiction], edgecolor=PAPER, linewidth=0.9, zorder=4)
        ax.text(0.55, y, jurisdiction, ha="center", va="center", color=PAPER, fontsize=7, fontweight="bold", zorder=5)
        country_rows = [row for row in rows if row["jurisdiction"] == jurisdiction]
        if not country_rows:
            continue
        crop_label = country_rows[0]["crop_local_labels"].split(" | ", 1)[0]
        crop_display = crop_label if not compact else f"{jurisdiction} local crop"
        crop_local_xy = (2.05, y + 0.35)
        local_font = jurisdiction_font(jurisdiction)
        node_box(
            ax,
            crop_local_xy,
            short_label(crop_display, 15),
            "CropLocal projection",
            PALETTE["CropLocal"],
            width=1.65,
            height=0.58,
            fontsize=6.2,
            fontfamily=local_font if not compact else None,
        )
        arrow(ax, (0.75, y), crop_local_xy, arrowstyle="-", color="#C4CCD3", linewidth=0.65, shrinkA=4, shrinkB=5)
        arrow(ax, crop_local_xy, crop_xy, linestyle=(0, (3, 2)), color=PALETTE["AGROVOC"], linewidth=0.75, mutation_scale=6)

        ai_rows = [by_country_ai[(jurisdiction, node_id)] for node_id in active_ids if (jurisdiction, node_id) in by_country_ai]
        if not ai_rows:
            continue
        offsets = np.linspace(-0.42, 0.34, len(ai_rows))
        for row, offset in zip(ai_rows, offsets):
            local_xy = (4.15, y + offset)
            local_label = short_label(
                row["active_ingredient_local_labels"].split(" | ", 1)[0], 18
            )
            ax.scatter(*local_xy, s=55 if not compact else 38, color=country_colors[jurisdiction], edgecolor=PAPER, linewidth=0.6, zorder=4)
            if not compact:
                ax.text(
                    4.02,
                    local_xy[1],
                    local_label,
                    ha="right",
                    va="center",
                    fontsize=5.5,
                    color=INK,
                    fontfamily=local_font,
                )
            shared_xy = (7.95, active_y[row["active_shared_id"]])
            arrow(ax, local_xy, shared_xy, linestyle=(0, (3, 2)), color="#6A98A2", linewidth=0.62, mutation_scale=5)
            if not compact:
                midpoint = ((local_xy[0] + shared_xy[0]) / 2, (local_xy[1] + shared_xy[1]) / 2)
                ax.text(*midpoint, row["registration_use_count"], fontsize=5.0, color=MUTED, ha="center")
    ax.text(
        4.95,
        -2.94,
        "Dashed edges: semantic alignment evidenced in Q1; labels on active-ingredient edges: registration-use count",
        fontsize=5.7,
        color=MUTED,
        ha="center",
    )


def figure_dataset_landscape() -> None:
    fig, axs = plt.subplots(1, 3, figsize=(11.6, 4.2), gridspec_kw={"width_ratios": [1.05, 1, 1.05]})
    draw_dataset_landscape(axs)
    for label, ax in zip(("a", "b", "c"), axs):
        panel_label(ax, label)
    fig.suptitle("PestKG release landscape", x=0.06, y=1.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(w_pad=2.1)
    save_figure(fig, "figure_01_dataset_landscape")


def figure_single_site(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(11.3, 6.2))
    draw_single_site(ax, nodes, edges)
    panel_label(ax, "a")
    fig.tight_layout()
    save_figure(fig, "figure_02_single_site_apvma")


def figure_federated() -> None:
    fig, ax = plt.subplots(figsize=(11.5, 6.0))
    draw_federated(ax)
    panel_label(ax, "b")
    fig.tight_layout()
    save_figure(fig, "figure_03_federated_chebi_agrovoc")


def figure_storyboard(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    fig = plt.figure(figsize=(15.8, 8.2))
    grid = fig.add_gridspec(2, 6, height_ratios=[1, 1.18], hspace=0.55, wspace=0.9)
    ax_records = fig.add_subplot(grid[0, 0:2])
    ax_scale = fig.add_subplot(grid[0, 2:4])
    ax_coverage = fig.add_subplot(grid[0, 4:6])
    draw_dataset_landscape((ax_records, ax_scale, ax_coverage), compact=True)
    panel_label(ax_records, "a")
    ax_single = fig.add_subplot(grid[1, 0:3])
    draw_single_site(ax_single, nodes, edges, compact=True)
    panel_label(ax_single, "b")
    ax_federated = fig.add_subplot(grid[1, 3:6])
    draw_federated(ax_federated, compact=True)
    panel_label(ax_federated, "c")
    fig.suptitle(
        "From official pesticide registers to a federated semantic knowledge graph",
        x=0.04,
        y=0.995,
        ha="left",
        fontsize=12,
        fontweight="bold",
    )
    save_figure(fig, "figure_04_pestkg_storyboard")


def write_captions(source_mode: str) -> None:
    captions = f"""# Figure captions

## Figure 1 | PestKG release landscape

Distribution of official-source records, graph scale, and source-field completeness across 12 jurisdictions in PestKG release `{RELEASE_ID}`. Bubble area in panel b scales with the square root of source-record count. Empty official fields are treated as unavailable, not as translation failures.

## Figure 2 | APVMA single-website knowledge graph

Bounded subgraph centered on APVMA registration 84962 (Fortin Herbicide). The graph preserves the country-specific registration, product, registration-use, active-ingredient, and crop nodes. All 48 crop contexts present in the released sample are drawn; eight representative crop labels are shown to maintain legibility. Dotted provenance edges are visual annotations and are not PestKG predicates. Graph source mode: `{source_mode}`.

## Figure 3 | PestKG federation through ChEBI and AGROVOC

Projection of banana-related registration-use results from jurisdictions represented in the released Q1 comparison table. Country-local crop and active-ingredient labels remain separate and connect to shared AGROVOC and ChEBI identifiers through semantic-alignment evidence. Dashed active-ingredient edges are annotated with registration-use counts. Because the Q1 table does not retain the row-level predicate, the figure does not infer whether a specific alignment is `exactMatch` or `lexicalAlignment`.

## Figure 4 | Integrated PestKG workflow

Combined overview linking release-scale statistics, an official-site jurisdictional subgraph, and cross-jurisdiction semantic federation. This multi-panel version is intended as a main-text overview; Figures 1-3 provide higher-resolution standalone alternatives.
"""
    (OUTPUT_ROOT / "CAPTIONS.md").write_text(captions, encoding="utf-8")


def write_manifest(source_mode: str) -> None:
    input_paths = [
        RELEASE_ROOT / "release.json",
        RELEASE_ROOT / "countries.json",
        SAMPLE_ROOT / "nodes.csv",
        SAMPLE_ROOT / "edges.csv",
        SAMPLE_ROOT / "comparisons" / "q1.csv",
    ]
    figures = []
    for path in sorted(OUTPUT_ROOT.glob("figure_*.*")):
        figures.append(
            {
                "file": path.name,
                "format": path.suffix.lstrip("."),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "png_dpi": 600 if path.suffix == ".png" else None,
            }
        )
    manifest = {
        "release_id": RELEASE_ID,
        "generated_on": "2026-09-02",
        "source_mode": source_mode,
        "neo4j_runtime_verified": source_mode.startswith("Neo4j"),
        "inputs": [
            {
                "file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256(path),
            }
            for path in input_paths
        ],
        "figures": figures,
    }
    (OUTPUT_ROOT / "FIGURE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate publication-ready PestKG figures.")
    parser.add_argument("--neo4j-uri", default="")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_style()
    source_mode = "release CSV fallback"
    if args.neo4j_uri:
        try:
            nodes, edges = neo4j_neighborhood(
                args.neo4j_uri, args.neo4j_user, args.neo4j_password, FORTIN_PRODUCT_ID
            )
            source_mode = f"Neo4j ({args.neo4j_uri})"
        except Exception as exc:
            print(f"Neo4j unavailable ({exc}); using released CSV sample.")
            nodes, edges = file_neighborhood(FORTIN_PRODUCT_ID)
    else:
        nodes, edges = file_neighborhood(FORTIN_PRODUCT_ID)
    figure_dataset_landscape()
    figure_single_site(nodes, edges)
    figure_federated()
    figure_storyboard(nodes, edges)
    write_captions(source_mode)
    write_manifest(source_mode)
    print(f"Generated four figure sets in {OUTPUT_ROOT} using {source_mode}.")


if __name__ == "__main__":
    main()
