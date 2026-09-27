"""Stream primary official source CSVs in the frozen PestKG Raw Snapshot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROFILE_VERSION = "a-line-profile-v1.0.0"
EXACT_UNIQUE_LIMIT = 20_000
TOP_VALUE_LIMIT = 2_000
HLL_BITS = 12
NULL_LIKE = {"NA", "N/A", "NULL", "NONE", ".", "-", "UNKNOWN"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLASH_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
CAS = re.compile(r"^\d{2,7}-\d{2}-\d$")
PUBCHEM = re.compile(r"^\d+$")
CHEBI = re.compile(r"^(?:CHEBI:)?\d+$", re.I)
INCHIKEY = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")
INT = re.compile(r"^[+-]?\d+$")
FLOAT = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?$")
UNIT = re.compile(r"(?i)(?:\bmg\b|\bkg\b|\bg\s*/\s*(?:l|kg|ha|亩)\b|\bml\b|\bl/ha\b|%|毫升|千克|克/亩|倍液)")

FEATURE_FIELDS = {
    "AU": {"active": "ActiveIngredient", "crop": "Crop / Site / Animal", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "PesticideProduct", "source": "SourceDatasetURL"},
    "CN": {"active": "有效成分", "crop": "作物/场所", "target": "防治对象", "formulation": "剂型", "name": "农药名称", "source": None},
    "TW": {"active": "ActiveIngredient", "crop": "Crop", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "PesticideProduct", "source": "SourceURL"},
    "GB": {"active": "Active(s)", "crop": "Crop(s) (may have different Expiry Dates)", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "Product_Name", "source": "OfficialDetailSourceURL"},
    "GB-NI": {"active": "Active(s)", "crop": "Crop(s) (may have different Expiry Dates)", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "Product_Name", "source": "OfficialDetailSourceURL"},
    "HU": {"active": "ActiveIngredient", "crop": "Crop", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "PesticideProduct", "source": "SourceURL"},
    "IE": {"active": "ActiveIngredient", "crop": "Crop", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "PesticideProduct", "source": "SourceURL"},
    "JP": {"active": "有効成分", "crop": "Crop", "target": "Pest / Pathogen / Weed", "formulation": "剤型名", "name": "農薬の名称", "source": "SourceURL"},
    "KR": {"active": "ActiveIngredient", "crop": "Crop", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "상표명", "source": "SourceURL"},
    "NL": {"active": "ActiveIngredient", "crop": "Crop / Site / UseArea", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "PesticideProduct", "source": "SourceURL"},
    "NZ": {"active": "Ingredient", "crop": None, "target": None, "formulation": None, "name": "Trade Name", "source": None},
    "US": {"active": "ActiveIngredient", "crop": "Crop", "target": "Pest / Pathogen / Weed", "formulation": "FormulationType", "name": "PesticideProduct", "source": "SourceURL", "CAS": "ActiveIngredientCASNumber"},
}


class HLL:
    def __init__(self) -> None:
        self.reg = bytearray(1 << HLL_BITS)

    def add(self, value: str) -> None:
        bits = int.from_bytes(hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest(), "big")
        index = bits & ((1 << HLL_BITS) - 1)
        remain = bits >> HLL_BITS
        width = 64 - HLL_BITS
        rank = width - remain.bit_length() + 1 if remain else width + 1
        if rank > self.reg[index]:
            self.reg[index] = rank

    def estimate(self) -> int:
        m = len(self.reg)
        alpha = 0.7213 / (1 + 1.079 / m)
        raw = alpha * m * m / sum(2.0 ** (-r) for r in self.reg)
        zero = self.reg.count(0)
        if raw <= 2.5 * m and zero:
            raw = m * math.log(m / zero)
        return round(raw)


class Column:
    def __init__(self, name: str) -> None:
        self.name = name
        self.nonempty = 0
        self.blank = 0
        self.null_like = Counter()
        self.length_min: int | None = None
        self.length_max = 0
        self.length_sum = 0
        self.unique: set[str] | None = set()
        self.hll: HLL | None = None
        self.value_counts: Counter[str] | None = Counter()
        self.sample_types = Counter()
        self.date_patterns = Counter()
        self.identifier_format = Counter()
        self.unit_hits = Counter()

    def add(self, raw: str) -> None:
        value = raw.strip()
        if not value:
            self.blank += 1
            return
        self.nonempty += 1
        length = len(raw)
        self.length_min = length if self.length_min is None else min(self.length_min, length)
        self.length_max = max(self.length_max, length)
        self.length_sum += length
        if value.upper() in NULL_LIKE:
            self.null_like[value.upper()] += 1
        if self.unique is not None:
            self.unique.add(raw)
            if len(self.unique) > EXACT_UNIQUE_LIMIT:
                self.hll = HLL()
                for item in self.unique:
                    self.hll.add(item)
                self.unique = None
        else:
            assert self.hll is not None
            self.hll.add(raw)
        if self.value_counts is not None:
            self.value_counts[raw] += 1
            if len(self.value_counts) > TOP_VALUE_LIMIT:
                self.value_counts = None
        if sum(self.sample_types.values()) < 2_000:
            if INT.fullmatch(value):
                self.sample_types["integer_like"] += 1
            elif FLOAT.fullmatch(value):
                self.sample_types["decimal_like"] += 1
            elif ISO_DATE.fullmatch(value):
                self.sample_types["iso_date_like"] += 1
            elif SLASH_DATE.fullmatch(value):
                self.sample_types["slash_date_like"] += 1
            elif value.lower() in ("true", "false", "yes", "no"):
                self.sample_types["boolean_like"] += 1
            elif value.startswith(("{", "[")):
                self.sample_types["json_like"] += 1
            else:
                self.sample_types["text_like"] += 1
        name = self.name.casefold()
        is_date_field = any(token in name for token in ("date", "expiry", "expiration", "年月日", "日期", "有效期", "등록일", "valid_until", "retrievedon"))
        if is_date_field:
            if ISO_DATE.fullmatch(value):
                self.date_patterns["ISO_YYYY_MM_DD"] += 1
            elif SLASH_DATE.fullmatch(value):
                a, b, _ = value.split("/")
                self.date_patterns["SLASH_AMBIGUOUS" if int(a) <= 12 and int(b) <= 12 else "SLASH_UNAMBIGUOUS"] += 1
            else:
                self.date_patterns["OTHER"] += 1
        if "cas" in name:
            if CAS.fullmatch(value):
                self.identifier_format["CAS_SYNTAX_VALID"] += 1
            else:
                self.identifier_format["CAS_SYNTAX_OTHER"] += 1
        elif "pubchem" in name or "cid" == name:
            self.identifier_format["PUBCHEM_NUMERIC" if PUBCHEM.fullmatch(value) else "PUBCHEM_OTHER"] += 1
        elif "chebi" in name:
            self.identifier_format["CHEBI_SYNTAX_VALID" if CHEBI.fullmatch(value) else "CHEBI_SYNTAX_OTHER"] += 1
        elif "inchikey" in name:
            self.identifier_format["INCHIKEY_SYNTAX_VALID" if INCHIKEY.fullmatch(value) else "INCHIKEY_SYNTAX_OTHER"] += 1
        if any(token in name for token in ("dose", "dosage", "concentration", "content", "用药量", "使用量", "주성분함량", "농도", "濃度")):
            match = UNIT.search(value[:500])
            if match:
                self.unit_hits[match.group(0).lower()] += 1

    def result(self, rows: int) -> dict:
        if self.unique is not None:
            unique_count = len(self.unique)
            unique_method = "EXACT"
        else:
            assert self.hll is not None
            unique_count = self.hll.estimate()
            unique_method = "HLL_ESTIMATE_4096_REGISTERS"
        if self.value_counts is None:
            distribution = []
            distribution_method = "HIGH_CARDINALITY_NOT_MATERIALIZED"
        else:
            distribution = self.value_counts.most_common(10)
            distribution_method = "EXACT"
        return {
            "field": self.name,
            "storage_dtype": "raw_string",
            "inferred_type_sample": dict(self.sample_types),
            "rows": rows,
            "nonempty_count": self.nonempty,
            "blank_count": self.blank,
            "blank_rate": round(self.blank / rows, 6) if rows else None,
            "null_like_tokens_preserved": dict(self.null_like),
            "unique_count": unique_count,
            "unique_method": unique_method,
            "top_values": distribution,
            "value_distribution_method": distribution_method,
            "string_length_min": self.length_min,
            "string_length_max": self.length_max,
            "string_length_mean": round(self.length_sum / self.nonempty, 2) if self.nonempty else None,
            "date_patterns": dict(self.date_patterns),
            "identifier_format": dict(self.identifier_format),
            "unit_pattern_hits": dict(self.unit_hits),
        }


def profile_one(root: Path, source: dict, out: Path) -> dict:
    rel = source["relative_path"]
    p = root / rel
    jurisdiction = source["jurisdiction"]
    started = datetime.now(timezone.utc)
    csv.field_size_limit(1_000_000_000)
    with p.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(set(header)):
            raise ValueError(f"Duplicate columns in {rel}")
        columns = [Column(name) for name in header]
        row_count = 0
        wrong_width = 0
        duplicate_rows = 0
        row_hashes = set()
        for row in reader:
            row_count += 1
            if len(row) != len(header):
                wrong_width += 1
                if len(row) < len(header):
                    row += [""] * (len(header) - len(row))
                else:
                    row = row[: len(header)]
            digest = hashlib.blake2b(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), digest_size=16).digest()
            if digest in row_hashes:
                duplicate_rows += 1
            else:
                row_hashes.add(digest)
            for col, value in zip(columns, row):
                col.add(value)
            if row_count % 50_000 == 0:
                print(f"PROFILE_PROGRESS {jurisdiction} {row_count}", flush=True)
    fields = [col.result(row_count) for col in columns]
    byfield = {x["field"]: x for x in fields}
    features = {}
    for feature in ("active", "crop", "target", "formulation", "name", "source", "CAS", "PubChem", "ChEBI", "InChIKey", "SMILES"):
        alias = FEATURE_FIELDS.get(jurisdiction, {}).get(feature)
        if alias and alias in byfield:
            features[feature] = {
                "field": alias, "field_present": True,
                "nonempty_count": byfield[alias]["nonempty_count"],
                "coverage": round(byfield[alias]["nonempty_count"] / row_count, 6) if row_count else None,
            }
        else:
            features[feature] = {"field": alias, "field_present": False, "nonempty_count": None, "coverage": None}
    result = {
        "profile_version": PROFILE_VERSION,
        "snapshot_id": "PESTKG_RAW_SNAPSHOT_2026-09-23",
        "jurisdiction": jurisdiction,
        "source": source["source"],
        "source_path": rel,
        "source_sha256": source["sha256"],
        "size_bytes": source["size_bytes"],
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
        "column_count": len(header),
        "header": header,
        "wrong_width_rows": wrong_width,
        "duplicate_row_hash_count": duplicate_rows,
        "declared_release_rows": source["declared_release_rows"],
        "declared_rows_match": row_count == source["declared_release_rows"],
        "features": features,
        "columns": fields,
    }
    target = out / f"{jurisdiction}_{source['source']}.json"
    temp = target.with_suffix(".json.partial")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    print(f"PROFILE_DONE {jurisdiction} rows={row_count} cols={len(header)} duplicate_hash_rows={duplicate_rows}", flush=True)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", type=Path, required=True)
    ap.add_argument("--manifest-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    root = args.raw_root.resolve(strict=True)
    manifest_dir = args.manifest_dir.resolve(strict=True)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    inventory = json.loads((manifest_dir / "RAW_INPUT_INVENTORY.json").read_text(encoding="utf-8"))
    for source in inventory["primary_source_files"]:
        if args.only and source["jurisdiction"] != args.only:
            continue
        target = out / f"{source['jurisdiction']}_{source['source']}.json"
        if target.exists():
            current = json.loads(target.read_text(encoding="utf-8"))
            if current.get("source_sha256") == source["sha256"] and current.get("profile_version") == PROFILE_VERSION:
                print(f"PROFILE_SKIP_VERIFIED {source['jurisdiction']}", flush=True)
                continue
        profile_one(root, source, out)


if __name__ == "__main__":
    main()