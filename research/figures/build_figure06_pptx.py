"""Render figure 06 panels individually and assemble a PPTX deck.

Slides:
  1. full figure (a+b+c)
  2. panel a alone (bipartite, large)
  3. panel b alone (jurisdiction projection)
  4. panel c alone (entity projection, large)
  5. notes explaining panel a
  6. notes explaining panel c
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

from generate_figures import (
    INK,
    MUTED,
    OUTPUT_ROOT,
    SAMPLE_ROOT,
    configure_style,
    panel_label,
    read_csv,
)
from generate_extended_figures import (
    draw_bipartite,
    draw_country_projection,
    draw_entity_projection,
    projection_contract,
)

PANEL_DIR = OUTPUT_ROOT / "figure06_panels"
PANEL_DIR.mkdir(parents=True, exist_ok=True)


def render_panels(contract):
    # panel a: tall canvas, 32 right-hand labels
    fig_a = plt.figure(figsize=(9.5, 10.2))
    ax = fig_a.add_subplot(111)
    draw_bipartite(ax, contract)
    ax.set_title("a  Jurisdiction–entity bipartite network (32 shared ChEBI AIs)", loc="left", fontweight="bold")
    fig_a.savefig(PANEL_DIR / "panel_a.png", dpi=300, bbox_inches="tight")
    plt.close(fig_a)

    # panel b
    fig_b = plt.figure(figsize=(6.5, 5.2))
    ax = fig_b.add_subplot(111)
    draw_country_projection(ax, contract)
    ax.set_title("b  Jurisdiction projection", loc="left", fontweight="bold")
    fig_b.savefig(PANEL_DIR / "panel_b.png", dpi=300, bbox_inches="tight")
    plt.close(fig_b)

    # panel c: large ring
    fig_c = plt.figure(figsize=(9.5, 9.5))
    ax = fig_c.add_subplot(111)
    draw_entity_projection(ax, contract)
    ax.set_title("c  Shared-entity projection (32 ChEBI AIs, 226 edges)", loc="left", fontweight="bold")
    fig_c.savefig(PANEL_DIR / "panel_c.png", dpi=300, bbox_inches="tight")
    plt.close(fig_c)

    # full figure (reuse the already-rendered full PNG)
    print("panels rendered")


def add_title(slide, text, subtitle=None):
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    tx = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.33), Inches(0.9))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.runs[0].font.size = Pt(28)
    p.runs[0].font.bold = True
    p.runs[0].font.color.rgb = RGBColor(0x17, 0x21, 0x2B)
    if subtitle:
        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.runs[0].font.size = Pt(14)
        p2.runs[0].font.color.rgb = RGBColor(0x62, 0x70, 0x80)


def add_image_centered(slide, img_path, top_in, height_in):
    from PIL import Image
    im = Image.open(img_path)
    w_px, h_px = im.size
    width_in = height_in * w_px / h_px
    left = (13.333 - width_in) / 2
    slide.shapes.add_picture(str(img_path), Inches(left), Inches(top_in), height=Inches(height_in))


def add_notes_slide(prs, title, bullets):
    from pptx.dml.color import RGBColor
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    add_title(slide, title)
    tx = slide.shapes.add_textbox(Inches(0.7), Inches(1.3), Inches(12), Inches(5.8))
    tf = tx.text_frame
    tf.word_wrap = True
    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = b
        p.runs[0].font.size = Pt(16)
        p.runs[0].font.color.rgb = RGBColor(0x17, 0x21, 0x2B)
        p.space_after = Pt(10)


def main():
    configure_style()
    q1_rows = read_csv(SAMPLE_ROOT / "comparisons" / "q1.csv")
    contract = projection_contract(q1_rows, limit=100)
    render_panels(contract)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1. full figure
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "Figure 06  Bipartite network and projections (full)",
              "PestKG release 2026.08.3_federated · 4 jurisdictions × 32 shared ChEBI AIs")
    add_image_centered(s, OUTPUT_ROOT / "figure_06_bipartite_and_projections_full.png", top_in=1.2, height_in=5.9)

    # 2. panel a
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "Panel a  Jurisdiction–entity bipartite network",
              "Left: TW/CN/KR/JP · Right: 32 shared ChEBI active ingredients · Edge width = log(registration use count)")
    add_image_centered(s, PANEL_DIR / "panel_a.png", top_in=1.1, height_in=6.1)

    # 3. panel b
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "Panel b  Jurisdiction projection",
              "Edge label = number of shared ChEBI AIs · Node size = distinct AIs registered in that jurisdiction")
    add_image_centered(s, PANEL_DIR / "panel_b.png", top_in=1.3, height_in=5.6)

    # 4. panel c
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "Panel c  Shared-entity (ChEBI) projection",
              "Ring layout · Edge = co-occurrence in ≥2 jurisdictions · Node size = total registration uses")
    add_image_centered(s, PANEL_DIR / "panel_c.png", top_in=1.1, height_in=6.1)

    # 5. notes on panel a
    add_notes_slide(prs, "Panel a  How to read it", [
        "• What it is: a bipartite (two-mode) graph. Only cross-type edges are drawn: jurisdiction ↔ active ingredient.",
        "• Left column: the four East-Asian regulatory jurisdictions covered by the Q1 cross-jurisdiction projection — TW (APHIA), CN (ICAMA), JP (FAMIC ACIS), KR (RDA PSIS).",
        "• Right column: all 32 ChEBI active ingredients observed in ≥2 of these four jurisdictions (previously only the top-14 were shown; this rebuild uses the full list from q1.csv).",
        "• Edge: the jurisdiction has a current registration record for that ingredient. Edge width scales with log(registration_use_count), i.e. how many crop/use contexts the ingredient is registered for in that country.",
        "• Reading guide: a 'global' ingredient (e.g. chlorothalonil) reaches all four jurisdictions; a 'regional' ingredient (e.g. 1-methylcyclopropene) reaches only two and has thin edges.",
        "• Why no other countries: the other 8 jurisdictions in the release (AU/US/NZ/NL/IE/GB/GB-NI/HU) are in the knowledge graph but their local ingredients have not yet been aligned to ChEBI, so they do not appear in the Q1 projection. Adding them requires running the ChEBI alignment for those sites — it is a data-pipeline step, not a plotting change.",
        "• Scientific point: cross-jurisdiction comparison becomes possible without merging raw national datasets, by routing through the shared ChEBI identifier.",
    ])

    # 6. notes on panel c
    add_notes_slide(prs, "Panel c  How to read it", [
        "• What it is: the one-mode projection of the bipartite graph onto the ingredient side, computed as B^T B where B is the jurisdiction×ingredient incidence matrix.",
        "• An edge between two ingredients means: the two ingredients are both registered in at least two shared jurisdictions. Edge weight = number of shared jurisdictions (2 or 3).",
        "• Node size = total registration-use count across all four jurisdictions (mancozeb 535 is largest; 1-methylcyclopropene 7 is smallest).",
        "• Why not every pair is connected: of 32 nodes there are 496 possible pairs, but only 226 are drawn. Pairs are dropped when (i) they share only one jurisdiction (below the ≥2 threshold), or (ii) their jurisdiction sets are disjoint (e.g. one pair appears only in TW+CN, the other only in KR+JP).",
        "• The dense inner ring (chlorothalonil, difenoconazole, pyraclostrobin, imidacloprid, azoxystrobin, thiophanate-methyl) are the multinational mainstream ingredients — they co-occur across 3 jurisdictions and dominate the network.",
        "• Sparse outer nodes are regionally confined ingredients; their thin or absent edges signal weak cross-jurisdiction alignment evidence and are candidates for data backfill.",
        "• Scientific point: this ring is the empirical signature of a federated knowledge graph — independent national registries become comparable through a shared external vocabulary (ChEBI) rather than through centralised data ingestion.",
    ])

    # 7. 中文说明：面板 a
    add_notes_slide(prs, "图 a  二部图怎么读（中文说明）", [
        "• 图形性质：二部图（bipartite / two-mode graph）。按定义只画跨类型边：辖区 ↔ 活性成分；同类节点之间不直接连边。",
        "• 左列：四个东亚监管辖区——TW（台湾 APHIA）、CN（中国大陆 ICAMA）、JP（日本 FAMIC ACIS）、KR（韩国 RDA PSIS）。",
        "• 右列：在这四个辖区中至少两个辖区出现过的全部 32 个 ChEBI 共享活性成分（旧图只取前 14 个，本版用 q1.csv 全量重算）。",
        "• 边：该辖区对该成分有现行登记记录。边宽按 log(registration_use_count) 缩放，即该成分在该国登记的作物/用途情境数——边越粗代表登记用途越广。",
        "• 读图要点：chlorothalonil（百菌清）连接四个辖区，是唯一的全球成分；1-methylcyclopropene 只连两个辖区且边很细，属于区域性成分。",
        "• 为什么没有其他国家：发布版共收录 12 个辖区，但另外 8 个（AU/US/NZ/NL/IE/GB/GB-NI/HU）的本地成分尚未对齐到 ChEBI 全局 ID，因此不出现在 Q1 投影表里。补全它们需要对这些站点再跑 ChEBI 语义对齐——这是数据工程步骤，不是画图问题。",
        "• 科研含义：四个国家的原始登记数据（中/繁/日/韩）无需跨国合并，只要路由到共享的 ChEBI 标识符，就能做跨国比较——这就是联邦式知识图谱的核心主张。",
    ])

    # 8. 中文说明：面板 c
    add_notes_slide(prs, "图 c  实体投影怎么读（中文说明）", [
        "• 图形性质：二部图在成分一侧的单模投影（one-mode projection）。设辖区×成分邻接矩阵为 B，则投影邻接矩阵 = BᵀB。",
        "• 两个成分之间画边 = 它们在至少两个共同辖区都有登记；边的粗细 = 共同辖区数（2 或 3）。",
        "• 节点大小 = 该成分在四个辖区的登记用途总数（mancozeb 最大 535，1-methylcyclopropene 最小 7）。",
        "• 为什么不是完全图：32 个节点理论上 496 对，只画了 226 条。其余 270 对被过滤掉的原因有二：(1) 只在 1 个辖区同时出现，低于 ≥2 的阈值；(2) 辖区集合无交集（例如一对只出现在 TW+CN，另一对只出现在 KR+JP）。",
        "• 密集内环（chlorothalonil、difenoconazole、pyraclostrobin、imidacloprid、azoxystrobin、thiophanate-methyl）= 跨国主流农药，在 3 个辖区同时登记，主导整个网络。",
        "• 稀疏外围节点 = 区域性成分；边少或无边意味着跨国对齐证据薄弱，是后续补数据的优先候选。",
        "• 科研含义：这张环形图是联邦式知识图谱的实证证据——各国独立登记体系通过 ChEBI 这个外部共享词表变得可比较，而不需要把原始数据集中到一处。",
    ])

    out = OUTPUT_ROOT / "figure_06_explained.pptx"
    prs.save(out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
