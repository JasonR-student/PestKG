from __future__ import annotations

import json
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "data/releases/2026.08.3_federated"


def test_release_metadata_matches_published_inventory() -> None:
    with (RELEASE / "release.json").open("r", encoding="utf-8") as handle:
        release = json.load(handle)
    assert release["release_id"] == "2026.08.3_federated"
    assert release["inventory"] == {
        "jurisdictions": 12,
        "source_records": 821_183,
        "country_nodes": 1_204_973,
        "country_edges": 9_739_818,
        "shared_nodes": 44_645,
        "alignment_edges": 48_721,
    }


def test_sample_edges_resolve_to_sample_nodes() -> None:
    sample = RELEASE / "sample"
    with (sample / "nodes.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        node_ids = {row["id"] for row in csv.DictReader(handle)}
    with (sample / "edges.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        edges = list(csv.DictReader(handle))
    assert edges
    assert all(edge["start_id"] in node_ids for edge in edges)
    assert all(edge["end_id"] in node_ids for edge in edges)


def test_sample_country_facts_are_traceable_and_isolated() -> None:
    sample = RELEASE / "sample"
    with (sample / "nodes.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        nodes = {row["id"]: row for row in csv.DictReader(handle)}
    with (sample / "edges.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        edges = list(csv.DictReader(handle))

    fact_types = {
        "ActiveIngredientLocal",
        "CropLocal",
        "FormulationLocal",
        "PesticideProduct",
        "Registration",
        "RegistrationUse",
        "TargetLocal",
    }
    local_facts = [node for node in nodes.values() if node["type"] in fact_types]
    assert local_facts
    assert all(node["source_record_id"] and node["source_url"] for node in local_facts)

    alignment_predicates = {"exactMatch", "lexicalAlignment"}
    for edge in edges:
        start = nodes[edge["start_id"]]
        end = nodes[edge["end_id"]]
        if edge["predicate"] not in alignment_predicates:
            assert not (
                start["jurisdiction"]
                and end["jurisdiction"]
                and start["jurisdiction"] != end["jurisdiction"]
            )


def test_sample_alignment_edges_are_unique() -> None:
    sample = RELEASE / "sample"
    with (sample / "edges.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        edges = list(csv.DictReader(handle))
    alignments = [
        (edge["start_id"], edge["predicate"], edge["end_id"])
        for edge in edges
        if edge["predicate"] in {"exactMatch", "lexicalAlignment"}
    ]
    assert len(alignments) == len(set(alignments))


def test_q1_to_q5_samples_are_present() -> None:
    comparison_dir = RELEASE / "sample/comparisons"
    for question in range(1, 6):
        path = comparison_dir / f"q{question}.csv"
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            assert next(csv.DictReader(handle), None) is not None
