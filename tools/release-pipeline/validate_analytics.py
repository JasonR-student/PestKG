from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb


def parquet_expression(path: Path) -> str:
    source = path / "**/*.parquet" if path.is_dir() else path
    escaped = str(source.resolve()).replace("\\", "/").replace("'", "''")
    return f"read_parquet('{escaped}', hive_partitioning=true)"


def validate_analytics(release_dir: Path) -> dict[str, Any]:
    analytics = release_dir / "analytics"
    nodes_path = analytics / "nodes"
    edges_path = analytics / "edges"
    uses_path = analytics / "registration_uses"
    if not nodes_path.exists():
        nodes_path = analytics / "nodes.parquet"
        edges_path = analytics / "edges.parquet"
        uses_path = analytics / "registration_uses.parquet"

    with (release_dir / "06_neo4j_import/preparation_report.json").open(
        "r", encoding="utf-8"
    ) as handle:
        preparation = json.load(handle)
    with (release_dir / "release.json").open("r", encoding="utf-8") as handle:
        release = json.load(handle)
    expected = {
        "nodes": int(preparation["nodes"]),
        "edges": int(preparation["relationships"]),
        "registration_uses": int(preparation["node_types"]["RegistrationUse"]),
        "jurisdictions": int(release["inventory"]["jurisdictions"]),
    }

    connection = duckdb.connect()
    connection.execute("PRAGMA threads=4")
    connection.execute("PRAGMA memory_limit='12GB'")
    connection.execute(
        f"CREATE VIEW nodes AS SELECT * FROM {parquet_expression(nodes_path)}"
    )
    connection.execute(
        f"CREATE VIEW edges AS SELECT * FROM {parquet_expression(edges_path)}"
    )
    connection.execute(
        f"CREATE VIEW uses AS SELECT * FROM {parquet_expression(uses_path)}"
    )
    checks = {
        "nodes": connection.sql("SELECT count(*) FROM nodes").fetchone()[0],
        "edges": connection.sql("SELECT count(*) FROM edges").fetchone()[0],
        "registration_uses": connection.sql("SELECT count(*) FROM uses").fetchone()[0],
        "jurisdictions": connection.sql(
            "SELECT count(DISTINCT jurisdiction) FROM uses"
        ).fetchone()[0],
        "missing_use_provenance": connection.sql(
            "SELECT count(*) FROM uses WHERE source_record_id = '' OR source_url = ''"
        ).fetchone()[0],
        "duplicate_alignments": connection.sql(
            "SELECT count(*) FROM ("
            "SELECT start_id, predicate, end_id, count(*) AS count "
            "FROM edges WHERE predicate IN ('EXACT_MATCH', 'LEXICAL_ALIGNMENT') "
            "GROUP BY ALL HAVING count > 1)"
        ).fetchone()[0],
        "broken_edges": connection.sql(
            "SELECT count(*) FROM edges e "
            "LEFT JOIN nodes s ON s.id = e.start_id "
            "LEFT JOIN nodes t ON t.id = e.end_id "
            "WHERE s.id IS NULL OR t.id IS NULL"
        ).fetchone()[0],
        "cross_country_non_alignment": connection.sql(
            "SELECT count(*) FROM edges e "
            "JOIN nodes s ON s.id = e.start_id "
            "JOIN nodes t ON t.id = e.end_id "
            "WHERE e.predicate NOT IN ('EXACT_MATCH', 'LEXICAL_ALIGNMENT') "
            "AND s.jurisdiction <> '' AND t.jurisdiction <> '' "
            "AND s.jurisdiction <> t.jurisdiction"
        ).fetchone()[0],
    }
    connection.close()

    failures = {
        key: {"expected": value, "actual": checks[key]}
        for key, value in expected.items()
        if checks[key] != value
    }
    invariant_failures = {
        key: checks[key]
        for key in (
            "missing_use_provenance",
            "duplicate_alignments",
            "broken_edges",
            "cross_country_non_alignment",
        )
        if checks[key] != 0
    }
    if failures or invariant_failures:
        raise RuntimeError(
            f"Analytics validation failed: counts={failures}, invariants={invariant_failures}"
        )
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_analytics(args.release_dir), indent=2))


if __name__ == "__main__":
    main()
