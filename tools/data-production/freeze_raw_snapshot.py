"""Freeze the actual PestKG project raw tree without modifying input files."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_VERSION = "a-line-data-production-v1.0.0"
SCHEMA_VERSION = "canonical-v0.2;kg-v0.2"
SNAPSHOT_ID = "PESTKG_RAW_SNAPSHOT_2026-09-23"
KNOWN_LIMITATIONS = [
    "The root FILE_MANIFEST_SHA256.csv is a LEGACY_UPSTREAM_MANIFEST, not a checksum manifest for this project snapshot.",
    "The legacy manifest lists 6,241 paths absent from the current directory, including 6,182 ChEBI search_cache paths.",
    "The current directory has seven files not listed in the legacy manifest.",
    "Twenty-one surviving files sampled against the legacy manifest matched SHA-256; old upstream completeness is not established.",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def primary_sources(root: Path) -> dict[str, dict]:
    base = root / "release" / "2026.08.3_federated" / "01_country_graphs"
    result: dict[str, dict] = {}
    for meta_path in sorted(base.glob("*/*/manifest.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        original = str(meta.get("source_file", "")).replace("\\", "/")
        anchor = "data/01_raw_sources/"
        if anchor in original:
            rel = original[original.index(anchor) :]
        else:
            matches = list((root / "data" / "01_raw_sources").rglob(Path(original).name))
            if len(matches) != 1:
                raise ValueError(f"Cannot identify primary source for {meta_path}: {original}")
            rel = matches[0].relative_to(root).as_posix()
        if not (root / rel).is_file():
            raise FileNotFoundError(f"Declared primary source missing: {rel}")
        if rel in result and result[rel]["jurisdiction"] != meta.get("jurisdiction"):
            raise ValueError(f"Conflicting source jurisdiction: {rel}")
        result[rel] = {
            "jurisdiction": meta.get("jurisdiction", ""),
            "source": meta_path.parent.name,
            "declared_sha256": meta.get("source_sha256", ""),
            "declared_rows": meta.get("source_rows"),
        }
    return result


def classify(rel: str, primary: dict[str, dict]) -> str:
    lower = rel.casefold()
    parts = rel.split("/")
    if rel in primary:
        return "CORE_RAW_DATA"
    if lower == "file_manifest_sha256.csv" or rel.startswith("data/00_registry/") or "audit" in lower and not rel.startswith("data/01_raw_sources/"):
        return "AUDIT_OUTPUT"
    if "cache" in lower or "/__pycache__/" in lower:
        return "CACHE"
    if "staging" in lower or rel.startswith("data/02_"):
        return "STAGING"
    if rel.startswith("data/01_raw_sources/"):
        return "SOURCE_SNAPSHOT"
    if rel.startswith(("data/03_", "data/04_", "data/05_", "data/06_", "data/07_")):
        return "INTERMEDIATE"
    if rel.startswith("data/08_"):
        return "AUDIT_OUTPUT"
    if rel.startswith("release/") and "/07_manuscript/" in rel:
        return "PAPER_MATERIAL"
    if rel.startswith("release/"):
        return "RELEASE_OUTPUT"
    if rel.startswith("tests/") or parts[-1].startswith("test_"):
        return "TEST"
    if rel.startswith(("src/", "scripts/", "sql/", "config/", "neo4j/")) or rel == "pyproject.toml":
        return "CODE"
    if rel.startswith("docs/") or rel.lower().endswith((".md", ".txt")):
        return "DOCUMENTATION"
    return "INTERMEDIATE"


def atomic_write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    out = args.out.resolve()
    if root == out or root in out.parents:
        raise ValueError("Output must be outside the raw input directory")
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    primary = primary_sources(root)
    if len(primary) != 12:
        raise ValueError(f"Expected 12 distinct primary source files, found {len(primary)}")
    files: list[Path] = []
    for base, dirs, names in os.walk(root, followlinks=False):
        for directory in dirs:
            if (Path(base) / directory).is_symlink():
                raise ValueError(f"Symlink directory in input: {Path(base) / directory}")
        for name in names:
            p = Path(base) / name
            if p.is_symlink():
                raise ValueError(f"Symlink file in input: {p}")
            files.append(p)
    files.sort(key=lambda p: p.relative_to(root).as_posix())
    original_paths = [p.relative_to(root).as_posix() for p in files]
    sha_path = out / "RAW_INPUT_SHA256.csv"
    sums_path = out / "SHA256SUMS"
    temp_sha = out / "RAW_INPUT_SHA256.csv.partial"
    temp_sums = out / "SHA256SUMS.partial"
    total_bytes = 0
    count_class: Counter[str] = Counter()
    bytes_class: Counter[str] = Counter()
    count_top: Counter[str] = Counter()
    count_ext: Counter[str] = Counter()
    primary_results: list[dict] = []
    with temp_sha.open("w", encoding="utf-8", newline="") as csvfile, temp_sums.open("w", encoding="utf-8", newline="") as sums:
        writer = csv.writer(csvfile)
        writer.writerow(["relative_path", "size_bytes", "mtime_utc", "sha256", "scope_class", "jurisdiction", "source"])
        for index, p in enumerate(files, start=1):
            rel = p.relative_to(root).as_posix()
            before = p.stat()
            digest = sha256_file(p)
            after = p.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise RuntimeError(f"Input changed while hashing: {rel}")
            scope = classify(rel, primary)
            source = primary.get(rel, {})
            mtime = datetime.fromtimestamp(before.st_mtime, timezone.utc).isoformat()
            writer.writerow([rel, before.st_size, mtime, digest, scope, source.get("jurisdiction", ""), source.get("source", "")])
            sums.write(f"{digest}  {rel}\n")
            total_bytes += before.st_size
            count_class[scope] += 1
            bytes_class[scope] += before.st_size
            count_top[rel.split("/")[0]] += 1
            ext = ".csv.gz" if rel.lower().endswith(".csv.gz") else (p.suffix.lower() or "[none]")
            count_ext[ext] += 1
            if source:
                primary_results.append({
                    "relative_path": rel,
                    "jurisdiction": source["jurisdiction"],
                    "source": source["source"],
                    "size_bytes": before.st_size,
                    "sha256": digest,
                    "declared_release_sha256": source["declared_sha256"],
                    "matches_release_metadata": digest.lower() == str(source["declared_sha256"]).lower(),
                    "declared_release_rows": source["declared_rows"],
                })
            if index % 5000 == 0 or index == len(files):
                csvfile.flush()
                sums.flush()
                print(f"HASH_PROGRESS {index}/{len(files)} bytes={total_bytes}", flush=True)
    final_paths = sorted((Path(base) / name).relative_to(root).as_posix() for base, dirs, names in os.walk(root, followlinks=False) for name in names)
    if final_paths != original_paths:
        raise RuntimeError("Input file set changed while hashing")
    os.replace(temp_sha, sha_path)
    os.replace(temp_sums, sums_path)
    sha_manifest_hash = sha256_file(sha_path)
    finished = datetime.now(timezone.utc)
    inventory = {
        "snapshot_id": SNAPSHOT_ID,
        "root_path": str(root),
        "created_at": finished.isoformat(),
        "file_count": len(files),
        "total_size_bytes": total_bytes,
        "counts_by_scope_class": dict(sorted(count_class.items())),
        "bytes_by_scope_class": dict(sorted(bytes_class.items())),
        "counts_by_top_level": dict(sorted(count_top.items())),
        "counts_by_extension": dict(count_ext.most_common()),
        "primary_source_files": sorted(primary_results, key=lambda x: x["jurisdiction"]),
        "classification_rule_version": PIPELINE_VERSION,
    }
    atomic_write_json(out / "RAW_INPUT_INVENTORY.json", inventory)
    manifest = {
        "snapshot_id": SNAPSHOT_ID,
        "status": "ACTIVE_RAW_INPUT",
        "integrity_gate": "DONE_BY_PROJECT_BASELINE_DECISION",
        "root_path": str(root),
        "source_path": str(root),
        "created_at": finished.isoformat(),
        "file_count": len(files),
        "total_size_bytes": total_bytes,
        "source_scope": "The actual current directory; CORE_RAW_DATA and SOURCE_SNAPSHOT prioritized, other classes retained as auxiliary or historical assets.",
        "known_limitations": KNOWN_LIMITATIONS,
        "legacy_manifest_reference": {
            "relative_path": "FILE_MANIFEST_SHA256.csv",
            "role": "LEGACY_UPSTREAM_MANIFEST",
            "sha256": "0e287f2e7261651cc979970ea7d13dd2aea6096b9b0b61a53a15387e766252d1",
        },
        "sha256_manifest": "RAW_INPUT_SHA256.csv",
        "sha256_manifest_sha256": sha_manifest_hash,
        "sha256sums": "SHA256SUMS",
        "inventory": "RAW_INPUT_INVENTORY.json",
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "canonical_registry_version": "NOT_CREATED",
        "decision_id": "DEC-RAW-001",
        "upstream_completeness": "NOT_ESTABLISHED",
        "hash_started_at": started.isoformat(),
        "hash_finished_at": finished.isoformat(),
    }
    atomic_write_json(out / "RAW_INPUT_MANIFEST.json", manifest)
    readme = f"""# PestKG project raw snapshot

Snapshot ID: {SNAPSHOT_ID}
Status: ACTIVE_RAW_INPUT under owner decision DEC-RAW-001.
Root: {root}
File count: {len(files)}
Total bytes: {total_bytes}
SHA-256 manifest: RAW_INPUT_SHA256.csv ({sha_manifest_hash})
Pipeline version: {PIPELINE_VERSION}

This is a project-level freeze of the actual downloaded directory. It does not certify
that the old upstream FILE_MANIFEST_SHA256.csv represented this tree or that an
upstream package was complete. That file is retained as LEGACY_UPSTREAM_MANIFEST.
The 6,241 old-manifest-only paths and seven unlisted current files are known
input limitations documented in docs/audits/A0_1_RAW_DIRECTORY_COMPLETENESS_DIAGNOSIS.md.

Each line of RAW_INPUT_SHA256.csv records one raw-tree file, its original relative
path, byte size, mtime, SHA-256 and preliminary scope class. SHA256SUMS is a
standard digest/path view of the same files. RAW_INPUT_INVENTORY.json summarizes
scope and the 12 primary source files. These outputs are outside the raw tree.
Do not edit the raw tree after this freeze. If any file changes, create a new
snapshot ID and manifest rather than silently replacing this baseline.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(f"FREEZE_DONE files={len(files)} bytes={total_bytes} manifest_sha256={sha_manifest_hash}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())