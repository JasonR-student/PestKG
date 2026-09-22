from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


KNOWN_RELEASE_EXPECTATIONS = {
    "2026.08.3_federated": {
        "integrity": {
            "country_graphs": 12,
            "country_nodes": 1_204_973,
            "country_edges": 9_739_818,
            "shared_external_nodes": 44_645,
            "unique_alignment_edges": 48_721,
        },
        "neo4j": {
            "nodes": 1_253_222,
            "relationships": 9_791_548,
            "broken_relationship_endpoints": 0,
        },
    }
}

REQUIRED_COMPETENCY_OUTPUTS = {
    "06_competency_questions/Q1_crop_active_ingredients_cross_country.csv.gz",
    "06_competency_questions/Q2_same_target_products_cross_country.csv.gz",
    "06_competency_questions/Q3_shared_crop_target_combinations.csv.gz",
    "06_competency_questions/Q4_active_ingredient_formulations.csv.gz",
    "06_competency_questions/Q5_active_ingredient_country_use_profiles.csv.gz",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(release_dir: Path) -> int:
    release_root = release_dir.resolve()
    manifest_path = release_root / "manifest_sha256.csv"
    failures: list[str] = []
    paths: set[str] = set()
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError("Release SHA-256 manifest is empty")

    for row in rows:
        relative_path = row["relative_path"].replace("\\", "/")
        paths.add(relative_path)
        target = (release_root / relative_path).resolve()
        if not target.is_relative_to(release_root):
            failures.append(f"unsafe path: {relative_path}")
            continue
        if not target.is_file():
            failures.append(f"missing: {relative_path}")
            continue
        actual_size = target.stat().st_size
        expected_size = int(row["bytes"])
        if actual_size != expected_size:
            failures.append(
                f"size mismatch: {relative_path} ({actual_size} != {expected_size})"
            )
            continue
        actual_hash = sha256_file(target)
        if actual_hash.lower() != row["sha256"].lower():
            failures.append(f"SHA-256 mismatch: {relative_path}")

    missing_outputs = sorted(REQUIRED_COMPETENCY_OUTPUTS - paths)
    failures.extend(f"manifest entry missing: {path}" for path in missing_outputs)
    if failures:
        preview = "; ".join(failures[:20])
        if len(failures) > 20:
            preview += f"; and {len(failures) - 20} more"
        raise RuntimeError(f"Release manifest verification failed: {preview}")
    return len(rows)


def _positive_integer(report: dict[str, object], key: str) -> int:
    value = report.get(key)
    if not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"Release report field must be a positive integer: {key}")
    return value


def _compare_expected(
    report: dict[str, object], expected: dict[str, int], label: str
) -> None:
    mismatches = {
        key: {"expected": value, "actual": report.get(key)}
        for key, value in expected.items()
        if report.get(key) != value
    }
    if mismatches:
        raise RuntimeError(f"{label} inventory mismatch: {mismatches}")


def _validate_portal_metadata(
    release_dir: Path, integrity: dict[str, object]
) -> None:
    metadata_path = release_dir / "release.json"
    if not metadata_path.is_file():
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("release_id") != release_dir.name:
        raise RuntimeError(
            "release.json release_id does not match the immutable directory name"
        )
    inventory = metadata.get("inventory")
    if not isinstance(inventory, dict):
        raise RuntimeError("release.json inventory is missing")
    expected_pairs = {
        "jurisdictions": "country_graphs",
        "country_nodes": "country_nodes",
        "country_edges": "country_edges",
        "shared_nodes": "shared_external_nodes",
        "alignment_edges": "unique_alignment_edges",
    }
    mismatches = {
        portal_key: {
            "expected": integrity.get(report_key),
            "actual": inventory.get(portal_key),
        }
        for portal_key, report_key in expected_pairs.items()
        if inventory.get(portal_key) != integrity.get(report_key)
    }
    if mismatches:
        raise RuntimeError(f"Portal metadata inventory mismatch: {mismatches}")


def validate(release_dir: Path) -> dict[str, int]:
    release_dir = release_dir.resolve()
    manifest_entries = verify_manifest(release_dir)
    report_path = release_dir / "04_validation/final_integrity_report.json"
    with report_path.open("r", encoding="utf-8") as handle:
        report = json.load(handle)
    if not report.get("passed"):
        raise RuntimeError("The federated release integrity report did not pass")
    for key in (
        "country_graphs",
        "country_nodes",
        "country_edges",
        "shared_external_nodes",
        "unique_alignment_edges",
    ):
        _positive_integer(report, key)
    required_checks = (
        "zero_country_broken_edges",
        "zero_duplicate_alignment_edges",
        "zero_broken_alignment_edges",
        "all_country_graphs_independent",
    )
    failed = [name for name in required_checks if not report["checks"].get(name)]
    if failed:
        raise RuntimeError(f"Required release checks failed: {failed}")

    preparation_path = release_dir / "06_neo4j_import/preparation_report.json"
    with preparation_path.open("r", encoding="utf-8") as handle:
        preparation = json.load(handle)
    if not preparation.get("passed"):
        raise RuntimeError("The Neo4j preparation report did not pass")
    neo4j_nodes = _positive_integer(preparation, "nodes")
    neo4j_relationships = _positive_integer(preparation, "relationships")
    if preparation.get("broken_relationship_endpoints") != 0:
        raise RuntimeError("Neo4j preparation contains broken relationship endpoints")
    minimum_nodes = int(report["country_nodes"]) + int(
        report["shared_external_nodes"]
    )
    minimum_relationships = int(report["country_edges"]) + int(
        report["unique_alignment_edges"]
    )
    if neo4j_nodes < minimum_nodes:
        raise RuntimeError(
            f"Neo4j node inventory is smaller than the federated inventory: "
            f"{neo4j_nodes} < {minimum_nodes}"
        )
    if neo4j_relationships < minimum_relationships:
        raise RuntimeError(
            f"Neo4j relationship inventory is smaller than the federated inventory: "
            f"{neo4j_relationships} < {minimum_relationships}"
        )

    known = KNOWN_RELEASE_EXPECTATIONS.get(release_dir.name)
    if known:
        _compare_expected(report, known["integrity"], "Release")
        _compare_expected(preparation, known["neo4j"], "Neo4j import")
    _validate_portal_metadata(release_dir, report)
    return {
        "manifest_entries": manifest_entries,
        "country_graphs": int(report["country_graphs"]),
        "nodes": neo4j_nodes,
        "relationships": neo4j_relationships,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    args = parser.parse_args()
    validate(args.release_dir)
    print(f"Validated release: {args.release_dir}")


if __name__ == "__main__":
    main()
