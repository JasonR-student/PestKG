"""Rebuild Figure 06 (bipartite + projections) from the FULL cross-jurisdiction Q1 table.

Instead of capping shared ChEBI active ingredients at the top-14, this rebuild uses
EVERY ChEBI active ingredient observed in >=2 of {TW, CN, KR, JP}, so panels (a)
and (c) carry the complete federation signal available in the frozen release.

Outputs (under artifacts/research/figures/output/):
  - source_tables/figure_06_*.csv            (old tables backed up to *.bak)
  - figure_06_bipartite_and_projections_full.{png,pdf,svg}
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt

from generate_figures import (
    INK,
    MUTED,
    OUTPUT_ROOT,
    SAMPLE_ROOT,
    configure_style,
    panel_label,
    read_csv,
    save_figure,
)
from generate_extended_figures import (
    COUNTRY_COLORS,
    COUNTRY_ORDER,
    PAPER,
    SOURCE_TABLE_ROOT,
    draw_bipartite,
    draw_country_projection,
    draw_entity_projection,
    projection_contract,
    write_projection_tables,
)


def main() -> None:
    configure_style()

    q1_rows = read_csv(SAMPLE_ROOT / "comparisons" / "q1.csv")
    # limit=100 -> all 32 cross-jurisdiction ChEBI AIs (was 14 in the original figure)
    contract = projection_contract(q1_rows, limit=100)
    n_ai = len(contract["active_nodes"])
    n_bip = len(contract["bipartite_edges"])
    n_entity_edges = len(contract["entity_projection"])
    print(f"AI nodes: {n_ai} | bipartite edges: {n_bip} | entity-projection edges: {n_entity_edges}")

    # --- backup old source tables, then rewrite with full data ---
    for stem in (
        "figure_06_active_nodes.csv",
        "figure_06_bipartite_edges.csv",
        "figure_06_country_projection.csv",
        "figure_06_entity_projection.csv",
    ):
        old = SOURCE_TABLE_ROOT / stem
        if old.exists():
            bak = SOURCE_TABLE_ROOT / f"{stem}.top14.bak"
            shutil.copy2(old, bak)
            print(f"backed up {old.name} -> {bak.name}")
    write_projection_tables(contract)
    print("wrote full source tables")

    # --- render with a taller canvas so 32 right-hand labels stay legible ---
    fig = plt.figure(figsize=(13.2, 10.2))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.55, 1], hspace=0.42, wspace=0.26)
    ax_bipartite = fig.add_subplot(grid[:, 0])
    ax_country = fig.add_subplot(grid[0, 1])
    ax_entity = fig.add_subplot(grid[1, 1])

    draw_bipartite(ax_bipartite, contract)
    draw_country_projection(ax_country, contract)
    draw_entity_projection(ax_entity, contract)

    ax_bipartite.set_title("Jurisdiction-shared entity bipartite network (all 32 shared ChEBI AIs)", loc="left", fontweight="bold")
    ax_country.set_title("Jurisdiction projection", loc="left", fontweight="bold")
    ax_entity.set_title("Shared-entity projection", loc="left", fontweight="bold")
    panel_label(ax_bipartite, "a")
    panel_label(ax_country, "b")
    panel_label(ax_entity, "c")
    fig.text(0.49, 0.71, "Jurisdiction\nprojection", fontsize=6.5, color=MUTED, ha="center")
    fig.text(0.49, 0.29, "Entity\nprojection", fontsize=6.5, color=MUTED, ha="center")

    save_figure(fig, "figure_06_bipartite_and_projections_full")
    print("saved figure_06_bipartite_and_projections_full.{png,pdf,svg}")


if __name__ == "__main__":
    main()
