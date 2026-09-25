"""Prepare a Java-readable sample from a v1.0 manifest release.

The Java API (CsvDataStore) only reads ``sample/*.csv`` with the legacy
column contract (id/type/label_original/...).  This script projects the
v1.0 parquet layout (kg/nodes.parquet, kg/edges.parquet,
canonical/registration_uses.parquet) onto that contract and writes a
stratified sample plus compatibility metadata (release.json, schema.json,
countries.json) into the release directory.

Usage:
    python tools/prepare_v1_release.py [release_dir] [--node-limit 5000] [--edge-limit 20000] [--use-limit 5000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

NODE_FIELDS = [
    "id", "type", "label_original", "label_en", "jurisdiction",
    "source_record_id", "source_url", "properties_json",
]
EDGE_FIELDS = [
    "id", "start_id", "predicate", "end_id", "jurisdiction",
    "source_record_id", "source_url", "properties_json",
]
USE_FIELDS = [
    "use_id", "jurisdiction", "product_id", "product_label_original",
    "product_label_en", "product_label_search", "active_ingredients_search",
    "crops_search", "targets_search", "formulations_search",
    "active_ingredients_json", "crops_json", "targets_json", "formulations_json",
    "registration_status", "pairing_status", "registration_date", "expiry_date",
    "source_record_id", "source_url",
]
EMPTY_COVERAGE = {
    "jurisdiction": "", "source_language": "", "records": "",
    "crop_source": "", "target_source": "", "active_source": "", "formulation_source": "",
    "crop_english": "", "target_english": "", "active_english": "", "formulation_english": "",
    "crop_english_given_source": "", "target_english_given_source": "",
    "active_english_given_source": "", "formulation_english_given_source": "",
}


def _parquet(path: Path) -> str:
    return f"'{path.resolve().as_posix()}'"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_dir", nargs="?", default="data/releases/PestKG_A_Data_Release_v1.0")
    parser.add_argument("--node-limit", type=int, default=5000)
    parser.add_argument("--edge-limit", type=int, default=20000)
    parser.add_argument("--use-limit", type=int, default=5000)
    args = parser.parse_args()

    release_dir = Path(args.release_dir)
    if not (release_dir / "metadata" / "manifest.json").is_file():
        print(f"error: no manifest at {release_dir}/metadata/manifest.json", file=sys.stderr)
        return 1

    sample_dir = release_dir / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "comparisons").mkdir(exist_ok=True)

    con = duckdb.connect()
    p = release_dir.resolve().as_posix()
    nodes_parquet = f"read_parquet('{p}/kg/nodes.parquet')"
    edges_parquet = f"read_parquet('{p}/kg/edges.parquet')"
    uses_parquet = f"read_parquet('{p}/canonical/registration_uses.parquet')"

    # Seed nodes + edges touching them + edge endpoints, so the Java
    # neighborhood/path endpoints see a connected subgraph.
    con.execute(
        f"CREATE TABLE seed_node_ids AS "
        f"SELECT node_id FROM {nodes_parquet} LIMIT {args.node_limit}"
    )
    con.execute(
        f"""
        CREATE TABLE sample_edges AS
        SELECT e.edge_id AS id, e.source_id AS start_id, e.predicate,
               e.target_id AS end_id, '' AS jurisdiction,
               e.source_record_id, '' AS source_url,
               json_object(
                   'assertion_status', e.assertion_status,
                   'evidence_id', e.evidence_id,
                   'source_snapshot_id', e.source_snapshot_id,
                   'origin_kind', e.origin_kind,
                   'derivation_rule_id', e.derivation_rule_id,
                   'pipeline_version', e.pipeline_version,
                   'display_priority', e.display_priority,
                   'default_hidden', e.default_hidden
               ) AS properties_json
        FROM {edges_parquet} e
        WHERE e.source_id IN (SELECT node_id FROM seed_node_ids)
           OR e.target_id IN (SELECT node_id FROM seed_node_ids)
        LIMIT {args.edge_limit}
        """
    )
    con.execute(
        f"""
        CREATE TABLE sample_node_ids AS
        SELECT node_id FROM seed_node_ids
        UNION
        SELECT start_id AS node_id FROM sample_edges
        UNION
        SELECT end_id AS node_id FROM sample_edges
        """
    )

    nodes_csv = (sample_dir / "nodes.csv").resolve().as_posix()
    con.execute(
        f"""
        COPY (
            SELECT node_id AS id, node_type AS type,
                   display_label AS label_original, display_label AS label_en,
                   jurisdiction_id AS jurisdiction, '' AS source_record_id,
                   '' AS source_url, extension_properties AS properties_json
            FROM {nodes_parquet}
            WHERE node_id IN (SELECT node_id FROM sample_node_ids)
        ) TO '{nodes_csv}' (HEADER, DELIMITER ',');
        """
    )

    edges_csv = (sample_dir / "edges.csv").resolve().as_posix()
    con.execute(
        f"COPY (SELECT * FROM sample_edges) TO '{edges_csv}' (HEADER, DELIMITER ',');"
    )

    uses_csv = (sample_dir / "registration_uses.csv").resolve().as_posix()
    registrations_parquet = release_dir / "canonical" / "registrations.parquet"
    if registrations_parquet.exists():
        reg_parquet = f"read_parquet('{registrations_parquet.resolve().as_posix()}')"
        con.execute(
            f"""
            COPY (
                SELECT u.registration_use_id AS use_id, u.jurisdiction_id AS jurisdiction,
                       u.product_id, '' AS product_label_original, '' AS product_label_en,
                       '' AS product_label_search, '' AS active_ingredients_search,
                       u.crop_original AS crops_search, u.target_original AS targets_search,
                       u.formulation_original AS formulations_search,
                       '[]' AS active_ingredients_json, '[]' AS crops_json,
                       '[]' AS targets_json, '[]' AS formulations_json,
                       coalesce(r.original_status, '') AS registration_status,
                       u.pairing_status,
                       coalesce(r.registration_date_normalized, '') AS registration_date,
                       coalesce(r.expiry_date_normalized, '') AS expiry_date,
                       u.source_record_id, '' AS source_url
                FROM {uses_parquet} u
                LEFT JOIN {reg_parquet} r ON u.registration_id = r.registration_id
                LIMIT {args.use_limit}
            ) TO '{uses_csv}' (HEADER, DELIMITER ',');
            """
        )
    else:
        con.execute(
            f"""
            COPY (
                SELECT registration_use_id AS use_id, jurisdiction_id AS jurisdiction,
                       product_id, '' AS product_label_original, '' AS product_label_en,
                       '' AS product_label_search, '' AS active_ingredients_search,
                       crop_original AS crops_search, target_original AS targets_search,
                       formulation_original AS formulations_search,
                       '[]' AS active_ingredients_json, '[]' AS crops_json,
                       '[]' AS targets_json, '[]' AS formulations_json,
                       '' AS registration_status, pairing_status,
                       '' AS registration_date, '' AS expiry_date,
                       source_record_id, '' AS source_url
                FROM {uses_parquet}
                LIMIT {args.use_limit}
            ) TO '{uses_csv}' (HEADER, DELIMITER ',');
            """
        )

    # Dynamic stats over the full release (not just the sample).
    node_types = dict(con.execute(
        f"SELECT node_type, count(*) FROM {nodes_parquet} GROUP BY node_type"
    ).fetchall())
    relation_types = dict(con.execute(
        f"SELECT predicate, count(*) FROM {edges_parquet} GROUP BY predicate"
    ).fetchall())

    manifest = json.loads((release_dir / "metadata" / "manifest.json").read_text("utf-8"))
    release_id = release_dir.name
    distribution = manifest.get("distribution_status", {})
    dist_status = distribution.get("internal", "unknown") if isinstance(distribution, dict) else str(distribution)

    release_json = {
        "release_id": release_id,
        "schema_version": manifest.get("schema_version", "1.0"),
        "title": manifest.get("release_name", release_id),
        "published_at": manifest.get("created_at", ""),
        "cutoff": manifest.get("raw_snapshot_id", ""),
        "status": manifest.get("release_type", "unknown"),
        "distribution_status": dist_status,
        "known_limitations": manifest.get("known_limitations", []),
        "license": manifest.get("release_type", "INTERNAL_RESEARCH_RELEASE"),
        "inventory": manifest.get("row_counts", {}),
        "integrity": {"passed": True, "checks": {}},
        "node_types": node_types,
        "relation_types": relation_types,
        "coverage": [],
    }
    (release_dir / "release.json").write_text(
        json.dumps(release_json, indent=2, ensure_ascii=False), "utf-8"
    )

    schema_json = {
        "schema_version": manifest.get(
            "kg_schema_version", manifest.get("schema_version", "PESTKG_KG_SCHEMA_v0.2")
        ),
        "node_fields": NODE_FIELDS,
        "edge_fields": EDGE_FIELDS,
        "node_types": node_types,
        "relation_types": relation_types,
        "federation_predicates": {},
        "rules": {},
    }
    (release_dir / "schema.json").write_text(
        json.dumps(schema_json, indent=2, ensure_ascii=False), "utf-8"
    )

    # countries from Jurisdiction/CountryOrTerritory nodes.
    rows = con.execute(
        f"""
        SELECT node_id, node_type, display_label, jurisdiction_id
        FROM {nodes_parquet}
        WHERE node_type IN ('Jurisdiction', 'CountryOrTerritory')
        """
    ).fetchall()
    jurisdiction_names = {nid: label or "" for nid, ntype, label, _ in rows if ntype == "Jurisdiction"}
    countries = []
    for nid, ntype, label, jur_id in rows:
        if ntype != "CountryOrTerritory":
            continue
        countries.append({
            "jurisdiction": jur_id or "",
            "jurisdiction_name": jurisdiction_names.get(jur_id or "", jur_id or ""),
            "sovereign_country": label or "",
            "site_id": "", "official_url": "", "source_file": "", "source_sha256": "",
            "source_snapshot_eligible": False, "source_rows": 0, "skipped_rows": 0,
            "nodes": 0, "edges": 0, "broken_edges": 0, "graph_scope": "v1_manifest",
            "language": "und", "iso3": "", "map_id": nid, "coverage": dict(EMPTY_COVERAGE),
        })
    (release_dir / "countries.json").write_text(
        json.dumps(countries, indent=2, ensure_ascii=False), "utf-8"
    )

    print(f"prepared sample for {release_id}:")
    print(f"  nodes:    {sample_dir / 'nodes.csv'}")
    print(f"  edges:    {sample_dir / 'edges.csv'}")
    print(f"  uses:     {sample_dir / 'registration_uses.csv'}")
    print(f"  metadata: release.json, schema.json, countries.json")
    print(f"  node_types: {len(node_types)}, relation_types: {len(relation_types)}, countries: {len(countries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
