from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Any

import duckdb

try:
    from .validate_analytics import parquet_expression
except ImportError:
    from validate_analytics import parquet_expression


NODE_FIELDS = [
    "id",
    "type",
    "label_original",
    "label_en",
    "jurisdiction",
    "source_record_id",
    "source_url",
    "properties_json",
]
EDGE_FIELDS = [
    "id",
    "start_id",
    "predicate",
    "end_id",
    "jurisdiction",
    "source_record_id",
    "source_url",
    "properties_json",
]
QUESTION_FILES = {
    "q1": "Q1_crop_active_ingredients_cross_country.csv.gz",
    "q2": "Q2_same_target_products_cross_country.csv.gz",
    "q3": "Q3_shared_crop_target_combinations.csv.gz",
    "q4": "Q4_active_ingredient_formulations.csv.gz",
    "q5": "Q5_active_ingredient_country_use_profiles.csv.gz",
}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_values(values: set[str]) -> str:
    if not values:
        return "NULL"
    return ",".join(sql_string(value) for value in sorted(values))


def normalize_predicate(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def build_release_sample(
    release_dir: Path,
    *,
    uses_per_jurisdiction: int = 2,
    question_limit: int = 200,
) -> Path:
    if uses_per_jurisdiction < 1:
        raise ValueError("uses_per_jurisdiction must be at least 1")
    analytics = release_dir / "analytics"
    nodes_path = analytics / "nodes"
    edges_path = analytics / "edges"
    uses_path = analytics / "registration_uses"
    if not uses_path.exists():
        nodes_path = analytics / "nodes.parquet"
        edges_path = analytics / "edges.parquet"
        uses_path = analytics / "registration_uses.parquet"
    if not nodes_path.exists() or not edges_path.exists() or not uses_path.exists():
        raise FileNotFoundError("Materialized analytics are required to build samples")

    connection = duckdb.connect()
    try:
        use_cursor = connection.execute(
            "SELECT * EXCLUDE (sample_rank) FROM ("
            "SELECT *, row_number() OVER (PARTITION BY jurisdiction ORDER BY use_id) AS sample_rank "
            f"FROM {parquet_expression(uses_path)}) WHERE sample_rank <= ? "
            "ORDER BY jurisdiction, use_id",
            [uses_per_jurisdiction],
        )
        use_columns = [column[0] for column in use_cursor.description]
        uses = [dict(zip(use_columns, row, strict=True)) for row in use_cursor.fetchall()]
        use_ids = {str(row["use_id"]) for row in uses}
        if not use_ids:
            raise RuntimeError("No RegistrationUse rows were available for the sample")

        edge_cursor = connection.execute(
            f"SELECT {','.join(EDGE_FIELDS)} FROM {parquet_expression(edges_path)} "
            f"WHERE start_id IN ({sql_values(use_ids)}) OR end_id IN ({sql_values(use_ids)})"
        )
        edge_columns = [column[0] for column in edge_cursor.description]
        edges = [dict(zip(edge_columns, row, strict=True)) for row in edge_cursor.fetchall()]
        registration_ids = {
            str(edge["start_id"])
            for edge in edges
            if normalize_predicate(str(edge["predicate"])) == "hasregistrationuse"
        }
        if registration_ids:
            related_cursor = connection.execute(
                f"SELECT {','.join(EDGE_FIELDS)} FROM {parquet_expression(edges_path)} "
                f"WHERE start_id IN ({sql_values(registration_ids)}) "
                f"OR end_id IN ({sql_values(registration_ids)})"
            )
            related_columns = [column[0] for column in related_cursor.description]
            by_id = {str(edge["id"]): edge for edge in edges}
            for row in related_cursor.fetchall():
                edge = dict(zip(related_columns, row, strict=True))
                by_id[str(edge["id"])] = edge
            edges = list(by_id.values())

        node_ids = {
            str(identifier)
            for edge in edges
            for identifier in (edge["start_id"], edge["end_id"])
        }
        jurisdictions = {str(row["jurisdiction"]) for row in uses}
        node_cursor = connection.execute(
            f"SELECT {','.join(NODE_FIELDS)} FROM {parquet_expression(nodes_path)} "
            f"WHERE id IN ({sql_values(node_ids)}) OR "
            "(type IN ('CountryJurisdiction', 'RegulatoryAgency') "
            f"AND jurisdiction IN ({sql_values(jurisdictions)}))"
        )
        node_columns = [column[0] for column in node_cursor.description]
        nodes = [dict(zip(node_columns, row, strict=True)) for row in node_cursor.fetchall()]
        available_nodes = {str(node["id"]) for node in nodes}
        edges = [
            edge
            for edge in edges
            if str(edge["start_id"]) in available_nodes
            and str(edge["end_id"]) in available_nodes
        ]
    finally:
        connection.close()

    sample_dir = release_dir / "sample"
    if sample_dir.exists():
        raise FileExistsError(f"Sample output already exists: {sample_dir}")
    write_csv(sample_dir / "nodes.csv", nodes, NODE_FIELDS)
    write_csv(sample_dir / "edges.csv", edges, EDGE_FIELDS)
    write_csv(sample_dir / "registration_uses.csv", uses, use_columns)

    question_root = release_dir / "06_competency_questions"
    for question, filename in QUESTION_FILES.items():
        source = question_root / filename
        if not source.is_file():
            continue
        with gzip.open(source, "rt", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for row in reader:
                rows.append(row)
                if len(rows) >= question_limit:
                    break
        if rows:
            write_csv(
                sample_dir / "comparisons" / f"{question}.csv",
                rows,
                list(rows[0]),
            )
    (sample_dir / "sample.json").write_text(
        json.dumps(
            {
                "uses_per_jurisdiction": uses_per_jurisdiction,
                "nodes": len(nodes),
                "edges": len(edges),
                "registration_uses": len(uses),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return sample_dir
