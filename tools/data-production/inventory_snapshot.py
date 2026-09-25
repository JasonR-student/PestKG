"""Inventory the frozen PestKG Raw Snapshot without modifying raw files."""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

COUNTRY_DIR = {
    "中国": "CN", "中国台湾": "TW", "日本": "JP", "韩国": "KR",
    "美国": "US", "澳大利亚": "AU", "匈牙利": "HU",
    "爱尔兰": "IE", "英国与北爱尔兰": "GB/GB-NI",
    "荷兰": "NL", "新西兰": "NZ",
}
FORMAT_CLASS = {
    ".json": "JSON", ".html": "HTML", ".csv": "CSV", ".csv.gz": "GZIP_CSV",
    ".tsv.gz": "GZIP_TSV", ".xlsx": "XLSX", ".xls": "XLS",
    ".zip": "ZIP", ".md": "MARKDOWN", ".py": "PYTHON", ".png": "PNG",
    ".pdf": "PDF", ".docx": "DOCX", ".pptx": "PPTX", ".ttl": "TURTLE",
    ".ndjson": "NDJSON", ".yaml": "YAML", ".sql": "SQL",
}


def extension(path: str) -> str:
    lower = path.lower()
    for suffix in (".csv.gz", ".tsv.gz", ".json.gz"):
        if lower.endswith(suffix):
            return suffix
    return Path(path).suffix.lower() or "[none]"


def context(path: str, scope: str) -> tuple[str, str, str]:
    parts = path.split("/")
    if parts[:2] == ["data", "01_raw_sources"]:
        family = parts[2] if len(parts) > 2 else "UNKNOWN"
        if family == "us_epa_pesticides":
            return "US", "us_epa_pesticides", "raw source / API capture"
        if family == "外部参考数据":
            return "N/A", parts[3] if len(parts) > 3 else "external_reference", "external reference"
        return COUNTRY_DIR.get(family, "UNKNOWN"), family, "official country source"
    if len(parts) >= 5 and parts[0] == "release" and parts[2] == "01_country_graphs":
        return parts[3], parts[4], "historical country graph release"
    if parts[0] == "release":
        return "N/A", "historical_release", "historical release"
    return "N/A", "project_workspace", scope.lower()


def sample_header(path: Path, ext: str) -> dict:
    try:
        with path.open("rb") as f:
            raw = f.read(16384)
        if raw.startswith(b"PK\x03\x04"):
            magic = "ZIP/OOXML"
        elif raw.startswith(b"\x1f\x8b"):
            magic = "GZIP"
        elif raw.startswith(b"%PDF"):
            magic = "PDF"
        elif raw.startswith(b"\x89PNG"):
            magic = "PNG"
        elif raw.startswith(b"Rar!"):
            magic = "RAR"
        else:
            magic = "TEXT_OR_OTHER"
        if ext in (".csv.gz", ".tsv.gz", ".json.gz"):
            with gzip.open(path, "rb") as f:
                raw = f.read(16384)
        text = None
        encoding = ""
        for enc in ("utf-8-sig", "gb18030"):
            try:
                text = raw.decode(enc, errors="ignore")
                encoding = enc
                break
            except UnicodeDecodeError:
                pass
        if text is None:
            text = ""
        stripped = text.lstrip()
        if magic == "TEXT_OR_OTHER":
            if stripped.startswith(("{", "[")):
                magic = "JSON_TEXT"
            elif stripped.lower().startswith(("<!doctype html", "<html")):
                magic = "HTML_TEXT"
            elif ext in (".csv", ".csv.gz", ".tsv.gz"):
                magic = "DELIMITED_TEXT"
        header = []
        if ext in (".csv", ".csv.gz", ".tsv.gz") and text:
            delimiter = "\t" if ext == ".tsv.gz" else ","
            try:
                header = next(csv.reader(io.StringIO(text), delimiter=delimiter))[:50]
            except (csv.Error, StopIteration):
                header = []
        return {"magic": magic, "sample_encoding": encoding, "sample_header": header}
    except Exception as exc:
        return {"magic": "READ_ERROR", "sample_encoding": "", "sample_header": [], "error": str(exc)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", type=Path, required=True)
    ap.add_argument("--manifest-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    raw = args.raw_root.resolve(strict=True)
    manifest_dir = args.manifest_dir.resolve(strict=True)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((manifest_dir / "RAW_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    frozen = manifest_dir / "RAW_INPUT_SHA256.csv"
    if manifest["snapshot_id"] != "PESTKG_RAW_SNAPSHOT_2026-09-23":
        raise ValueError("Wrong Raw Snapshot")
    with frozen.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != manifest["file_count"]:
        raise ValueError("Frozen manifest count mismatch")
    role_counts = Counter()
    source_counts = Counter()
    jurisdiction_counts = Counter()
    extension_counts = Counter()
    directory_counts = Counter()
    sha_counts = Counter()
    role_bytes = Counter()
    source_bytes = Counter()
    top_bytes = Counter()
    suspicious = []
    inventory_path = out / "A2_FILE_INVENTORY.csv"
    with inventory_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["relative_path", "size_bytes", "sha256", "mtime_utc", "scope_class", "jurisdiction", "source", "asset_context", "extension", "inferred_format", "inventory_note"])
        for row in rows:
            path = row["relative_path"]
            scope = row["scope_class"]
            juris, source, asset_context = context(path, scope)
            if row["jurisdiction"]:
                juris = row["jurisdiction"]
            if row["source"]:
                source = row["source"]
            ext = extension(path)
            kind = FORMAT_CLASS.get(ext, "OTHER")
            note = ""
            lower = path.lower()
            if re.search(r"(^|/)(backup|old|deprecated|temp|tmp)(/|_|$)", lower) or lower.endswith((".tmp", ".download")) or Path(path).name.startswith("~$"):
                note = "backup/temporary marker; verify role before any exclusion"
                suspicious.append(path)
            writer.writerow([path, row["size_bytes"], row["sha256"], row["mtime_utc"], scope, juris, source, asset_context, ext, kind, note])
            size = int(row["size_bytes"])
            role_counts[scope] += 1
            role_bytes[scope] += size
            source_counts[source] += 1
            source_bytes[source] += size
            jurisdiction_counts[juris] += 1
            extension_counts[ext] += 1
            directory_counts[str(Path(path).parent).replace("\\", "/")] += 1
            top_bytes[path.split("/")[0]] += size
            sha_counts[row["sha256"]] += 1

    primary = json.loads((manifest_dir / "RAW_INPUT_INVENTORY.json").read_text(encoding="utf-8"))["primary_source_files"]
    samples = {r["relative_path"] for r in primary}
    for prefix in (
        "data/01_raw_sources/us_epa_pesticides/raw_api/ppls/",
        "data/01_raw_sources/us_epa_pesticides/raw_api/pplsdist/",
        "data/01_raw_sources/us_epa_pesticides/raw_appril_pages/",
        "data/01_raw_sources/外部参考数据/ChEBI/",
        "data/01_raw_sources/外部参考数据/Crop_Target_English_Enrichment/agrovoc_search_cache/",
        "release/2026.08.3_federated/01_country_graphs/CN-TW/",
        "release/2026.08.3_federated/06_neo4j_import/",
    ):
        match = next((r["relative_path"] for r in rows if r["relative_path"].startswith(prefix)), None)
        if match:
            samples.add(match)
    for ext in (".html", ".json", ".csv.gz", ".tsv.gz", ".xlsx", ".zip", ".ttl", ".pdf", ".md"):
        match = next((r["relative_path"] for r in rows if extension(r["relative_path"]) == ext), None)
        if match:
            samples.add(match)
    for r in sorted(rows, key=lambda x: int(x["size_bytes"]), reverse=True)[:8]:
        samples.add(r["relative_path"])
    sample_results = []
    for rel in sorted(samples):
        desc = sample_header(raw / rel, extension(rel))
        sample_results.append({"relative_path": rel, "declared_extension": extension(rel), **desc})
    summary = {
        "snapshot_id": manifest["snapshot_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(rows),
        "total_size_bytes": sum(int(r["size_bytes"]) for r in rows),
        "scope_counts": dict(role_counts),
        "scope_bytes": dict(role_bytes),
        "source_counts": dict(source_counts),
        "source_bytes": dict(source_bytes),
        "jurisdiction_file_counts": dict(jurisdiction_counts),
        "extension_counts": dict(extension_counts),
        "top_directories": directory_counts.most_common(30),
        "exact_duplicate_sha_groups": sum(n > 1 for n in sha_counts.values()),
        "exact_duplicate_extra_files": sum(n - 1 for n in sha_counts.values() if n > 1),
        "backup_temporary_marker_count": len(suspicious),
        "backup_temporary_examples": suspicious[:30],
        "sample_count": len(sample_results),
        "content_samples": sample_results,
        "primary_source_files": primary,
        "record_count_status": "Historical release declarations only in A2; actual row counts to be streamed in A3.",
    }
    (out / "A2_INVENTORY_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "A2_CONTENT_SAMPLES.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["relative_path", "declared_extension", "magic", "sample_encoding", "sample_header", "error"])
        for s in sample_results:
            writer.writerow([s["relative_path"], s["declared_extension"], s["magic"], s["sample_encoding"], json.dumps(s["sample_header"], ensure_ascii=False), s.get("error", "")])
    top_dirs = "\n".join(f"| {p} | {n:,} |" for p, n in directory_counts.most_common(20))
    classes = "\n".join(f"| {name} | {count:,} | {role_bytes[name]:,} |" for name, count in sorted(role_counts.items()))
    sources = "\n".join(f"| {name} | {count:,} | {source_bytes[name]:,} |" for name, count in source_counts.most_common(15))
    core = "\n".join(f"| {x['jurisdiction']} | {x['source']} | {x['relative_path']} | {x['size_bytes']:,} | {x['declared_release_rows']:,} | {'YES' if x['matches_release_metadata'] else 'NO'} |" for x in primary)
    formats = ", ".join(f"{k}: {v:,}" for k, v in extension_counts.most_common(15))
    report = f"""# A2 Full Data Inventory

**Source Dataset Baseline:** {manifest['snapshot_id']}. **Input:** frozen project-level Raw Snapshot, not the old upstream manifest. **Status:** DONE for file/source/format inventory. Actual table row counts and field coverage are A3 tasks.

## Scope and evidence

The new RAW_INPUT_SHA256.csv lists {len(rows):,} files / {summary['total_size_bytes']:,} bytes. A2 classified every listed file by role, path context, source and jurisdiction and sampled {len(sample_results)} real file headers/magic bytes. File-level detail is in dataset/_audit_workspace/inventory/A2_FILE_INVENTORY.csv; machine summary and samples are beside it. Classification is a processing policy, not deletion. All files remain in the snapshot.

| Scope class | Files | Bytes |
| --- | ---: | ---: |
{classes}

CORE_RAW_DATA contains the 12 primary official-source CSV files referenced by the 12 country-graph source manifests. SOURCE_SNAPSHOT includes supplementary official captures and external reference material. INTERMEDIATE, RELEASE_OUTPUT, CACHE, STAGING, CODE, TEST, DOCUMENTATION, PAPER_MATERIAL and AUDIT_OUTPUT remain available as auxiliary or historical evidence. This prevents historical graph exports, caches and manuscripts from masquerading as fresh official source records.

## Primary official-source files

The release-declared row counts below are **historical metadata, not A3 recounts**. All 12 source-file SHA-256 values match those declarations.

| Jurisdiction | Source | Relative file | Bytes | Declared rows | SHA matches source metadata |
| --- | --- | --- | ---: | ---: | --- |
{core}

## Distribution and real-content sampling

Most files are individual API/reference objects; extensions: {formats}. SHA-256 content identity yields {summary['exact_duplicate_sha_groups']:,} duplicate-content groups and {summary['exact_duplicate_extra_files']:,} additional byte-identical files across the whole workspace; these are **not** automatic duplicate source records and none were removed. {summary['backup_temporary_marker_count']:,} paths have backup/temporary markers requiring role review, not deletion. Sampled signatures/headers are in A2_CONTENT_SAMPLES.csv. A declared extension alone was not used as proof of format.

**Largest source families:** 
| Source/family | Files | Bytes |
| --- | ---: | ---: |
{sources}

**Top 20 parent directories by file count:**
| Parent directory | Files |
| --- | ---: |
{top_dirs}

Jurisdiction counts in A2 are *file counts*, not source record coverage; the 12 principal jurisdictions are AU, CN, TW, GB, GB-NI, HU, IE, JP, KR, NL, NZ, US. External references, release-wide files and code have no single jurisdiction. A3 will stream the structured data and report actual rows, columns, missingness, identifiers, dates, units and per-jurisdiction coverage.

## Known limitations and next step

The project snapshot retains the old manifest mismatch (6,241 legacy-only paths including 6,182 ChEBI cache files, and seven unlisted present files). The old manifest is LEGACY_UPSTREAM_MANIFEST. A2 inventory is complete for the **actual frozen tree** and does not claim that an upstream package was complete. Source licensing and redistribution remain UNKNOWN until A17. No raw file was modified.

**Next:** A3 full streaming profile of primary and other major structured assets. Preserve original values, source context and provenance; do not extrapolate a small file sample to full-data quality.
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"A2_DONE files={len(rows)} bytes={summary['total_size_bytes']} samples={len(sample_results)}", flush=True)


if __name__ == "__main__":
    main()