"""Validate JSON source/cache collections in the frozen PestKG Raw Snapshot."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION = "a-line-json-profile-v1.0.0"
MAX_PARSE_BYTES = 25_000_000


def group_for(rel: str) -> str:
    if "us_epa_pesticides/raw_api/ppls/" in rel:
        return "US_EPA_PPLS_API"
    if "us_epa_pesticides/raw_api/pplsdist/" in rel:
        return "US_EPA_PPLSDIST_API"
    if "/agrovoc_search_cache/" in rel:
        return "AGROVOC_SEARCH_CACHE"
    if "/ChEBI/" in rel:
        return "CHEBI_REFERENCE"
    return rel.split("/")[2] if rel.startswith("data/01_raw_sources/") else "OTHER"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", type=Path, required=True)
    ap.add_argument("--manifest-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root = args.raw_root.resolve(strict=True)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with (args.manifest_dir / "RAW_INPUT_SHA256.csv").open("r", encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["relative_path"].lower().endswith(".json") and r["scope_class"] in ("SOURCE_SNAPSHOT", "CACHE")]
    groups = defaultdict(lambda: {"files": 0, "bytes": 0, "parsed_files": 0, "parse_errors": 0, "too_large": 0, "top_level_types": Counter(), "key_presence": Counter(), "array_items": 0})
    failures = []
    for i, item in enumerate(rows, start=1):
        rel = item["relative_path"]
        size = int(item["size_bytes"])
        g = groups[group_for(rel)]
        g["files"] += 1
        g["bytes"] += size
        if size > MAX_PARSE_BYTES:
            g["too_large"] += 1
            failures.append((rel, "LARGE_JSON_DEFERRED", f"{size} bytes; streaming parser required"))
            continue
        try:
            with (root / rel).open("r", encoding="utf-8-sig") as f:
                value = json.load(f)
            g["parsed_files"] += 1
            kind = type(value).__name__
            g["top_level_types"][kind] += 1
            if isinstance(value, dict):
                g["key_presence"].update(value.keys())
            elif isinstance(value, list):
                g["array_items"] += len(value)
        except Exception as exc:
            g["parse_errors"] += 1
            failures.append((rel, "JSON_PARSE_ERROR", repr(exc)))
        if i % 10_000 == 0 or i == len(rows):
            print(f"JSON_PROGRESS {i}/{len(rows)}", flush=True)
    summary = {
        "profile_version": VERSION,
        "snapshot_id": "PESTKG_RAW_SNAPSHOT_2026-09-23",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(rows),
        "total_bytes": sum(int(r["size_bytes"]) for r in rows),
        "groups": {
            key: {
                **{k: v for k, v in data.items() if k not in ("top_level_types", "key_presence")},
                "top_level_types": dict(data["top_level_types"]),
                "top_30_keys": data["key_presence"].most_common(30),
            }
            for key, data in sorted(groups.items())
        },
        "error_count": sum(v["parse_errors"] for v in groups.values()),
        "large_json_deferred_count": sum(v["too_large"] for v in groups.values()),
    }
    (out / "A3_JSON_COLLECTION_PROFILE.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "A3_JSON_EXCEPTIONS.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["relative_path", "reason_code", "detail"])
        writer.writerows(failures)
    print(f"JSON_DONE files={len(rows)} errors={summary['error_count']} large_deferred={summary['large_json_deferred_count']}", flush=True)


if __name__ == "__main__":
    main()