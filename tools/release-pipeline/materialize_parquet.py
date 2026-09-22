from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import duckdb


def sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''").replace("\\", "/")


def materialize(
    release_dir: Path,
    *,
    threads: int | None = None,
    memory_limit: str | None = None,
    temp_directory: Path | None = None,
) -> Path:
    import_dir = release_dir / "06_neo4j_import"
    nodes_csv = import_dir / "nodes.csv.gz"
    relationships_csv = import_dir / "relationships.csv.gz"
    if not nodes_csv.exists() or not relationships_csv.exists():
        raise FileNotFoundError("Neo4j import package is missing from the release")

    analytics_dir = release_dir / "analytics"
    if analytics_dir.exists():
        raise FileExistsError(
            f"Analytics output already exists for immutable release: {analytics_dir}"
        )
    analytics_dir.mkdir(parents=True)
    database = analytics_dir / "build.duckdb"
    configured_threads = threads or int(
        os.environ.get("PESTKG_PIPELINE_THREADS", min(4, os.cpu_count() or 1))
    )
    configured_memory = memory_limit or os.environ.get(
        "PESTKG_PIPELINE_MEMORY_LIMIT", "4GB"
    )
    if configured_threads < 1:
        raise ValueError("DuckDB threads must be at least 1")
    scratch = temp_directory or Path(
        os.environ.get("PESTKG_PIPELINE_TEMP_DIR", analytics_dir / "tmp")
    )
    scratch.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))
    try:
        connection.execute(f"PRAGMA threads={configured_threads}")
        escaped_memory = configured_memory.replace("'", "''")
        connection.execute(f"PRAGMA memory_limit='{escaped_memory}'")
        connection.execute(
            f"PRAGMA temp_directory='{sql_path(scratch)}'"
        )

        connection.execute(
            f"""
            CREATE OR REPLACE TABLE nodes AS
            SELECT
                "nodeId:ID(PesticideKG)" AS id,
                regexp_extract(":LABEL", '([^;]+)$', 1) AS type,
                coalesce(labelOriginal, '') AS label_original,
                coalesce(labelEnglish, '') AS label_en,
                coalesce(jurisdiction, '') AS jurisdiction,
                coalesce(sourceRecordId, '') AS source_record_id,
                coalesce(sourceUrl, '') AS source_url,
                coalesce(propertiesJson, '{{}}') AS properties_json
            FROM read_csv_auto(
                '{sql_path(nodes_csv)}',
                header=true,
                all_varchar=true,
                normalize_names=false,
                sample_size=200000
            )
            """
        )
        connection.execute(
            f"""
            CREATE OR REPLACE TABLE edges AS
            SELECT
                relationshipId AS id,
                ":START_ID(PesticideKG)" AS start_id,
                ":TYPE" AS predicate,
                ":END_ID(PesticideKG)" AS end_id,
                coalesce(jurisdiction, '') AS jurisdiction,
                coalesce(sourceRecordId, '') AS source_record_id,
                coalesce(sourceUrl, '') AS source_url,
                coalesce(propertiesJson, '{{}}') AS properties_json
            FROM read_csv_auto(
                '{sql_path(relationships_csv)}',
                header=true,
                all_varchar=true,
                normalize_names=false,
                sample_size=200000
            )
            """
        )

        connection.execute(
            """
            CREATE OR REPLACE TABLE registration_uses AS
        WITH
        uses AS (
            SELECT * FROM nodes WHERE type = 'RegistrationUse'
        ),
        product_links AS (
            SELECT e.start_id AS use_id, n.id, n.label_original, n.label_en
            FROM edges e JOIN nodes n ON n.id = e.end_id
            WHERE e.predicate = 'USES_PRODUCT'
        ),
        ingredient_links AS (
            SELECT e.start_id AS use_id,
                   to_json(list(DISTINCT struct_pack(
                       id := n.id,
                       label_original := n.label_original,
                       label_en := n.label_en
                   ))) AS values_json,
                   string_agg(DISTINCT coalesce(nullif(n.label_en, ''), n.label_original), ' | ') AS search
            FROM edges e JOIN nodes n ON n.id = e.end_id
            WHERE e.predicate = 'HAS_ACTIVE_INGREDIENT'
            GROUP BY e.start_id
        ),
        crop_links AS (
            SELECT e.start_id AS use_id,
                   to_json(list(DISTINCT struct_pack(
                       id := n.id,
                       label_original := n.label_original,
                       label_en := n.label_en
                   ))) AS values_json,
                   string_agg(DISTINCT coalesce(nullif(n.label_en, ''), n.label_original), ' | ') AS search
            FROM edges e JOIN nodes n ON n.id = e.end_id
            WHERE e.predicate = 'REGISTERED_FOR_CROP'
            GROUP BY e.start_id
        ),
        target_links AS (
            SELECT e.start_id AS use_id,
                   to_json(list(DISTINCT struct_pack(
                       id := n.id,
                       label_original := n.label_original,
                       label_en := n.label_en
                   ))) AS values_json,
                   string_agg(DISTINCT coalesce(nullif(n.label_en, ''), n.label_original), ' | ') AS search
            FROM edges e JOIN nodes n ON n.id = e.end_id
            WHERE e.predicate = 'REGISTERED_FOR_TARGET'
            GROUP BY e.start_id
        ),
        formulation_links AS (
            SELECT e.start_id AS use_id,
                   to_json(list(DISTINCT struct_pack(
                       id := n.id,
                       label_original := n.label_original,
                       label_en := n.label_en
                   ))) AS values_json,
                   string_agg(DISTINCT coalesce(nullif(n.label_en, ''), n.label_original), ' | ') AS search
            FROM edges e JOIN nodes n ON n.id = e.end_id
            WHERE e.predicate = 'HAS_FORMULATION'
            GROUP BY e.start_id
        ),
        registration_links AS (
            SELECT e.end_id AS use_id,
                   any_value(json_extract_string(n.properties_json, '$.status_original')) AS registration_status,
                   any_value(json_extract_string(n.properties_json, '$.registration_date')) AS registration_date,
                   any_value(json_extract_string(n.properties_json, '$.expiry_date')) AS expiry_date
            FROM edges e JOIN nodes n ON n.id = e.start_id
            WHERE e.predicate = 'HAS_REGISTRATION_USE'
            GROUP BY e.end_id
        )
        SELECT
            u.id AS use_id,
            u.jurisdiction,
            coalesce(p.id, '') AS product_id,
            coalesce(p.label_original, '') AS product_label_original,
            coalesce(p.label_en, '') AS product_label_en,
            concat_ws(' | ', p.label_original, p.label_en) AS product_label_search,
            coalesce(ai.values_json, '[]') AS active_ingredients_json,
            coalesce(ai.search, '') AS active_ingredients_search,
            coalesce(c.values_json, '[]') AS crops_json,
            coalesce(c.search, '') AS crops_search,
            coalesce(t.values_json, '[]') AS targets_json,
            coalesce(t.search, '') AS targets_search,
            coalesce(f.values_json, '[]') AS formulations_json,
            coalesce(f.search, '') AS formulations_search,
            coalesce(r.registration_status, '') AS registration_status,
            coalesce(r.registration_date, '') AS registration_date,
            coalesce(r.expiry_date, '') AS expiry_date,
            coalesce(json_extract_string(u.properties_json, '$.pairing_status'), '') AS pairing_status,
            u.source_record_id,
            u.source_url
        FROM uses u
        LEFT JOIN product_links p ON p.use_id = u.id
        LEFT JOIN ingredient_links ai ON ai.use_id = u.id
        LEFT JOIN crop_links c ON c.use_id = u.id
        LEFT JOIN target_links t ON t.use_id = u.id
        LEFT JOIN formulation_links f ON f.use_id = u.id
        LEFT JOIN registration_links r ON r.use_id = u.id
            """
        )

        connection.execute(
            """
            CREATE OR REPLACE TABLE country_stats AS
            WITH
            node_counts AS (
                SELECT jurisdiction, count(*) AS nodes
                FROM nodes GROUP BY jurisdiction
            ),
            edge_counts AS (
                SELECT jurisdiction, count(*) AS edges
                FROM edges GROUP BY jurisdiction
            ),
            use_counts AS (
                SELECT jurisdiction, count(*) AS registration_uses
                FROM registration_uses GROUP BY jurisdiction
            )
            SELECT
                coalesce(n.jurisdiction, e.jurisdiction, u.jurisdiction) AS jurisdiction,
                coalesce(n.nodes, 0) AS nodes,
                coalesce(e.edges, 0) AS edges,
                coalesce(u.registration_uses, 0) AS registration_uses
            FROM node_counts n
            FULL OUTER JOIN edge_counts e USING (jurisdiction)
            FULL OUTER JOIN use_counts u USING (jurisdiction)
            ORDER BY jurisdiction
            """
        )

        for table in ("nodes", "edges", "registration_uses"):
            destination = analytics_dir / table
            connection.execute(
                f"COPY {table} TO '{sql_path(destination)}' "
                "(FORMAT PARQUET, COMPRESSION ZSTD, PARTITION_BY (jurisdiction), "
                "OVERWRITE_OR_IGNORE TRUE)"
            )
        connection.execute(
            f"COPY country_stats TO '{sql_path(analytics_dir / 'country_stats.parquet')}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    except Exception:
        connection.close()
        shutil.rmtree(analytics_dir, ignore_errors=True)
        raise
    else:
        connection.close()
        database.unlink(missing_ok=True)
        shutil.rmtree(scratch, ignore_errors=True)
    return analytics_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("--threads", type=int)
    parser.add_argument("--memory-limit")
    parser.add_argument("--temp-directory", type=Path)
    args = parser.parse_args()
    output = materialize(
        args.release_dir,
        threads=args.threads,
        memory_limit=args.memory_limit,
        temp_directory=args.temp_directory,
    )
    print(f"Materialized analytics tables: {output}")


if __name__ == "__main__":
    main()
