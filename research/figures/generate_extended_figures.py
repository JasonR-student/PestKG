from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import Ellipse, Polygon, Rectangle
from neo4j import GraphDatabase

from generate_figures import (
    FORTIN_PRODUCT_ID,
    GRID,
    INK,
    MUTED,
    OUTPUT_ROOT,
    PALETTE,
    PAPER,
    PROJECT_ROOT,
    RELEASE_ID,
    RELEASE_ROOT,
    SAMPLE_ROOT,
    arrow,
    configure_style,
    draw_dataset_landscape,
    file_neighborhood,
    jurisdiction_font,
    neo4j_neighborhood,
    panel_label,
    read_csv,
    save_figure,
    sha256,
    short_label,
)


SOURCE_TABLE_ROOT = OUTPUT_ROOT / "source_tables"
COUNTRY_ORDER = ["TW", "CN", "KR", "JP"]
COUNTRY_COLORS = {
    "TW": "#416F9B",
    "CN": "#9A6248",
    "KR": "#7562A0",
    "JP": "#4C8C79",
}
SITE_LABELS = {
    "CN": "ICAMA",
    "TW": "APHIA",
    "JP": "FAMIC ACIS",
    "KR": "RDA PSIS",
}
ENTITY_FILL = "#F5D94E"
RELATION_FILL = "#E7A719"
ATTRIBUTE_FILL = "#FFF4CF"


def integer(value: str) -> int:
    return int(value or 0)


def camel_label(value: str, width: int = 12) -> str:
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z]*", value) or [value]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def q1_from_neo4j(uri: str, user: str, password: str) -> list[dict[str, str]]:
    query = """
    MATCH (observation:PaperQ1Observation)
    RETURN observation.cropSharedId AS crop_shared_id,
           observation.cropLabelEnglish AS crop_label_en,
           observation.cropCountryCount AS crop_country_count,
           observation.activeSharedId AS active_shared_id,
           observation.activeIngredientLabelEnglish AS active_ingredient_label_en,
           observation.activeCountryCount AS active_country_count,
           observation.jurisdiction AS jurisdiction,
           observation.cropLocalLabels AS crop_local_labels,
           observation.activeIngredientLocalLabels AS active_ingredient_local_labels,
           observation.productCount AS product_count,
           observation.registrationUseCount AS registration_use_count,
           observation.sourceRecordCount AS source_record_count,
           observation.pairingStatus AS pairing_status
    ORDER BY observation.rowNumber
    """
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        records = driver.execute_query(query).records
    return [{key: str(value or "") for key, value in record.data().items()} for record in records]


def projection_contract(rows: list[dict[str, str]], limit: int = 14) -> dict[str, Any]:
    active_stats: dict[str, dict[str, Any]] = {}
    country_active_uses: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        active_id = row["active_shared_id"]
        jurisdiction = row["jurisdiction"]
        if not active_id.startswith("CHEBI:") or jurisdiction not in COUNTRY_ORDER:
            continue
        stats = active_stats.setdefault(
            active_id,
            {
                "id": active_id,
                "labels": Counter(),
                "jurisdictions": set(),
                "registration_use_count": 0,
            },
        )
        label = row["active_ingredient_label_en"].strip()
        if label:
            stats["labels"][label.casefold()] += 1
        stats["jurisdictions"].add(jurisdiction)
        use_count = integer(row["registration_use_count"])
        stats["registration_use_count"] += use_count
        country_active_uses[(jurisdiction, active_id)] += use_count

    eligible = [stats for stats in active_stats.values() if len(stats["jurisdictions"]) >= 2]
    eligible.sort(
        key=lambda item: (
            -len(item["jurisdictions"]),
            -item["registration_use_count"],
            item["id"],
        )
    )
    active_nodes = []
    for stats in eligible[:limit]:
        label_key = stats["labels"].most_common(1)[0][0]
        active_nodes.append(
            {
                "id": stats["id"],
                "label": label_key.title(),
                "jurisdiction_count": len(stats["jurisdictions"]),
                "registration_use_count": stats["registration_use_count"],
            }
        )

    selected_ids = {row["id"] for row in active_nodes}
    bipartite_edges = [
        {
            "jurisdiction": jurisdiction,
            "active_shared_id": active_id,
            "registration_use_count": count,
        }
        for (jurisdiction, active_id), count in country_active_uses.items()
        if active_id in selected_ids and count > 0
    ]
    bipartite_edges.sort(key=lambda row: (COUNTRY_ORDER.index(row["jurisdiction"]), row["active_shared_id"]))

    country_sets = {
        jurisdiction: {
            edge["active_shared_id"]
            for edge in bipartite_edges
            if edge["jurisdiction"] == jurisdiction
        }
        for jurisdiction in COUNTRY_ORDER
    }
    country_projection = []
    for source, target in combinations(COUNTRY_ORDER, 2):
        shared = country_sets[source] & country_sets[target]
        union = country_sets[source] | country_sets[target]
        if shared:
            country_projection.append(
                {
                    "source": source,
                    "target": target,
                    "shared_active_count": len(shared),
                    "jaccard": len(shared) / len(union),
                }
            )

    active_country_sets = {
        active["id"]: {
            edge["jurisdiction"]
            for edge in bipartite_edges
            if edge["active_shared_id"] == active["id"]
        }
        for active in active_nodes
    }
    entity_projection = []
    for source, target in combinations([row["id"] for row in active_nodes], 2):
        shared = active_country_sets[source] & active_country_sets[target]
        if len(shared) >= 2:
            entity_projection.append(
                {
                    "source": source,
                    "target": target,
                    "shared_jurisdiction_count": len(shared),
                    "shared_jurisdictions": "|".join(sorted(shared, key=COUNTRY_ORDER.index)),
                }
            )

    return {
        "active_nodes": active_nodes,
        "bipartite_edges": bipartite_edges,
        "country_projection": country_projection,
        "entity_projection": entity_projection,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_projection_tables(contract: dict[str, Any]) -> None:
    write_csv(
        SOURCE_TABLE_ROOT / "figure_06_active_nodes.csv",
        contract["active_nodes"],
        ["id", "label", "jurisdiction_count", "registration_use_count"],
    )
    write_csv(
        SOURCE_TABLE_ROOT / "figure_06_bipartite_edges.csv",
        contract["bipartite_edges"],
        ["jurisdiction", "active_shared_id", "registration_use_count"],
    )
    write_csv(
        SOURCE_TABLE_ROOT / "figure_06_country_projection.csv",
        contract["country_projection"],
        ["source", "target", "shared_active_count", "jaccard"],
    )
    write_csv(
        SOURCE_TABLE_ROOT / "figure_06_entity_projection.csv",
        contract["entity_projection"],
        ["source", "target", "shared_jurisdiction_count", "shared_jurisdictions"],
    )


def er_entity(ax: plt.Axes, xy: tuple[float, float], label: str, width: float = 1.75) -> None:
    x, y = xy
    rect = Rectangle(
        (x - width / 2, y - 0.28),
        width,
        0.56,
        facecolor=ENTITY_FILL,
        edgecolor="#7C8C91",
        linewidth=0.8,
        zorder=4,
    )
    ax.add_patch(rect)
    ax.text(x, y, short_label(label, 22), ha="center", va="center", fontsize=6.4, fontweight="bold", zorder=5)


def er_relation(ax: plt.Axes, xy: tuple[float, float], label: str, scale: float = 1.0) -> None:
    x, y = xy
    half_x = 0.48 * scale
    half_y = 0.25 * scale
    diamond = Polygon(
        [(x, y + half_y), (x + half_x, y), (x, y - half_y), (x - half_x, y)],
        closed=True,
        facecolor=RELATION_FILL,
        edgecolor="#7C8C91",
        linewidth=0.75,
        zorder=4,
    )
    ax.add_patch(diamond)
    ax.text(x, y, short_label(label, 13), ha="center", va="center", fontsize=4.9, zorder=5)


def er_attribute(ax: plt.Axes, xy: tuple[float, float], label: str, width: float = 1.2) -> None:
    x, y = xy
    patch = Ellipse(
        (x, y),
        width,
        0.42,
        facecolor=ATTRIBUTE_FILL,
        edgecolor="#B8C8CF",
        linewidth=0.65,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(x, y, short_label(label, 18), ha="center", va="center", fontsize=4.9, color=INK, zorder=4)


def plain_link(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], linewidth: float = 0.65) -> None:
    ax.plot([start[0], end[0]], [start[1], end[1]], color="#9EB3BE", linewidth=linewidth, zorder=1)


def draw_apvma_er(ax: plt.Axes, compact: bool = False) -> None:
    if compact:
        draw_apvma_er_compact(ax)
        return
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(-2.65, 3.35)
    ax.axis("off")
    ax.set_title("APVMA single-site entity-relationship model", loc="left", fontweight="bold", fontsize=8 if compact else 10)

    entities = {
        "agency": ((0.9, 2.35), "RegulatoryAgency"),
        "country": ((3.0, 2.35), "CountryJurisdiction"),
        "registration": ((5.35, 2.35), "Registration"),
        "product": ((8.25, 2.35), "PesticideProduct"),
        "use": ((5.35, 0.25), "RegistrationUse"),
        "active": ((8.25, 0.25), "ActiveIngredientLocal"),
        "crop": ((1.15, -1.55), "CropLocal"),
        "target": ((3.75, -1.55), "TargetLocal"),
        "formulation": ((7.0, -1.55), "FormulationLocal"),
    }
    for key, (xy, label) in entities.items():
        er_entity(ax, xy, label, width=1.55 if compact else (1.95 if key in {"country", "active"} else 1.72))

    relations = [
        ("agency", "country", (1.95, 2.35), "regulatesIn"),
        ("country", "registration", (4.18, 2.35), "hasRegistration"),
        ("registration", "product", (6.82, 2.35), "hasProduct"),
        ("registration", "use", (5.35, 1.27), "hasRegistrationUse"),
        ("use", "product", (6.92, 1.18), "usesProduct"),
        ("use", "active", (6.82, 0.25), "hasActiveIngredient"),
        ("use", "crop", (3.22, -0.7), "registeredForCrop"),
        ("use", "target", (4.55, -0.7), "registeredForTarget"),
        ("use", "formulation", (6.18, -0.7), "hasFormulation"),
    ]
    for source_key, target_key, relation_xy, label in relations:
        source_xy = entities[source_key][0]
        target_xy = entities[target_key][0]
        plain_link(ax, source_xy, relation_xy, linewidth=0.5 if compact else 0.7)
        plain_link(ax, relation_xy, target_xy, linewidth=0.5 if compact else 0.7)
        er_relation(ax, relation_xy, label, scale=0.82 if compact else 1.0)

    attributes = [
        ((4.15, 3.08), "node_id", entities["registration"][0]),
        ((5.35, 3.08), "registration no. 84962", entities["registration"][0]),
        ((6.55, 3.08), "status", entities["registration"][0]),
        ((7.55, 3.08), "label_original", entities["product"][0]),
        ((8.9, 3.08), "Fortin Herbicide", entities["product"][0]),
        ((9.65, 1.3), "source_record_id", entities["product"][0]),
        ((4.0, -0.15), "jurisdiction = AU", entities["use"][0]),
        ((4.15, 0.95), "source_url", entities["use"][0]),
        ((8.25, 0.95), "GLYPHOSATE", entities["active"][0]),
        ((0.7, -2.3), "label_en", entities["crop"][0]),
        ((2.0, -2.3), "label_original", entities["crop"][0]),
        ((5.3, -2.3), "properties_json", entities["target"][0]),
        ((8.0, -2.3), "formulation name", entities["formulation"][0]),
    ]
    for xy, label, entity_xy in attributes:
        plain_link(ax, entity_xy, xy, linewidth=0.48)
        er_attribute(ax, xy, label, width=max(1.05, min(1.65, 0.078 * len(label))))
    ax.text(
        0.05,
        -2.58,
        "Rectangles: entities  |  diamonds: released predicates  |  ellipses: retained fields and example values",
        fontsize=5.5,
        color=MUTED,
    )


def compact_entity(ax: plt.Axes, xy: tuple[float, float], label: str) -> None:
    x, y = xy
    width = 1.45
    height = 0.52
    ax.add_patch(
        Rectangle(
            (x - width / 2, y - height / 2),
            width,
            height,
            facecolor=ENTITY_FILL,
            edgecolor="#7C8C91",
            linewidth=0.7,
            zorder=3,
        )
    )
    ax.text(x, y, camel_label(label), fontsize=3.75, fontweight="bold", ha="center", va="center", linespacing=0.92, zorder=4)


def compact_relation(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    label: str,
    offset: tuple[float, float] = (0.0, 0.0),
) -> None:
    plain_link(ax, start, end, linewidth=0.55)
    midpoint = ((start[0] + end[0]) / 2 + offset[0], (start[1] + end[1]) / 2 + offset[1])
    er_relation(ax, midpoint, "", scale=0.43)
    ax.text(
        midpoint[0],
        midpoint[1] + 0.27,
        short_label(label, 15),
        fontsize=3.45,
        color=MUTED,
        ha="center",
        va="bottom",
        bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 0.25},
        zorder=5,
    )


def draw_apvma_er_compact(ax: plt.Axes) -> None:
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("APVMA entity-relationship model", loc="left", fontweight="bold", fontsize=8)
    positions = {
        "agency": (0.8, 5.0),
        "country": (3.15, 5.0),
        "registration": (5.55, 5.0),
        "product": (8.9, 5.0),
        "use": (5.55, 2.9),
        "active": (8.9, 2.9),
        "crop": (2.0, 0.75),
        "target": (5.3, 0.75),
        "formulation": (8.55, 0.75),
    }
    labels = {
        "agency": "RegulatoryAgency",
        "country": "CountryJurisdiction",
        "registration": "Registration",
        "product": "PesticideProduct",
        "use": "RegistrationUse",
        "active": "ActiveIngredientLocal",
        "crop": "CropLocal",
        "target": "TargetLocal",
        "formulation": "FormulationLocal",
    }
    for key, xy in positions.items():
        compact_entity(ax, xy, labels[key])
    compact_relation(ax, positions["agency"], positions["country"], "regulatesIn")
    compact_relation(ax, positions["country"], positions["registration"], "hasRegistration")
    compact_relation(ax, positions["registration"], positions["product"], "hasProduct")
    compact_relation(ax, positions["registration"], positions["use"], "hasRegistrationUse", (-0.48, 0.0))
    compact_relation(ax, positions["use"], positions["product"], "usesProduct", (0.48, 0.0))
    compact_relation(ax, positions["use"], positions["active"], "hasActiveIngredient")
    compact_relation(ax, positions["use"], positions["crop"], "registeredForCrop", (-0.18, 0.02))
    compact_relation(ax, positions["use"], positions["target"], "registeredForTarget", (0.02, -0.03))
    compact_relation(ax, positions["use"], positions["formulation"], "hasFormulation", (0.18, 0.02))
    ax.text(0.2, 0.08, "Country-local entity classes and released predicates", fontsize=4.5, color=MUTED)


def draw_bipartite(ax: plt.Axes, contract: dict[str, Any], compact: bool = False) -> None:
    active_nodes = contract["active_nodes"][: 8 if compact else len(contract["active_nodes"])]
    active_ids = [row["id"] for row in active_nodes]
    active_by_id = {row["id"]: row for row in active_nodes}
    edges = [row for row in contract["bipartite_edges"] if row["active_shared_id"] in active_ids]

    country_y = {code: value for code, value in zip(COUNTRY_ORDER, np.linspace(0.86, 0.14, len(COUNTRY_ORDER)))}
    active_y = {node_id: value for node_id, value in zip(active_ids, np.linspace(0.94, 0.06, len(active_ids)))}
    max_uses = max(row["registration_use_count"] for row in edges)
    for edge in edges:
        y1 = country_y[edge["jurisdiction"]]
        y2 = active_y[edge["active_shared_id"]]
        width = 0.25 + 1.7 * math.log1p(edge["registration_use_count"]) / math.log1p(max_uses)
        ax.plot(
            [0.18, 0.78],
            [y1, y2],
            color=COUNTRY_COLORS[edge["jurisdiction"]],
            alpha=0.34,
            linewidth=width,
            zorder=1,
        )
    for code, y in country_y.items():
        size = 290 if compact else 430
        ax.scatter(0.16, y, s=size, color=COUNTRY_COLORS[code], edgecolor=PAPER, linewidth=0.9, zorder=3)
        ax.text(0.16, y, code, color=PAPER, fontsize=6 if compact else 7, fontweight="bold", ha="center", va="center", zorder=4)
    uses = [row["registration_use_count"] for row in active_nodes]
    minimum, maximum = min(uses), max(uses)
    for node_id, y in active_y.items():
        row = active_by_id[node_id]
        normalized = (row["registration_use_count"] - minimum) / max(1, maximum - minimum)
        ax.scatter(0.8, y, s=(45 if compact else 70) + normalized * (95 if compact else 170), color=PALETTE["CHEBI"], edgecolor=PAPER, linewidth=0.65, zorder=3)
        label = row["label"] if not compact else row["label"].split("-")[0]
        ax.text(0.84, y, short_label(label, 18), fontsize=4.8 if compact else 5.7, va="center", color=INK)
    ax.text(0.16, 1.0, "Jurisdictions", fontsize=5.7 if compact else 6.5, fontweight="bold", ha="center", color=MUTED)
    ax.text(0.8, 1.0, "Shared ChEBI entities", fontsize=5.7 if compact else 6.5, fontweight="bold", ha="center", color=MUTED)
    ax.set_xlim(0, 1.18)
    ax.set_ylim(0, 1.04)
    ax.axis("off")


def draw_country_projection(ax: plt.Axes, contract: dict[str, Any], compact: bool = False) -> None:
    graph = nx.Graph()
    graph.add_nodes_from(COUNTRY_ORDER)
    for edge in contract["country_projection"]:
        graph.add_edge(edge["source"], edge["target"], **edge)
    positions = {"TW": (-0.75, 0.25), "CN": (0.75, 0.25), "KR": (-0.42, -0.68), "JP": (0.55, -0.66)}
    for source, target, data in graph.edges(data=True):
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        ax.plot(
            [x1, x2],
            [y1, y2],
            color="#8DA4AE",
            linewidth=0.8 + data["shared_active_count"] * (0.28 if compact else 0.38),
            alpha=0.7,
            zorder=1,
        )
        if not compact:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2, str(data["shared_active_count"]), fontsize=5.5, ha="center", va="center", bbox={"facecolor": PAPER, "edgecolor": "none", "pad": 0.4})
    for node in COUNTRY_ORDER:
        x, y = positions[node]
        active_count = sum(1 for edge in contract["bipartite_edges"] if edge["jurisdiction"] == node)
        ax.scatter(x, y, s=(220 if compact else 390) + active_count * 22, color=COUNTRY_COLORS[node], edgecolor=PAPER, linewidth=0.9, zorder=3)
        ax.text(x, y, node, color=PAPER, fontsize=6.2 if compact else 7.2, fontweight="bold", ha="center", va="center", zorder=4)
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.05, 0.75)
    ax.axis("off")


def draw_entity_projection(ax: plt.Axes, contract: dict[str, Any], compact: bool = False) -> None:
    graph = nx.Graph()
    active_nodes = contract["active_nodes"][: 8 if compact else len(contract["active_nodes"])]
    active_by_id = {row["id"]: row for row in active_nodes}
    graph.add_nodes_from(active_by_id)
    for edge in contract["entity_projection"]:
        if edge["source"] in graph and edge["target"] in graph:
            graph.add_edge(edge["source"], edge["target"], **edge)
    node_ids = list(active_by_id)
    angles = np.linspace(math.pi / 2, math.pi / 2 + 2 * math.pi, len(node_ids), endpoint=False)
    positions = {
        node_id: (math.cos(angle), math.sin(angle))
        for node_id, angle in zip(node_ids, angles)
    }
    for source, target, data in graph.edges(data=True):
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        ax.plot(
            [x1, x2],
            [y1, y2],
            color="#A7B8BE",
            linewidth=0.35 + 0.65 * data["shared_jurisdiction_count"],
            alpha=0.45,
            zorder=1,
        )
    max_uses = max(row["registration_use_count"] for row in active_nodes)
    for node_id, row in active_by_id.items():
        x, y = positions[node_id]
        size = (55 if compact else 75) + (row["registration_use_count"] / max_uses) * (170 if compact else 300)
        ax.scatter(x, y, s=size, color=PALETTE["CHEBI"], edgecolor=PAPER, linewidth=0.7, zorder=3)
        radius = 1.18
        label_x = x * radius
        label_y = y * radius
        horizontal = "left" if label_x >= 0.02 else ("right" if label_x <= -0.02 else "center")
        ax.text(
            label_x,
            label_y,
            short_label(row["label"], 17),
            fontsize=4.4 if compact else 5.0,
            ha=horizontal,
            va="center",
            zorder=4,
        )
    ax.set_xlim(-1.48, 1.48)
    ax.set_ylim(-1.42, 1.42)
    ax.axis("off")


def figure_apvma_er() -> None:
    fig, ax = plt.subplots(figsize=(11.4, 6.5))
    draw_apvma_er(ax)
    panel_label(ax, "a")
    fig.tight_layout()
    save_figure(fig, "figure_05_apvma_entity_relationship")


def figure_bipartite_projection(contract: dict[str, Any]) -> None:
    fig = plt.figure(figsize=(12.2, 7.1))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.55, 1], hspace=0.38, wspace=0.24)
    ax_bipartite = fig.add_subplot(grid[:, 0])
    ax_country = fig.add_subplot(grid[0, 1])
    ax_entity = fig.add_subplot(grid[1, 1])
    draw_bipartite(ax_bipartite, contract)
    draw_country_projection(ax_country, contract)
    draw_entity_projection(ax_entity, contract)
    ax_bipartite.set_title("Jurisdiction-shared entity bipartite network", loc="left", fontweight="bold")
    ax_country.set_title("Jurisdiction projection", loc="left", fontweight="bold")
    ax_entity.set_title("Shared-entity projection", loc="left", fontweight="bold")
    panel_label(ax_bipartite, "a")
    panel_label(ax_country, "b")
    panel_label(ax_entity, "c")
    fig.text(0.49, 0.72, "Jurisdiction\nprojection", fontsize=6.5, color=MUTED, ha="center")
    fig.text(0.49, 0.28, "Entity\nprojection", fontsize=6.5, color=MUTED, ha="center")
    save_figure(fig, "figure_06_bipartite_and_projections")


def chain_rows(q1_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    candidates = [row for row in q1_rows if row["active_shared_id"] == "CHEBI:3639" and row["jurisdiction"] in COUNTRY_ORDER]
    by_country: dict[str, dict[str, str]] = {}
    for row in candidates:
        by_country.setdefault(row["jurisdiction"], row)
    if set(by_country) != set(COUNTRY_ORDER):
        raise ValueError("Expected chlorothalonil alignment evidence for TW, CN, KR, and JP.")
    return [by_country[code] for code in COUNTRY_ORDER]


def site_box(ax: plt.Axes, xy: tuple[float, float], title: str, subtitle: str, color: str, compact: bool) -> None:
    x, y = xy
    width = 1.52 if compact else 1.95
    height = 0.54 if compact else 0.68
    patch = Rectangle(
        (x - width / 2, y - height / 2),
        width,
        height,
        facecolor=PAPER,
        edgecolor=color,
        linewidth=1.0,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.add_patch(Rectangle((x - width / 2, y + height / 2 - 0.10), width, 0.10, color=color, zorder=4))
    ax.text(x, y + 0.06, short_label(title, 18), fontsize=4.8 if compact else 6.5, fontweight="bold", ha="center", va="center", zorder=5)
    ax.text(x, y - 0.14, short_label(subtitle, 16 if compact else 23), fontsize=3.55 if compact else 5.2, color=MUTED, ha="center", va="center", zorder=5)


def draw_multisite_chain(ax: plt.Axes, q1_rows: list[dict[str, str]], compact: bool = False) -> None:
    countries = json.loads((RELEASE_ROOT / "countries.json").read_text(encoding="utf-8"))
    metadata = {row["jurisdiction"]: row for row in countries}
    rows = chain_rows(q1_rows)
    ax.set_xlim(-0.15, 11.35)
    ax.set_ylim(-2.75, 3.0)
    ax.axis("off")
    ax.set_title("Official registers linked through PestKG to shared semantic resources", loc="left", fontweight="bold", fontsize=8 if compact else 10)
    ax.add_patch(Rectangle((8.45, -2.55), 2.7, 5.2, facecolor="#F3F6F7", edgecolor="none", zorder=0))
    headers = [
        (0.9, "OFFICIAL WEBSITE"),
        (3.15, "COUNTRY-LOCAL GRAPH"),
        (5.75, "LOCAL SEMANTIC ENTITIES"),
        (9.72, "EXTERNAL KNOWLEDGE BASES"),
    ]
    for x, label in headers:
        ax.text(x, 2.68, label, fontsize=5.2 if compact else 6.3, fontweight="bold", color=MUTED, ha="center")

    row_y = {code: 2.05 - index * 1.25 for index, code in enumerate(COUNTRY_ORDER)}
    active_shared_xy = (9.72, 1.15)
    banana_xy = (9.72, -0.35)
    cauliflower_xy = (9.72, -1.65)
    site_box(ax, active_shared_xy, "Chlorothalonil", "ChEBI:3639", PALETTE["CHEBI"], compact)
    site_box(ax, banana_xy, "Bananas", "AGROVOC c_806", PALETTE["AGROVOC"], compact)
    site_box(ax, cauliflower_xy, "Cauliflowers", "AGROVOC c_1394", PALETTE["AGROVOC"], compact)
    ax.text(10.8, 1.6, "ChEBI", fontsize=6.2 if compact else 7.2, fontweight="bold", color=PALETTE["CHEBI"], ha="right")
    ax.text(10.8, 0.08, "AGROVOC", fontsize=6.2 if compact else 7.2, fontweight="bold", color=PALETTE["AGROVOC"], ha="right")

    for row in rows:
        code = row["jurisdiction"]
        y = row_y[code]
        meta = metadata[code]
        website_xy = (0.92, y)
        graph_xy = (3.15, y)
        active_xy = (5.72, y + 0.2)
        crop_xy = (5.72, y - 0.2)
        site_box(ax, website_xy, SITE_LABELS[code], meta["site_id"], COUNTRY_COLORS[code], compact)
        site_box(
            ax,
            graph_xy,
            f"{code} PestKG",
            f"{meta['nodes']:,} nodes / {meta['edges']:,} rels",
            COUNTRY_COLORS[code],
            compact,
        )
        arrow(ax, website_xy, graph_xy, color="#9FAEB6", linewidth=0.7, mutation_scale=5)
        arrow(ax, graph_xy, active_xy, color="#A9B7BD", linewidth=0.62, mutation_scale=5)
        arrow(ax, graph_xy, crop_xy, color="#A9B7BD", linewidth=0.62, mutation_scale=5)

        active_label = row["active_ingredient_local_labels"].split(" | ", 1)[0]
        crop_label = row["crop_local_labels"].split(" | ", 1)[0]
        if code == "KR" and "(" in crop_label:
            crop_label = crop_label.split("(", 1)[0]
        ax.scatter(*active_xy, s=46 if compact else 66, color=PALETTE["CHEBI"], edgecolor=PAPER, linewidth=0.6, zorder=3)
        ax.scatter(*crop_xy, s=46 if compact else 66, color=PALETTE["AGROVOC"], edgecolor=PAPER, linewidth=0.6, zorder=3)
        local_font = jurisdiction_font(code)
        ax.text(active_xy[0] + 0.12, active_xy[1], short_label(active_label, 20), fontsize=4.5 if compact else 5.3, va="center", fontfamily=local_font)
        ax.text(crop_xy[0] + 0.12, crop_xy[1], short_label(crop_label, 20), fontsize=4.5 if compact else 5.3, va="center", fontfamily=local_font)
        arrow(ax, active_xy, active_shared_xy, linestyle=(0, (3, 2)), color=PALETTE["CHEBI"], linewidth=0.68, mutation_scale=5)
        crop_target = banana_xy if row["crop_shared_id"].endswith("c_806") else cauliflower_xy
        arrow(ax, crop_xy, crop_target, linestyle=(0, (3, 2)), color=PALETTE["AGROVOC"], linewidth=0.68, mutation_scale=5)
        if not compact:
            ax.text(7.35, y + 0.43, "semantic alignment", fontsize=4.9, color=MUTED, ha="center")

    ax.text(
        5.45,
        -2.58,
        "Country-local entities remain distinct; dashed links represent Q1 semantic-alignment evidence.",
        fontsize=5.0 if compact else 5.7,
        color=MUTED,
        ha="center",
    )


def figure_multisite_chain(q1_rows: list[dict[str, str]]) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 6.3))
    draw_multisite_chain(ax, q1_rows)
    panel_label(ax, "a")
    fig.tight_layout()
    save_figure(fig, "figure_07_multisite_external_chain")


def draw_release_summary(ax: plt.Axes) -> None:
    release = json.loads((RELEASE_ROOT / "release.json").read_text(encoding="utf-8"))
    countries = json.loads((RELEASE_ROOT / "countries.json").read_text(encoding="utf-8"))
    inventory = release["inventory"]
    metrics = [
        ("12", "jurisdictions"),
        ("821,183", "source records"),
        ("1.20 M", "country nodes"),
        ("9.74 M", "relationships"),
        ("44,645", "shared nodes"),
        ("48,721", "alignment links"),
    ]
    for index, (value, label) in enumerate(metrics):
        column = index % 3
        row = index // 3
        x = 0.04 + column * 0.32
        y = 0.88 - row * 0.25
        ax.text(x, y, value, transform=ax.transAxes, fontsize=8.5, fontweight="bold", color=INK)
        ax.text(x, y - 0.07, label, transform=ax.transAxes, fontsize=4.9, color=MUTED)
    top = sorted(countries, key=lambda row: row["source_rows"], reverse=True)[:4]
    values = np.array([row["source_rows"] for row in top]) / 1000
    y_positions = np.arange(len(top))
    inset = ax.inset_axes([0.05, 0.06, 0.9, 0.36])
    inset.barh(y_positions, values, color=[COUNTRY_COLORS.get(row["jurisdiction"], "#7A8A99") for row in top], height=0.58)
    inset.set_yticks(y_positions, [row["jurisdiction"] for row in top], fontsize=5)
    inset.invert_yaxis()
    inset.tick_params(axis="x", labelsize=4.5, length=2)
    inset.set_xlabel("Source records (thousands)", fontsize=4.7)
    inset.spines[["top", "right"]].set_visible(False)
    inset.grid(axis="x", color=GRID, linewidth=0.4)
    inset.set_axisbelow(True)
    ax.set_title("Release-scale evidence base", loc="left", fontsize=8, fontweight="bold")
    ax.axis("off")
    assert inventory["jurisdictions"] == 12


def draw_multisite_chain_compact(ax: plt.Axes, q1_rows: list[dict[str, str]]) -> None:
    rows = chain_rows(q1_rows)
    ax.set_xlim(0, 10)
    ax.set_ylim(-2.7, 2.85)
    ax.axis("off")
    ax.set_title("Four official sites linked to shared resources", loc="left", fontsize=8, fontweight="bold")
    ax.add_patch(Rectangle((7.4, -2.45), 2.45, 4.95, facecolor="#F3F6F7", edgecolor="none", zorder=0))
    for x, label in [(0.75, "Sites"), (2.9, "Country graphs"), (5.15, "Local entities"), (8.6, "Shared concepts")]:
        ax.text(x, 2.55, label, fontsize=4.6, fontweight="bold", color=MUTED, ha="center")

    shared = {
        "active": ((8.6, 1.35), "Chlorothalonil", "ChEBI:3639", PALETTE["CHEBI"]),
        "banana": ((8.6, -0.1), "Bananas", "AGROVOC c_806", PALETTE["AGROVOC"]),
        "cauliflower": ((8.6, -1.65), "Cauliflowers", "AGROVOC c_1394", PALETTE["AGROVOC"]),
    }
    for xy, title, subtitle, color in shared.values():
        site_box(ax, xy, title, subtitle, color, True)

    y_values = {code: 1.9 - index * 1.25 for index, code in enumerate(COUNTRY_ORDER)}
    for row in rows:
        code = row["jurisdiction"]
        y = y_values[code]
        site_xy = (0.75, y)
        graph_xy = (2.9, y)
        active_xy = (5.05, y + 0.18)
        crop_xy = (5.05, y - 0.18)
        site_box(ax, site_xy, SITE_LABELS[code], code, COUNTRY_COLORS[code], True)
        site_box(ax, graph_xy, f"{code} PestKG", "country-local", COUNTRY_COLORS[code], True)
        arrow(ax, site_xy, graph_xy, color="#A6B4BA", linewidth=0.55, mutation_scale=4)
        arrow(ax, graph_xy, active_xy, color="#A6B4BA", linewidth=0.5, mutation_scale=4)
        arrow(ax, graph_xy, crop_xy, color="#A6B4BA", linewidth=0.5, mutation_scale=4)
        ax.scatter(*active_xy, s=28, color=PALETTE["CHEBI"], edgecolor=PAPER, linewidth=0.4, zorder=3)
        ax.scatter(*crop_xy, s=28, color=PALETTE["AGROVOC"], edgecolor=PAPER, linewidth=0.4, zorder=3)
        ax.text(active_xy[0] + 0.1, active_xy[1], f"{code} active", fontsize=3.9, va="center")
        ax.text(crop_xy[0] + 0.1, crop_xy[1], f"{code} crop", fontsize=3.9, va="center")
        arrow(ax, active_xy, shared["active"][0], linestyle=(0, (3, 2)), color=PALETTE["CHEBI"], linewidth=0.55, mutation_scale=4)
        crop_key = "banana" if row["crop_shared_id"].endswith("c_806") else "cauliflower"
        arrow(ax, crop_xy, shared[crop_key][0], linestyle=(0, (3, 2)), color=PALETTE["AGROVOC"], linewidth=0.55, mutation_scale=4)
    ax.text(0.12, -2.58, "Dashed links: Q1 semantic-alignment evidence", fontsize=4.4, color=MUTED)


def figure_complete_main(q1_rows: list[dict[str, str]], contract: dict[str, Any]) -> None:
    fig = plt.figure(figsize=(7.2, 7.9))
    grid = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.22, height_ratios=[0.92, 1.08])
    ax_release = fig.add_subplot(grid[0, 0])
    ax_er = fig.add_subplot(grid[0, 1])
    ax_projection = fig.add_subplot(grid[1, 0])
    ax_chain = fig.add_subplot(grid[1, 1])
    draw_release_summary(ax_release)
    draw_apvma_er(ax_er, compact=True)
    draw_bipartite(ax_projection, contract, compact=True)
    ax_projection.set_title("Cross-jurisdiction shared-entity structure", loc="left", fontsize=8, fontweight="bold")
    draw_multisite_chain_compact(ax_chain, q1_rows)
    for label, ax in zip(("a", "b", "c", "d"), (ax_release, ax_er, ax_projection, ax_chain)):
        panel_label(ax, label)
    fig.text(
        0.5,
        0.012,
        f"PestKG release {RELEASE_ID} | official-source records, jurisdictional graphs, and external semantic alignment",
        ha="center",
        fontsize=5.2,
        color=MUTED,
    )
    save_figure(fig, "figure_08_complete_main_figure")


def write_captions(source_mode: str, contract: dict[str, Any]) -> None:
    selected_count = len(contract["active_nodes"])
    captions_en = f"""# Figure captions (English)

## Figure 1 | PestKG release landscape

Distribution of official-source records, graph scale, and source-field completeness across 12 jurisdictions in PestKG release {RELEASE_ID}. Bubble area in panel b scales with the square root of source-record count. Empty official fields are treated as unavailable, not as translation failures.

## Figure 2 | APVMA single-website knowledge graph

Bounded subgraph centered on APVMA registration 84962 (Fortin Herbicide). The graph preserves country-specific registration, product, registration-use, active-ingredient, and crop nodes. All 48 released crop contexts are drawn; eight representative crop labels are shown for legibility. Dotted provenance edges are visual annotations and are not PestKG predicates. Graph source mode: {source_mode}.

## Figure 3 | PestKG federation through ChEBI and AGROVOC

Projection of registration-use results from jurisdictions represented in the released Q1 table. Country-local crop and active-ingredient labels remain separate and connect to shared AGROVOC and ChEBI identifiers through semantic-alignment evidence. Because Q1 does not retain the row-level predicate, the figure does not infer whether an alignment is exactMatch or lexicalAlignment.

## Figure 4 | Integrated PestKG workflow

Combined overview linking release-scale statistics, an official-site jurisdictional subgraph, and cross-jurisdiction semantic federation. Figures 1-3 provide higher-resolution standalone alternatives.

## Figure 5 | APVMA entity-relationship model

Entity-relationship view of the APVMA PubCRIS portion of PestKG. Rectangles denote released entity classes, diamonds denote predicates observed in the APVMA sample, and ellipses denote retained fields or traceable example values. The diagram preserves the distinction between Registration and RegistrationUse and retains node_id, source_record_id, and source_url provenance fields.

## Figure 6 | Bipartite network and graph projections

Network representation of four jurisdictions and {selected_count} shared ChEBI active-ingredient entities selected by jurisdiction coverage and registration-use count from Q1. Panel a is the jurisdiction-entity bipartite graph; edge width scales logarithmically with registration-use count. Panel b projects the bipartite graph onto jurisdictions, with edge labels showing the number of selected shared entities. Panel c projects it onto ChEBI entities; edges require co-occurrence in at least two jurisdictions. Source tables report every plotted node, edge, and projection weight.

## Figure 7 | Multi-site federation to external knowledge bases

Official pesticide registers for mainland China (ICAMA), Taiwan (APHIA), Japan (FAMIC ACIS), and Korea (RDA PSIS) feed independent jurisdictional PestKG graphs. Country-local chlorothalonil and crop entities remain distinct and connect through Q1 semantic-alignment evidence to ChEBI:3639 and the corresponding AGROVOC banana or cauliflower concepts. Dashed edges are derived alignment evidence, not asserted cross-country identity.

## Figure 8 | Complete PestKG main figure

Integrated double-column figure combining release-scale statistics, the APVMA entity-relationship model, the jurisdiction-shared entity network, and four-site federation through ChEBI and AGROVOC. All panels use frozen release {RELEASE_ID}; browser-scale full-graph loading is not implied.
"""
    captions_zh = f"""# 图注（中文）

## 图 1 | PestKG 发布版数据概览

展示 PestKG 发布版 {RELEASE_ID} 在 12 个司法辖区的官方来源记录量、图谱规模和源字段完整度。b 面板气泡面积按源记录数平方根缩放。官方字段缺失仅表示数据不可用，不视为翻译失败。

## 图 2 | APVMA 单网站知识图谱

以 APVMA 登记号 84962（Fortin Herbicide）为中心的受限子图。图中保留国家本地的登记、产品、登记用途、有效成分和作物节点。发布样例中的 48 个作物情境全部绘制，为保证可读性仅标注 8 个代表性作物。点状来源边仅用于可视化，不属于 PestKG 谓词。图谱数据模式：{source_mode}。

## 图 3 | PestKG 经 ChEBI 和 AGROVOC 的联邦连接

依据发布版 Q1 表展示多个司法辖区的登记用途结果。各国本地作物和有效成分实体保持独立，通过语义对齐证据连接到共享 AGROVOC 和 ChEBI 标识符。由于 Q1 未保存逐行对齐谓词，本图不推断某条关系具体属于 exactMatch 还是 lexicalAlignment。

## 图 4 | PestKG 综合流程

综合展示发布规模统计、官方站点对应的国家子图，以及跨司法辖区语义联邦。图 1-3 提供相应的高分辨率独立版本。

## 图 5 | APVMA 实体-关系模型

PestKG 中 APVMA PubCRIS 部分的实体-关系视图。矩形表示已发布实体类型，菱形表示 APVMA 样例中实际出现的谓词，椭圆表示保留字段或可追溯实例值。模型明确区分 Registration 与 RegistrationUse，并保留 node_id、source_record_id 和 source_url 来源字段。

## 图 6 | 二部网络及图投影

依据 Q1 的司法辖区覆盖度和登记用途数量，展示 4 个司法辖区与 {selected_count} 个共享 ChEBI 有效成分实体。a 为司法辖区-实体二部网络，边宽按登记用途数的对数缩放；b 为司法辖区投影，边上数字表示选定实体中的共享数量；c 为 ChEBI 实体投影，仅保留至少在两个司法辖区共同出现的连接。绘图数据表给出全部节点、边和投影权重。

## 图 7 | 多官方网站到外部知识库的联邦串联

中国大陆 ICAMA、中国台湾 APHIA、日本 FAMIC ACIS 和韩国 RDA PSIS 的官方农药登记数据分别进入独立的国家 PestKG 子图。本地百菌清和作物实体不直接跨国合并，而是依据 Q1 语义对齐证据连接 ChEBI:3639 以及 AGROVOC 中的香蕉或花椰菜概念。虚线为派生对齐证据，不代表直接断言跨国实体同一。

## 图 8 | PestKG 完整论文主图

双栏综合图，组合发布规模统计、APVMA 实体-关系模型、司法辖区-共享实体网络，以及四个官方网站经 ChEBI 和 AGROVOC 的语义联邦。全部面板均基于冻结发布版 {RELEASE_ID}，不暗示浏览器一次性加载完整图谱。
"""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "CAPTIONS.md").write_text(captions_en, encoding="utf-8")
    (OUTPUT_ROOT / "CAPTIONS_EN.md").write_text(captions_en, encoding="utf-8")
    (OUTPUT_ROOT / "CAPTIONS_ZH.md").write_text(captions_zh, encoding="utf-8")


def write_manifest(source_mode: str) -> None:
    input_paths = [
        RELEASE_ROOT / "release.json",
        RELEASE_ROOT / "countries.json",
        SAMPLE_ROOT / "nodes.csv",
        SAMPLE_ROOT / "edges.csv",
        SAMPLE_ROOT / "comparisons" / "q1.csv",
    ]
    output_paths = sorted(
        [path for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "FIGURE_MANIFEST.json"]
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
        "outputs": [
            {
                "file": str(path.relative_to(OUTPUT_ROOT)).replace("\\", "/"),
                "format": path.suffix.lstrip("."),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "png_dpi": 600 if path.suffix.lower() == ".png" else None,
            }
            for path in output_paths
        ],
    }
    (OUTPUT_ROOT / "FIGURE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate extended PestKG publication figures.")
    parser.add_argument("--neo4j-uri")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="pestkg-paper")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_style()
    source_mode = "release CSV fallback"
    q1_rows = read_csv(SAMPLE_ROOT / "comparisons" / "q1.csv")
    if args.neo4j_uri:
        try:
            nodes, edges = neo4j_neighborhood(
                args.neo4j_uri,
                args.neo4j_user,
                args.neo4j_password,
                FORTIN_PRODUCT_ID,
            )
            neo_rows = q1_from_neo4j(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
            if not neo_rows:
                raise RuntimeError("Neo4j returned no Q1 projection rows.")
            q1_rows = neo_rows
            source_mode = "Neo4j PaperSample and PaperProjection"
        except Exception as exc:
            print(f"Neo4j unavailable; using frozen release CSV: {exc}")
            nodes, edges = file_neighborhood(FORTIN_PRODUCT_ID)
    else:
        nodes, edges = file_neighborhood(FORTIN_PRODUCT_ID)

    if not nodes or not edges:
        raise RuntimeError("APVMA neighborhood is empty.")
    contract = projection_contract(q1_rows)
    write_projection_tables(contract)
    figure_apvma_er()
    figure_bipartite_projection(contract)
    figure_multisite_chain(q1_rows)
    figure_complete_main(q1_rows, contract)
    write_captions(source_mode, contract)
    write_manifest(source_mode)
    print(f"Generated extended figures in {OUTPUT_ROOT}")
    print(f"Graph source mode: {source_mode}")


if __name__ == "__main__":
    main()
