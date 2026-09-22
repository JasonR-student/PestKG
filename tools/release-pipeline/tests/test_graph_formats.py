from __future__ import annotations

import gzip
import json
import csv
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb

from export_graph_formats import export_ntriples, export_sample_formats


ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "data/releases/2026.08.3_federated/sample"


def test_sample_jsonld_and_graphml_are_well_formed(tmp_path: Path) -> None:
    with (SAMPLE / "nodes.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        node_count = sum(1 for _ in csv.DictReader(handle))
    with (SAMPLE / "edges.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        edge_count = sum(1 for _ in csv.DictReader(handle))
    jsonld_path, graphml_path = export_sample_formats(SAMPLE, tmp_path)
    with jsonld_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    assert document["@context"]
    assert len(document["@graph"]) == node_count + edge_count

    root = ET.parse(graphml_path).getroot()
    namespace = {"g": "http://graphml.graphdrawing.org/xmlns"}
    assert len(root.findall(".//g:node", namespace)) == node_count
    assert len(root.findall(".//g:edge", namespace)) == edge_count


def test_ntriples_preserves_relationship_identity_and_provenance(tmp_path: Path) -> None:
    release = tmp_path / "release"
    analytics = release / "analytics"
    analytics.mkdir(parents=True)
    connection = duckdb.connect()
    connection.execute(
        "CREATE TABLE nodes AS SELECT 'AU:USE:1' id, 'RegistrationUse' AS \"type\", "
        "'1 use' label_original, '' label_en, 'AU' jurisdiction, 'RAW:1' source_record_id, "
        "'https://example.test/1' source_url, '{\"pairing_status\":\"official_pair_asserted\"}' properties_json"
    )
    connection.execute(
        "CREATE TABLE edges AS SELECT 'EDGE:1' id, 'AU:USE:1' start_id, "
        "'USES_PRODUCT' predicate, 'AU:PRODUCT:1' end_id, 'AU' jurisdiction, "
        "'RAW:1' source_record_id, 'https://example.test/1' source_url, '{}' properties_json"
    )
    connection.execute(
        f"COPY nodes TO '{(analytics / 'nodes.parquet').as_posix()}' (FORMAT PARQUET)"
    )
    connection.execute(
        f"COPY edges TO '{(analytics / 'edges.parquet').as_posix()}' (FORMAT PARQUET)"
    )
    connection.close()

    output = export_ntriples(release, release / "08_rdf/sample.nt.gz")
    with gzip.open(output, "rt", encoding="utf-8") as handle:
        text = handle.read()
    assert "relationship/EDGE%3A1" in text
    assert "rdf-syntax-ns#subject" in text
    assert '"RAW:1"' in text
    assert "USES_PRODUCT" in text
