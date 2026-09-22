from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RELEASE_ROOT = PROJECT_ROOT / "data" / "releases" / "2026.08.3_federated"
sys.path.insert(0, str(PROJECT_ROOT / "research" / "figures"))

from generate_extended_figures import chain_rows, projection_contract


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class PaperFigureDataContractTest(unittest.TestCase):
    def test_release_inventory_is_frozen(self) -> None:
        release = json.loads((RELEASE_ROOT / "release.json").read_text(encoding="utf-8"))
        self.assertEqual(release["release_id"], "2026.08.3_federated")
        self.assertEqual(release["inventory"]["jurisdictions"], 12)
        self.assertEqual(release["inventory"]["country_nodes"], 1_204_973)
        self.assertEqual(release["inventory"]["country_edges"], 9_739_818)
        self.assertEqual(release["inventory"]["shared_nodes"], 44_645)
        self.assertEqual(release["inventory"]["alignment_edges"], 48_721)

    def test_apvma_fortin_subgraph_is_traceable(self) -> None:
        nodes = read_csv(RELEASE_ROOT / "sample" / "nodes.csv")
        edges = read_csv(RELEASE_ROOT / "sample" / "edges.csv")
        by_id = {row["id"]: row for row in nodes}
        product_id = "AU:PRODUCT:7feed95ebf8a4d6f19180bcc"
        use_id = "AU:USE:36eb10d52505b1259844b48b"
        self.assertEqual(by_id[product_id]["label_en"], "Fortin Herbicide")
        crop_edges = [
            row
            for row in edges
            if row["start_id"] == use_id and row["predicate"] == "registeredForCrop"
        ]
        self.assertEqual(len(crop_edges), 48)
        self.assertTrue(all(row["source_record_id"] for row in crop_edges))

    def test_federated_comparison_has_real_external_identifiers(self) -> None:
        rows = read_csv(RELEASE_ROOT / "sample" / "comparisons" / "q1.csv")
        self.assertTrue(any(row["active_shared_id"].startswith("CHEBI:") for row in rows))
        self.assertTrue(
            all(row["crop_shared_id"].startswith("http://aims.fao.org/aos/agrovoc/") for row in rows)
        )
        self.assertTrue(all(row["pairing_status"] == "official_pair_asserted" for row in rows))

    def test_projection_contract_is_derived_from_q1(self) -> None:
        rows = read_csv(RELEASE_ROOT / "sample" / "comparisons" / "q1.csv")
        contract = projection_contract(rows)
        self.assertEqual(len(contract["active_nodes"]), 14)
        self.assertTrue(all(row["id"].startswith("CHEBI:") for row in contract["active_nodes"]))
        self.assertTrue(all(row["jurisdiction_count"] >= 2 for row in contract["active_nodes"]))
        self.assertEqual({row["jurisdiction"] for row in contract["bipartite_edges"]}, {"TW", "CN", "KR", "JP"})
        self.assertTrue(contract["country_projection"])
        self.assertTrue(contract["entity_projection"])

    def test_multisite_chain_has_four_real_jurisdictions(self) -> None:
        rows = read_csv(RELEASE_ROOT / "sample" / "comparisons" / "q1.csv")
        selected = chain_rows(rows)
        self.assertEqual([row["jurisdiction"] for row in selected], ["TW", "CN", "KR", "JP"])
        self.assertTrue(all(row["active_shared_id"] == "CHEBI:3639" for row in selected))


if __name__ == "__main__":
    unittest.main()
