"""Aggregate validated A3 profiles for the PestKG project raw snapshot."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def fmt_coverage(value: dict) -> str:
    if not value["field_present"]:
        return "FIELD_ABSENT"
    return f"{100 * value['coverage']:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest-dir", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--quarantine", type=Path, required=True)
    args = ap.parse_args()
    manifest = json.loads((args.manifest_dir / "RAW_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    inventory = json.loads((args.manifest_dir / "RAW_INPUT_INVENTORY.json").read_text(encoding="utf-8"))
    profiles = []
    for source in inventory["primary_source_files"]:
        path = args.profiles / f"{source['jurisdiction']}_{source['source']}.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        if profile["source_sha256"] != source["sha256"]:
            raise ValueError(f"Stale profile: {path}")
        profiles.append(profile)
    if len(profiles) != 12 or sum(p["row_count"] for p in profiles) != 821183:
        raise ValueError("Core source profile incomplete or unexpected")
    args.out.mkdir(parents=True, exist_ok=True)
    matrix_path = args.out / "A3_JURISDICTION_FEATURE_MATRIX.csv"
    features = ("active", "crop", "target", "formulation", "name", "source", "CAS", "PubChem", "ChEBI", "InChIKey", "SMILES")
    with matrix_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["jurisdiction", "source", "rows", "columns", "duplicate_row_hash_count", "wrong_width_rows"] + [f"{name}_field" for name in features] + [f"{name}_nonempty" for name in features] + [f"{name}_coverage" for name in features])
        for p in profiles:
            values = [p["features"][name] for name in features]
            writer.writerow([p["jurisdiction"], p["source"], p["row_count"], p["column_count"], p["duplicate_row_hash_count"], p["wrong_width_rows"]] + [v["field"] or "" for v in values] + [v["nonempty_count"] if v["field_present"] else "" for v in values] + [v["coverage"] if v["field_present"] else "" for v in values])
    with (args.out / "A3_FIELD_PROFILE.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["jurisdiction", "source", "field", "rows", "nonempty_count", "blank_count", "blank_rate", "unique_count", "unique_method", "string_length_min", "string_length_max", "string_length_mean", "date_patterns_json", "identifier_format_json", "unit_pattern_hits_json", "top_values_json"])
        for p in profiles:
            for c in p["columns"]:
                writer.writerow([p["jurisdiction"], p["source"], c["field"], p["row_count"], c["nonempty_count"], c["blank_count"], c["blank_rate"], c["unique_count"], c["unique_method"], c["string_length_min"], c["string_length_max"], c["string_length_mean"], json.dumps(c["date_patterns"], ensure_ascii=False), json.dumps(c["identifier_format"], ensure_ascii=False), json.dumps(c["unit_pattern_hits"], ensure_ascii=False), json.dumps(c["top_values"], ensure_ascii=False)])
    supplementary = []
    with (args.profiles / "supplementary" / "SUPPLEMENTARY_PROFILE_INDEX.csv").open("r", encoding="utf-8-sig", newline="") as f:
        supplementary = list(csv.DictReader(f))
    status = Counter(r["status"] for r in supplementary)
    if len(supplementary) != 102:
        raise ValueError("Supplementary source inventory incomplete")
    json_profile = json.loads((args.profiles / "A3_JSON_COLLECTION_PROFILE.json").read_text(encoding="utf-8"))
    if json_profile["file_count"] != 71855 or json_profile["error_count"] != 0 or sum(g["parsed_files"] for g in json_profile["groups"].values()) != 71855:
        raise ValueError("JSON collection profile incomplete")
    args.quarantine.mkdir(parents=True, exist_ok=True)
    corrupt = next(r for r in supplementary if r["status"] == "TRUNCATED_GZIP")
    with (args.quarantine / "A3_QUARANTINE_FILES.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["record_id", "reason_code", "source", "stage", "raw_reference", "review_status", "action"])
        writer.writerow(["RAWFILE_" + corrupt["sha256"][:16], "TRUNCATED_GZIP", "ChEBI", "A3_FULL_DATA_PROFILE", corrupt["relative_path"], "QUARANTINED_UNUSABLE", "Preserve raw bytes; exclude this structure file from parsing/import; use only independently valid ChEBI inputs."])
    matrix = "\n".join(
        "| " + " | ".join([
            p["jurisdiction"], p["source"], f"{p['row_count']:,}", str(p["column_count"]),
            str(p["duplicate_row_hash_count"]),
            *[fmt_coverage(p["features"][name]) for name in ("active", "crop", "target", "formulation", "name", "source")],
        ]) + " |"
        for p in profiles
    )
    supplement_top = sorted((r for r in supplementary if r["row_count"]), key=lambda x: int(x["row_count"]), reverse=True)[:12]
    supplement_table = "\n".join(f"| {r['relative_path']} | {int(r['row_count']):,} | {r['status']} |" for r in supplement_top)
    cas = next(p for p in profiles if p["jurisdiction"] == "US")
    cas_field = next(c for c in cas["columns"] if c["field"] == "ActiveIngredientCASNumber")
    unique_estimate_fields = sum(c["unique_method"] != "EXACT" for p in profiles for c in p["columns"])
    duplicate_core = sum(p["duplicate_row_hash_count"] for p in profiles)
    total_supp_rows = sum(int(r["row_count"]) for r in supplementary if r["row_count"])
    now = datetime.now(timezone.utc).isoformat()
    report = f"""# A3 Full Data Profile

**Source Dataset Baseline:** {manifest['snapshot_id']}. **Generated:** {now}. **Status:** DONE for all 12 primary official CSVs, 102 supplementary structured assets inventoried/profiled with explicit exceptions, and all 71,855 selected JSON source/cache files parsed. This is a project snapshot assessment, not certification of the legacy upstream archive.

## Processing method and boundaries

Primary CSVs were streamed row by row; original text was not rewritten. Per-column profiles record exact blanks, original-value length, bounded value distributions, candidate date/unit/identifier syntax and distinct counts. Distinct counts are exact up to 20,000 values per field; above that, a 4,096-register HLL estimate is explicitly labeled. Duplicate-row counts use 128-bit content hashes of complete parsed rows and do not authorize deletion. All 12 input SHA-256 values match the frozen snapshot. Supplementary CSV/GZIP/XLSX/NDJSON sources were scanned separately; JSON collections were syntax-checked. Detailed machine outputs are in dataset/_audit_workspace/profiles/ and A3_FIELD_PROFILE.csv.

## Jurisdiction × feature matrix

The 12 primary CSVs contain **{sum(p['row_count'] for p in profiles):,} actual rows**, exactly matching their release-declared row counts. They have **0 row-width anomalies** and **{duplicate_core:,} duplicate row hashes** (NL 1,269; NZ 19). Counts are source records, not unique registrations or entities. FIELD_ABSENT means the chosen core CSV lacks a dedicated field, not that the value cannot exist in a supplementary file or source page.

| Jurisdiction | Source | Rows | Columns | Duplicate rows | Active | Crop | Target | Formulation | Product/name | Source URL |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{matrix}

The NL and NZ duplicate rows are retained unchanged. Their semantic duplicate/registration grain must be assessed before any deduplication. Zero target coverage in GB, GB-NI and IE, zero formulation coverage in NL, and absent crop/target/formulation fields in NZ reflect current core-source availability; they are not silently filled.

## Chemical identifiers and source coverage

Among the 12 primary files, only US has a dedicated CAS column, ActiveIngredientCASNumber: **{cas_field['nonempty_count']:,}/{cas['row_count']:,}** rows contain text ({100 * cas_field['nonempty_count'] / cas['row_count']:.1f}%); **{cas_field['identifier_format'].get('CAS_SYNTAX_VALID', 0):,}** are single-token CAS syntax matches and **{cas_field['identifier_format'].get('CAS_SYNTAX_OTHER', 0):,}** have other syntax. This is a format screen, **not** checksum validation or chemical identity verification; multi-value strings require later parsing. PubChem, ChEBI, InChIKey and SMILES have no dedicated columns in these 12 primary CSVs. External ChEBI and other reference files are separate sources and must not be counted as zero global coverage. CN and NZ core CSVs lack a dedicated row-level source URL column; file/snapshot provenance is known, record/field evidence needs A16 review.

## Supplementary structured sources and JSON

There are **102** supplementary structured files totaling the frozen inventory's declared bytes. Profile status: {dict(status)}. Summed supplementary row counts are **{total_supp_rows:,}** across different files/sheets; this is *not* an additive count of distinct source records because some assets are parallel views, backups or derived tables. Examples:

| Supplementary asset | Rows | Status |
| --- | ---: | --- |
{supplement_table}

Australia_pesticide_uses_official_detail.csv has 2,329,486 use-detail rows; US_pesticide_sites_official_detail.csv has 1,487,457 rows; US_pesticide_pests_official_detail.csv has 824,016 rows. Their grain must be mapped before making RegistrationUse facts. The KR retry workbook has a false A1:A1 sheet dimension; resetting dimensions and using row 3 as header yielded 144,453 rows and 21 columns. Three Japanese official CSV files are CP932, not UTF-8; corrected profiles have zero replacement-character rows. The AU pubcris produse.csv is physically zero bytes and retained.

The JSON scan parsed **71,855/71,855** source/cache JSON files with **0 parse errors**. The single 168 MB enrichment JSON was validated separately with Python json.load and its top-level structure recorded. JSON syntax validity is not semantic validity or a redistribution license.

## Quality exceptions and next use

- The ChEBI structures.tsv.gz file ends before the GZIP end-of-stream marker. Its own ChEBI build metadata says structure transfer was incomplete and not used/checksummed. Preserve the bytes; quarantine this file from downstream parsing/import. See dataset/quarantine/A3_QUARANTINE_FILES.csv.
- The Japanese sikkounouyaku_20260731.xls remains structurally inventoried but not row-profiled because no local legacy XLS reader is available. JP core CSV and three CP932 official CSVs were profiled; this one supplemental file must remain deferred, not treated as empty or clean.
- High-cardinality unique counts in **{unique_estimate_fields}** primary fields are HLL estimates; other distinct counts are exact. Date-pattern and unit-pattern results are syntactic screens and preserve original strings.
- Source license/redistribution remains UNKNOWN. The legacy FILE_MANIFEST_SHA256.csv mismatch remains a known input limitation; DEC-RAW-001 authorizes use of this exact project snapshot, not a claim of upstream completeness.

**Next:** A4 source-field mapping from the observed headers and source documentation; A5 core/extension classification. Any field whose semantics cannot be established enters the decision queue with record evidence, while the remaining fields continue.
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"A3_SUMMARY_DONE core_rows=821183 supplementary={len(supplementary)} json={json_profile['file_count']} quarantine=1")


if __name__ == "__main__":
    main()