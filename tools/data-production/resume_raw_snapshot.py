"""Resume the PestKG raw freeze from preserved partial hash files."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from freeze_raw_snapshot import (
    KNOWN_LIMITATIONS,
    PIPELINE_VERSION,
    SCHEMA_VERSION,
    SNAPSHOT_ID,
    atomic_write_json,
    classify,
    primary_sources,
    sha256_file,
)

HEADER = ["relative_path", "size_bytes", "mtime_utc", "sha256", "scope_class", "jurisdiction", "source"]


def all_files(root: Path) -> list[Path]:
    paths = []
    for base, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            if (Path(base) / name).is_symlink():
                raise ValueError("Symlink directory in raw input")
        for name in names:
            p = Path(base) / name
            if p.is_symlink():
                raise ValueError("Symlink file in raw input")
            paths.append(p)
    return sorted(paths, key=lambda p: p.relative_to(root).as_posix())


def validate_checkpoint(
    root: Path, files: list[Path], primary: dict, csv_path: Path, sums_path: Path
) -> tuple[list[dict], int]:
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADER:
            raise ValueError(f"Wrong CSV header: {reader.fieldnames}")
        rows = list(reader)
    with sums_path.open("r", encoding="utf-8") as stream:
        sums = stream.read().splitlines()
    if len(rows) > len(files) or len(sums) > len(rows):
        raise ValueError("Partial row count exceeds input count or sums count")
    seen = set()
    for i, row in enumerate(rows):
        p = files[i]
        rel = p.relative_to(root).as_posix()
        if row["relative_path"] != rel or rel in seen:
            raise ValueError(f"Path/order/duplicate mismatch at {i}: {rel}")
        seen.add(rel)
        stat = p.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        if int(row["size_bytes"]) != stat.st_size or row["mtime_utc"] != mtime:
            raise ValueError(f"Raw file changed since partial hash: {rel}")
        if row["scope_class"] != classify(rel, primary):
            raise ValueError(f"Scope classification changed: {rel}")
        if not re.fullmatch("[0-9a-f]{64}", row["sha256"]):
            raise ValueError(f"Invalid SHA-256 at {rel}")
        if i < len(sums) and sums[i] != row["sha256"] + "  " + rel:
            raise ValueError(f"SHA256SUMS mismatch at {rel}")
    for row in rows[len(sums) :]:
        rel = row["relative_path"]
        if sha256_file(root / rel) != row["sha256"]:
            raise ValueError(f"Unpaired partial hash mismatch: {rel}")
    return rows, len(sums)


def validate_lists(root: Path, files: list[Path], csv_path: Path, sums_path: Path) -> tuple[int, int]:
    count = 0
    total = 0
    with csv_path.open("r", encoding="utf-8", newline="") as source, sums_path.open("r", encoding="utf-8") as sums:
        reader = csv.DictReader(source)
        if reader.fieldnames != HEADER:
            raise ValueError("Final CSV header mismatch")
        for row in reader:
            if count >= len(files):
                raise ValueError("Too many final rows")
            rel = files[count].relative_to(root).as_posix()
            if row["relative_path"] != rel:
                raise ValueError(f"Final path mismatch: {count}")
            digest_line = sums.readline().rstrip("\r\n")
            if digest_line != row["sha256"] + "  " + rel:
                raise ValueError(f"Final SHA list mismatch: {count}")
            stat = files[count].stat()
            if int(row["size_bytes"]) != stat.st_size or row["mtime_utc"] != datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat():
                raise ValueError(f"Raw file changed after hashing: {rel}")
            count += 1
            total += stat.st_size
        if sums.readline():
            raise ValueError("Trailing extra SHA256SUMS lines")
    if count != len(files):
        raise ValueError(f"Incomplete final list: {count}/{len(files)}")
    return count, total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve(strict=True)
    out = args.out.resolve()
    if root == out or root in out.parents:
        raise ValueError("Output must be outside raw input")
    files = all_files(root)
    primary = primary_sources(root)
    if len(primary) != 12:
        raise ValueError("Expected 12 primary source files")
    initial_csv = out / "RAW_INPUT_SHA256.csv.partial"
    initial_sums = out / "SHA256SUMS.partial"
    work_csv = out / "RAW_INPUT_SHA256.csv.resume"
    work_sums = out / "SHA256SUMS.resume"
    if work_csv.exists() != work_sums.exists():
        raise ValueError("Only one resume working file exists")
    if work_csv.exists():
        source_csv, source_sums = work_csv, work_sums
    else:
        source_csv, source_sums = initial_csv, initial_sums
    if not source_csv.exists() or not source_sums.exists():
        raise FileNotFoundError("Preserved partial checkpoint missing")
    rows, paired = validate_checkpoint(root, files, primary, source_csv, source_sums)
    if source_csv == initial_csv:
        shutil.copyfile(initial_csv, work_csv)
        shutil.copyfile(initial_sums, work_sums)
    with work_sums.open("a", encoding="utf-8", newline="") as sums:
        for row in rows[paired:]:
            sums.write(row["sha256"] + "  " + row["relative_path"] + "\n")
        sums.flush()
    checkpoint = len(rows)
    print(f"RESUME_CHECKPOINT rows={checkpoint} recovered_sums={checkpoint-paired} total={len(files)}", flush=True)

    counts = Counter()
    bytes_class = Counter()
    top = Counter()
    ext = Counter()
    primary_results = []
    total_bytes = 0
    for row in rows:
        rel = row["relative_path"]
        size = int(row["size_bytes"])
        scope = row["scope_class"]
        counts[scope] += 1
        bytes_class[scope] += size
        top[rel.split("/")[0]] += 1
        ext[".csv.gz" if rel.lower().endswith(".csv.gz") else (Path(rel).suffix.lower() or "[none]")] += 1
        total_bytes += size
        if rel in primary:
            meta = primary[rel]
            primary_results.append({
                "relative_path": rel, "jurisdiction": meta["jurisdiction"], "source": meta["source"],
                "size_bytes": size, "sha256": row["sha256"],
                "declared_release_sha256": meta["declared_sha256"],
                "matches_release_metadata": row["sha256"].lower() == str(meta["declared_sha256"]).lower(),
                "declared_release_rows": meta["declared_rows"],
            })
    resumed_at = datetime.now(timezone.utc)
    with work_csv.open("a", encoding="utf-8", newline="") as csvfile, work_sums.open("a", encoding="utf-8", newline="") as sums:
        writer = csv.writer(csvfile)
        for index in range(checkpoint, len(files)):
            p = files[index]
            rel = p.relative_to(root).as_posix()
            before = p.stat()
            digest = sha256_file(p)
            after = p.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise RuntimeError(f"Input changed while hashing: {rel}")
            scope = classify(rel, primary)
            meta = primary.get(rel, {})
            mtime = datetime.fromtimestamp(before.st_mtime, timezone.utc).isoformat()
            writer.writerow([rel, before.st_size, mtime, digest, scope, meta.get("jurisdiction", ""), meta.get("source", "")])
            sums.write(digest + "  " + rel + "\n")
            total_bytes += before.st_size
            counts[scope] += 1
            bytes_class[scope] += before.st_size
            top[rel.split("/")[0]] += 1
            ext[".csv.gz" if rel.lower().endswith(".csv.gz") else (p.suffix.lower() or "[none]")] += 1
            if meta:
                primary_results.append({
                    "relative_path": rel, "jurisdiction": meta["jurisdiction"], "source": meta["source"],
                    "size_bytes": before.st_size, "sha256": digest,
                    "declared_release_sha256": meta["declared_sha256"],
                    "matches_release_metadata": digest.lower() == str(meta["declared_sha256"]).lower(),
                    "declared_release_rows": meta["declared_rows"],
                })
            if (index + 1) % 5000 == 0 or index + 1 == len(files):
                csvfile.flush()
                sums.flush()
                print(f"HASH_PROGRESS {index+1}/{len(files)} bytes={total_bytes}", flush=True)
    final_paths = [p.relative_to(root).as_posix() for p in all_files(root)]
    if final_paths != [p.relative_to(root).as_posix() for p in files]:
        raise RuntimeError("Input path set changed during resume")
    checked_count, checked_bytes = validate_lists(root, files, work_csv, work_sums)
    if checked_bytes != total_bytes:
        raise ValueError("Inventory byte total mismatch")
    final_csv = out / "RAW_INPUT_SHA256.csv"
    final_sums = out / "SHA256SUMS"
    os.replace(work_csv, final_csv)
    os.replace(work_sums, final_sums)
    manifest_hash = sha256_file(final_csv)
    finished = datetime.now(timezone.utc)
    inventory = {
        "snapshot_id": SNAPSHOT_ID, "root_path": str(root), "created_at": finished.isoformat(),
        "file_count": checked_count, "total_size_bytes": checked_bytes,
        "counts_by_scope_class": dict(sorted(counts.items())),
        "bytes_by_scope_class": dict(sorted(bytes_class.items())),
        "counts_by_top_level": dict(sorted(top.items())),
        "counts_by_extension": dict(ext.most_common()),
        "primary_source_files": sorted(primary_results, key=lambda x: x["jurisdiction"]),
        "classification_rule_version": PIPELINE_VERSION,
    }
    atomic_write_json(out / "RAW_INPUT_INVENTORY.json", inventory)
    manifest = {
        "snapshot_id": SNAPSHOT_ID, "status": "ACTIVE_RAW_INPUT",
        "integrity_gate": "DONE_BY_PROJECT_BASELINE_DECISION",
        "root_path": str(root), "source_path": str(root), "created_at": finished.isoformat(),
        "file_count": checked_count, "total_size_bytes": checked_bytes,
        "source_scope": "Actual current directory; CORE_RAW_DATA and SOURCE_SNAPSHOT are the processing priority; all other scope classes retained.",
        "known_limitations": KNOWN_LIMITATIONS,
        "legacy_manifest_reference": {
            "relative_path": "FILE_MANIFEST_SHA256.csv",
            "role": "LEGACY_UPSTREAM_MANIFEST",
            "sha256": "0e287f2e7261651cc979970ea7d13dd2aea6096b9b0b61a53a15387e766252d1",
        },
        "sha256_manifest": "RAW_INPUT_SHA256.csv",
        "sha256_manifest_sha256": manifest_hash,
        "sha256sums": "SHA256SUMS",
        "inventory": "RAW_INPUT_INVENTORY.json",
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "canonical_registry_version": "NOT_CREATED",
        "decision_id": "DEC-RAW-001",
        "upstream_completeness": "NOT_ESTABLISHED",
        "resume_checkpoint_rows": checkpoint,
        "hash_resumed_at": resumed_at.isoformat(),
        "hash_finished_at": finished.isoformat(),
    }
    atomic_write_json(out / "RAW_INPUT_MANIFEST.json", manifest)
    readme = f"""# PestKG project raw snapshot

Snapshot ID: {SNAPSHOT_ID}
Status: ACTIVE_RAW_INPUT under DEC-RAW-001.
Root: {root}
File count: {checked_count}
Total bytes: {checked_bytes}
SHA-256 manifest: RAW_INPUT_SHA256.csv ({manifest_hash})
Pipeline version: {PIPELINE_VERSION}
Resume checkpoint reused: {checkpoint} file hashes.

This is a project-level freeze of the actual downloaded directory. It does not
certify the old upstream FILE_MANIFEST_SHA256.csv or upstream completeness.
That file remains LEGACY_UPSTREAM_MANIFEST; see the A0.1 audit for 6,241
legacy-only paths and seven unlisted current files.
The original interrupted .partial files are preserved in this directory.
Do not modify the raw tree. A change requires a new snapshot ID and manifest.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(f"FREEZE_DONE files={checked_count} bytes={checked_bytes} manifest_sha256={manifest_hash}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())