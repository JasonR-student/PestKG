from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import duckdb

from materialize_parquet import materialize
from validate_analytics import validate_analytics


NODE_HEADER = [
    "nodeId:ID(PesticideKG)",
    "labelOriginal",
    "labelEnglish",
    "jurisdiction",
    "sourceRecordId",
    "sourceUrl",
    "sourceGraph",
    "system",
    "propertiesJson",
    ":LABEL",
]

EDGE_HEADER = [
    "relationshipId",
    ":START_ID(PesticideKG)",
    ":END_ID(PesticideKG)",
    "jurisdiction",
    "sourceRecordId",
    "sourceUrl",
    "sourceGraph",
    "evidenceCount:long",
    "alignmentStatus",
    "propertiesJson",
    ":TYPE",
]


def write_gzip_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def test_materialize_reads_typed_neo4j_headers_and_partitions(tmp_path: Path) -> None:
    release = tmp_path / "release"
    import_dir = release / "06_neo4j_import"
    import_dir.mkdir(parents=True)
    nodes = [
        ["AU:USE:1", "1 use", "", "AU", "RAW:1", "https://example.test/1", "AU", "", json.dumps({"pairing_status": "official_pair_asserted"}), "Entity;CountryEntity;RegistrationUse"],
        ["AU:PRODUCT:1", "Test product", "Test product", "AU", "RAW:1", "https://example.test/1", "AU", "", "{}", "Entity;CountryEntity;PesticideProduct"],
        ["AU:AI:1", "GLYPHOSATE", "GLYPHOSATE", "AU", "RAW:1", "https://example.test/1", "AU", "", "{}", "Entity;CountryEntity;ActiveIngredientLocal"],
        ["AU:CROP:1", "WHEAT", "WHEAT", "AU", "RAW:1", "https://example.test/1", "AU", "", "{}", "Entity;CountryEntity;CropLocal"],
        ["AU:TARGET:1", "WEED", "WEED", "AU", "RAW:1", "https://example.test/1", "AU", "", "{}", "Entity;CountryEntity;TargetLocal"],
        ["AU:FORM:1", "SC", "SC", "AU", "RAW:1", "https://example.test/1", "AU", "", "{}", "Entity;CountryEntity;FormulationLocal"],
        ["AU:REG:1", "R-1", "R-1", "AU", "RAW:1", "https://example.test/1", "AU", "", json.dumps({"status_original": "Valid", "registration_date": "2026-01-01", "expiry_date": "2027-01-01"}), "Entity;CountryEntity;Registration"],
    ]
    edges = [
        ["E1", "AU:USE:1", "AU:PRODUCT:1", "AU", "RAW:1", "https://example.test/1", "AU", "1", "", "{}", "USES_PRODUCT"],
        ["E2", "AU:USE:1", "AU:AI:1", "AU", "RAW:1", "https://example.test/1", "AU", "1", "", "{}", "HAS_ACTIVE_INGREDIENT"],
        ["E3", "AU:USE:1", "AU:CROP:1", "AU", "RAW:1", "https://example.test/1", "AU", "1", "", "{}", "REGISTERED_FOR_CROP"],
        ["E4", "AU:USE:1", "AU:TARGET:1", "AU", "RAW:1", "https://example.test/1", "AU", "1", "", "{}", "REGISTERED_FOR_TARGET"],
        ["E5", "AU:USE:1", "AU:FORM:1", "AU", "RAW:1", "https://example.test/1", "AU", "1", "", "{}", "HAS_FORMULATION"],
        ["E6", "AU:REG:1", "AU:USE:1", "AU", "RAW:1", "https://example.test/1", "AU", "1", "", "{}", "HAS_REGISTRATION_USE"],
    ]
    write_gzip_csv(import_dir / "nodes.csv.gz", NODE_HEADER, nodes)
    write_gzip_csv(import_dir / "relationships.csv.gz", EDGE_HEADER, edges)
    (import_dir / "preparation_report.json").write_text(
        json.dumps(
            {
                "nodes": len(nodes),
                "relationships": len(edges),
                "node_types": {"RegistrationUse": 1},
            }
        ),
        encoding="utf-8",
    )
    (release / "release.json").write_text(
        json.dumps({"inventory": {"jurisdictions": 1}}), encoding="utf-8"
    )

    analytics = materialize(release)
    connection = duckdb.connect()
    node_count = connection.execute(
        f"SELECT count(*) FROM read_parquet('{(analytics / 'nodes/**/*.parquet').as_posix()}', hive_partitioning=true)"
    ).fetchone()[0]
    use = connection.execute(
        f"SELECT * FROM read_parquet('{(analytics / 'registration_uses/**/*.parquet').as_posix()}', hive_partitioning=true)"
    ).fetchone()
    columns = [column[0] for column in connection.description]
    record = dict(zip(columns, use, strict=True))
    connection.close()

    assert node_count == len(nodes)
    assert record["use_id"] == "AU:USE:1"
    assert record["jurisdiction"] == "AU"
    assert record["registration_status"] == "Valid"
    assert json.loads(record["active_ingredients_json"])[0]["id"] == "AU:AI:1"
    assert (analytics / "country_stats.parquet").is_file()
    checks = validate_analytics(release)
    assert checks["broken_edges"] == 0
