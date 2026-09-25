"""Bounded-memory structural profiles for supplementary source snapshots."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from itertools import chain, islice
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

VERSION = "a-line-supplementary-profile-v1.0.0"
EXTENSIONS = (".csv", ".csv.gz", ".tsv.gz", ".xlsx", ".xls", ".ndjson")
csv.field_size_limit(1_000_000_000)


def encoding_for(path: Path, compressed: bool) -> tuple[str, str]:
    with (gzip.open(path, "rb") if compressed else path.open("rb")) as stream:
        chunks = []
        size = 0
        while size < 256_000:
            line = stream.readline()
            if not line:
                break
            chunks.append(line)
            size += len(line)
    sample = b"".join(chunks)
    preferred = ("utf-8-sig", "cp932", "gb18030") if "日本" in str(path) else ("utf-8-sig", "gb18030", "cp932")
    for encoding in preferred:
        try:
            sample.decode(encoding)
            return encoding, "STRICT_MULTILINE_SAMPLE"
        except UnicodeDecodeError:
            pass
    return "utf-8-sig", "REPLACEMENT_FALLBACK"


def row_hash(row: list) -> bytes:
    return hashlib.blake2b(json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8"), digest_size=16).digest()


def profile_delimited(path: Path, suffix: str) -> dict:
    compressed = suffix.endswith(".gz")
    encoding, encoding_status = encoding_for(path, compressed)
    open_fn = gzip.open if compressed else open
    separator = "\t" if suffix == ".tsv.gz" else ","
    blanks = []
    rows = 0
    wrong_width = 0
    replacement_rows = 0
    duplicate_rows = 0
    hashes = set()
    with open_fn(path, "rt", encoding=encoding, errors="replace", newline="") as stream:
        reader = csv.reader(stream, delimiter=separator)
        try:
            header = next(reader)
        except StopIteration:
            return {"status": "EMPTY_FILE", "format": suffix, "encoding": encoding, "encoding_status": encoding_status, "row_count": 0, "column_count": 0, "header": [], "blank_counts": [], "wrong_width_rows": 0, "replacement_character_rows": 0, "duplicate_row_hash_count": 0}
        blanks = [0] * len(header)
        for row in reader:
            rows += 1
            if len(row) != len(header):
                wrong_width += 1
                row = (row + [""] * len(header))[: len(header)]
            if any("\ufffd" in value for value in row):
                replacement_rows += 1
            digest = row_hash(row)
            if digest in hashes:
                duplicate_rows += 1
            else:
                hashes.add(digest)
            for i, value in enumerate(row):
                if not str(value).strip():
                    blanks[i] += 1
            if rows % 100_000 == 0:
                print(f"SUPPLEMENT_PROGRESS {path.name} {rows}", flush=True)
    return {
        "status": "DONE", "format": suffix, "encoding": encoding,
        "encoding_status": encoding_status, "row_count": rows,
        "column_count": len(header), "header": header,
        "blank_counts": blanks, "wrong_width_rows": wrong_width,
        "replacement_character_rows": replacement_rows,
        "duplicate_row_hash_count": duplicate_rows,
    }


def profile_xlsx(path: Path) -> dict:
    from openpyxl import load_workbook
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheets = []
    try:
        for sheet in workbook.worksheets:
            declared_dimension = sheet.calculate_dimension()
            if declared_dimension == "A1:A1":
                sheet.reset_dimensions()
                iterator = sheet.iter_rows(values_only=True)
                prefix = list(islice(iterator, 20))
                header_index = next((i for i, row in enumerate(prefix) if sum(x is not None and str(x).strip() != "" for x in row) >= 2), 0)
                header = ["" if x is None else str(x) for x in prefix[header_index]] if prefix else []
                data_rows = chain(prefix[header_index + 1 :], iterator)
            else:
                iterator = sheet.iter_rows(values_only=True)
                header = ["" if x is None else str(x) for x in next(iterator, [])]
                header_index = 0
                data_rows = iterator
            blanks = [0] * len(header)
            rows = 0
            blank_sheet_rows = 0
            wrong_width = 0
            for row in data_rows:
                if not any(value is not None and str(value).strip() for value in row):
                    blank_sheet_rows += 1
                    continue
                rows += 1
                if len(row) != len(header):
                    wrong_width += 1
                for i, value in enumerate(row[: len(header)]):
                    if value is None or str(value).strip() == "":
                        blanks[i] += 1
                if rows % 100_000 == 0:
                    print(f"SUPPLEMENT_PROGRESS {path.name}:{sheet.title} {rows}", flush=True)
            sheets.append({
                "sheet": sheet.title, "row_count": rows, "column_count": len(header),
                "header": header, "blank_counts": blanks, "wrong_width_rows": wrong_width,
                "blank_sheet_rows": blank_sheet_rows, "header_row_number": header_index + 1,
                "declared_dimension": declared_dimension,
            })
    finally:
        workbook.close()
    return {
        "status": "DONE", "format": ".xlsx", "sheets": sheets,
        "row_count": sum(x["row_count"] for x in sheets),
        "column_count": max((x["column_count"] for x in sheets), default=0),
    }


def profile_ndjson(path: Path) -> dict:
    encoding, encoding_status = encoding_for(path, False)
    rows = 0
    bad = 0
    keys = Counter()
    with path.open("r", encoding=encoding, errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            rows += 1
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    keys.update(value.keys())
            except json.JSONDecodeError:
                bad += 1
    return {
        "status": "DONE" if bad == 0 else "PARSE_ERRORS",
        "format": ".ndjson", "encoding": encoding, "encoding_status": encoding_status,
        "row_count": rows, "json_parse_errors": bad,
        "key_presence": dict(keys.most_common()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", type=Path, required=True)
    ap.add_argument("--manifest-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root = args.raw_root.resolve(strict=True)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with (args.manifest_dir / "RAW_INPUT_SHA256.csv").open("r", encoding="utf-8", newline="") as stream:
        items = [r for r in csv.DictReader(stream) if r["scope_class"] == "SOURCE_SNAPSHOT" and r["relative_path"].lower().endswith(EXTENSIONS)]
    results = []
    for index, row in enumerate(sorted(items, key=lambda x: int(x["size_bytes"]), reverse=True), start=1):
        rel = row["relative_path"]
        digest = row["sha256"]
        result_path = out / (digest + ".json")
        if result_path.exists():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result.get("profile_version") == VERSION and result.get("sha256") == digest:
                print(f"SUPPLEMENT_SKIP {index}/{len(items)} {rel}", flush=True)
                results.append({"relative_path": rel, "sha256": digest, "profile": result_path.name, "status": result["status"], "row_count": result.get("row_count"), "column_count": result.get("column_count")})
                continue
        path = root / rel
        suffix = next(x for x in EXTENSIONS if rel.lower().endswith(x))
        try:
            if suffix in (".csv", ".csv.gz", ".tsv.gz"):
                result = profile_delimited(path, suffix)
            elif suffix == ".xlsx":
                result = profile_xlsx(path)
            elif suffix == ".ndjson":
                result = profile_ndjson(path)
            else:
                result = {"status": "UNSUPPORTED_XLS_READER", "format": suffix, "row_count": None, "column_count": None}
        except Exception as exc:
            result = {"status": "PROFILE_ERROR", "format": suffix, "row_count": None, "column_count": None, "error": repr(exc)}
        result.update({
            "profile_version": VERSION, "snapshot_id": "PESTKG_RAW_SNAPSHOT_2026-09-23",
            "sha256": digest, "source_paths": [rel],
            "size_bytes": int(row["size_bytes"]), "generated_at": datetime.now(timezone.utc).isoformat(),
        })
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append({"relative_path": rel, "sha256": digest, "profile": result_path.name, "status": result["status"], "row_count": result.get("row_count"), "column_count": result.get("column_count")})
        print(f"SUPPLEMENT_DONE {index}/{len(items)} status={result['status']} rows={result.get('row_count')} {rel}", flush=True)
    with (out / "SUPPLEMENTARY_PROFILE_INDEX.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["relative_path", "sha256", "profile", "status", "row_count", "column_count"])
        writer.writeheader()
        writer.writerows(results)
    print(f"SUPPLEMENTARY_COMPLETE files={len(items)} status_counts={dict(Counter(x['status'] for x in results))}", flush=True)


if __name__ == "__main__":
    main()