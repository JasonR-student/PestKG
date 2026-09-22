from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from archive_io import archive_names, read_csv_rows, read_json


ROOT = "multicountry_pesticide_kg_research/release/2026.08.3_federated"
COUNTRY_META = {
    "AU": ("AUS", "036"),
    "CN": ("CHN", "156"),
    "TW": ("TWN", "158"),
    "GB": ("GBR", "826"),
    "GB-NI": ("GBR", "826"),
    "HU": ("HUN", "348"),
    "IE": ("IRL", "372"),
    "JP": ("JPN", "392"),
    "KR": ("KOR", "410"),
    "NL": ("NLD", "528"),
    "NZ": ("NZL", "554"),
    "US": ("USA", "840"),
}
QUESTION_FILES = {
    "q1": "Q1_crop_active_ingredients_cross_country.csv.gz",
    "q2": "Q2_same_target_products_cross_country.csv.gz",
    "q3": "Q3_shared_crop_target_combinations.csv.gz",
    "q4": "Q4_active_ingredient_formulations.csv.gz",
    "q5": "Q5_active_ingredient_country_use_profiles.csv.gz",
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def graph_members(names: list[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    prefix = f"{ROOT}/01_country_graphs/"
    for name in names:
        if not name.startswith(prefix) or not name.endswith(("nodes.csv.gz", "edges.csv.gz")):
            continue
        parts = name[len(prefix) :].split("/")
        if len(parts) != 3:
            continue
        folder_jurisdiction, _, filename = parts
        key = "TW" if folder_jurisdiction == "CN-TW" else folder_jurisdiction
        result.setdefault(key, {})["nodes" if filename.startswith("nodes") else "edges"] = name
    return result


def select_use_rows(archive: Path, edge_member: str, count: int) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in read_csv_rows(archive, edge_member, gzipped=True):
        if row["predicate"] == "usesProduct" and row["start_id"] not in seen:
            seen.add(row["start_id"])
            result.append(row)
            if len(result) == count:
                break
    return result


def sample_country_graph(
    archive: Path,
    members: dict[str, str],
    use_count: int,
    max_edge_scan: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, Any]]]:
    selected_product_edges = select_use_rows(archive, members["edges"], use_count)
    selected_uses = {row["start_id"] for row in selected_product_edges}
    selected_ids = set(selected_uses)
    edges: list[dict[str, str]] = list(selected_product_edges)
    for edge in selected_product_edges:
        selected_ids.update((edge["start_id"], edge["end_id"]))
    registration_ids: set[str] = set()

    for index, row in enumerate(read_csv_rows(archive, members["edges"], gzipped=True)):
        related = row["start_id"] in selected_uses or row["end_id"] in selected_uses
        if related:
            edges.append(row)
            selected_ids.update((row["start_id"], row["end_id"]))
            if row["predicate"] == "hasRegistrationUse":
                registration_ids.add(row["start_id"])
        if index >= max_edge_scan and edges:
            break

    if registration_ids:
        for index, row in enumerate(read_csv_rows(archive, members["edges"], gzipped=True)):
            if row["start_id"] in registration_ids or row["end_id"] in registration_ids:
                if row["id"] not in {edge["id"] for edge in edges}:
                    edges.append(row)
                    selected_ids.update((row["start_id"], row["end_id"]))
            if index >= max_edge_scan:
                break

    nodes: list[dict[str, str]] = []
    system_types = {"CountryJurisdiction", "RegulatoryAgency"}
    found_system_types: set[str] = set()
    for row in read_csv_rows(archive, members["nodes"], gzipped=True):
        if row["id"] in selected_ids or (
            row["type"] in system_types and row["type"] not in found_system_types
        ):
            nodes.append(row)
            selected_ids.add(row["id"])
            found_system_types.add(row["type"])

    node_map = {row["id"]: row for row in nodes}
    outgoing: dict[str, list[dict[str, str]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        outgoing[edge["start_id"]].append(edge)
        incoming[edge["end_id"]].append(edge)

    def related(use_id: str, predicate: str) -> list[dict[str, str]]:
        values = []
        for edge in outgoing[use_id]:
            if edge["predicate"] == predicate and edge["end_id"] in node_map:
                values.append(node_map[edge["end_id"]])
        return values

    uses: list[dict[str, Any]] = []
    for use_id in selected_uses:
        use = node_map.get(use_id)
        if not use:
            continue
        products = related(use_id, "usesProduct")
        ingredients = related(use_id, "hasActiveIngredient")
        crops = related(use_id, "registeredForCrop")
        targets = related(use_id, "registeredForTarget")
        formulations = related(use_id, "hasFormulation")
        registrations = [
            node_map[edge["start_id"]]
            for edge in incoming[use_id]
            if edge["predicate"] == "hasRegistrationUse" and edge["start_id"] in node_map
        ]
        registration_properties = {}
        if registrations:
            try:
                registration_properties = json.loads(registrations[0]["properties_json"] or "{}")
            except json.JSONDecodeError:
                pass
        use_properties = json.loads(use["properties_json"] or "{}")

        def entities(values: list[dict[str, str]]) -> list[dict[str, str]]:
            return [
                {
                    "id": value["id"],
                    "label_original": value["label_original"],
                    "label_en": value["label_en"],
                }
                for value in values
            ]

        product = products[0] if products else {}
        search_values = [
            product.get("label_original", ""),
            product.get("label_en", ""),
            *[item["label_original"] for item in ingredients + crops + targets + formulations],
            *[item["label_en"] for item in ingredients + crops + targets + formulations],
        ]
        uses.append(
            {
                "use_id": use_id,
                "jurisdiction": use["jurisdiction"],
                "product_id": product.get("id", ""),
                "product_label_original": product.get("label_original", ""),
                "product_label_en": product.get("label_en", ""),
                "product_label_search": " | ".join(search_values[:2]),
                "active_ingredients_json": json.dumps(entities(ingredients), ensure_ascii=False),
                "active_ingredients_search": " | ".join(
                    item["label_original"] or item["label_en"] for item in ingredients
                ),
                "crops_json": json.dumps(entities(crops), ensure_ascii=False),
                "crops_search": " | ".join(item["label_original"] or item["label_en"] for item in crops),
                "targets_json": json.dumps(entities(targets), ensure_ascii=False),
                "targets_search": " | ".join(
                    item["label_original"] or item["label_en"] for item in targets
                ),
                "formulations_json": json.dumps(entities(formulations), ensure_ascii=False),
                "formulations_search": " | ".join(
                    item["label_original"] or item["label_en"] for item in formulations
                ),
                "registration_status": registration_properties.get("status_original", ""),
                "registration_date": registration_properties.get("registration_date", ""),
                "expiry_date": registration_properties.get("expiry_date", ""),
                "pairing_status": use_properties.get("pairing_status", ""),
                "source_record_id": use["source_record_id"],
                "source_url": use["source_url"],
            }
        )
    return nodes, edges, uses


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--uses-per-country", type=int, default=2)
    parser.add_argument("--max-edge-scan", type=int, default=400_000)
    args = parser.parse_args()

    build_report = read_json(args.archive, f"{ROOT}/04_validation/federated_build_report.json")
    inventory = read_json(args.archive, f"{ROOT}/04_validation/entity_relation_inventory.json")
    final_report = read_json(args.archive, f"{ROOT}/04_validation/final_integrity_report.json")
    coverage_rows = list(
        read_csv_rows(args.archive, f"{ROOT}/04_validation/semantic_coverage_corrected.csv")
    )
    coverage_by_country = {row["jurisdiction"]: row for row in coverage_rows}

    countries = []
    for graph in build_report["country_manifests"]:
        jurisdiction = graph["jurisdiction"]
        iso3, map_id = COUNTRY_META[jurisdiction]
        countries.append(
            {
                **graph,
                "iso3": iso3,
                "map_id": map_id,
                "coverage": coverage_by_country.get(jurisdiction, {}),
            }
        )

    release = {
        "release_id": "2026.08.3_federated",
        "title": "Federated multicountry pesticide registration knowledge graphs",
        "published_at": "2026-08-24",
        "cutoff": build_report["cutoff"],
        "status": build_report["status"],
        "license": "CC BY 4.0 for project-derived data",
        "inventory": {
            "jurisdictions": final_report["country_graphs"],
            "source_records": sum(item["source_rows"] for item in countries),
            "country_nodes": final_report["country_nodes"],
            "country_edges": final_report["country_edges"],
            "shared_nodes": final_report["shared_external_nodes"],
            "alignment_edges": final_report["unique_alignment_edges"],
        },
        "node_types": inventory["country_node_types"],
        "relation_types": inventory["country_relation_types"],
        "coverage": coverage_rows,
        "integrity": final_report,
    }
    schema = {
        "node_fields": [
            "id",
            "type",
            "label_original",
            "label_en",
            "jurisdiction",
            "source_record_id",
            "source_url",
            "properties_json",
        ],
        "edge_fields": [
            "id",
            "start_id",
            "predicate",
            "end_id",
            "jurisdiction",
            "source_record_id",
            "source_url",
            "properties_json",
        ],
        "node_types": inventory["country_node_types"],
        "relation_types": inventory["country_relation_types"],
        "federation_predicates": inventory["federation_predicates"],
        "rules": {
            "country_local_identity": "Local regulatory entities are never merged across jurisdictions.",
            "cross_country_alignment": "Cross-country traversal uses exactMatch or lexicalAlignment.",
            "formal_crop_target_pair": "Formal comparison defaults to official_pair_asserted.",
        },
    }

    write_json(args.output / "release.json", release)
    write_json(args.output / "countries.json", countries)
    write_json(args.output / "schema.json", schema)

    members = graph_members(archive_names(args.archive))
    all_nodes: list[dict[str, str]] = []
    all_edges: list[dict[str, str]] = []
    all_uses: list[dict[str, Any]] = []
    for country in countries:
        jurisdiction = country["jurisdiction"]
        if jurisdiction not in members:
            continue
        nodes, edges, uses = sample_country_graph(
            args.archive,
            members[jurisdiction],
            args.uses_per_country,
            args.max_edge_scan,
        )
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        all_uses.extend(uses)

    write_csv(
        args.output / "sample/nodes.csv",
        all_nodes,
        [
            "id",
            "type",
            "label_original",
            "label_en",
            "jurisdiction",
            "source_record_id",
            "source_url",
            "properties_json",
        ],
    )
    write_csv(
        args.output / "sample/edges.csv",
        all_edges,
        [
            "id",
            "start_id",
            "predicate",
            "end_id",
            "jurisdiction",
            "source_record_id",
            "source_url",
            "properties_json",
        ],
    )
    use_fields = list(all_uses[0]) if all_uses else []
    write_csv(args.output / "sample/registration_uses.csv", all_uses, use_fields)

    question_root = f"{ROOT}/06_competency_questions"
    for question, filename in QUESTION_FILES.items():
        rows = []
        for row in read_csv_rows(args.archive, f"{question_root}/{filename}", gzipped=True):
            rows.append(row)
            if len(rows) == 200:
                break
        if rows:
            write_csv(
                args.output / f"sample/comparisons/{question}.csv",
                rows,
                list(rows[0]),
            )


if __name__ == "__main__":
    main()
