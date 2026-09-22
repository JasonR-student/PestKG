from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


COUNTRY_META = {
    "AU": ("AUS", "036"),
    "CN": ("CHN", "156"),
    "TW": ("TWN", "158"),
    "GB": ("GBR", "826"),
    "GB-NI": ("GBR", "826"),
    "HU": ("HUN", "348"),
    "IE": ("IRL", "372"),
    "JP": ("JPN", "392"),
    "KR": ("KOR", "410"),
    "NL": ("NLD", "528"),
    "NZ": ("NZL", "554"),
    "US": ("USA", "840"),
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_portal_metadata(
    release_dir: Path,
    *,
    published_at: str | None = None,
    distribution_status: str = "ready",
) -> tuple[Path, Path, Path]:
    release_dir = release_dir.resolve()
    release_id = release_dir.name
    validation = release_dir / "04_validation"
    build_report = read_json(validation / "federated_build_report.json")
    inventory = read_json(validation / "entity_relation_inventory.json")
    integrity = read_json(validation / "final_integrity_report.json")
    coverage = read_csv(validation / "semantic_coverage_corrected.csv")
    coverage_by_country = {row["jurisdiction"]: row for row in coverage}

    country_manifests = build_report.get("country_manifests")
    if not isinstance(country_manifests, list) or not country_manifests:
        raise RuntimeError("federated_build_report.json has no country_manifests")

    countries: list[dict[str, Any]] = []
    for raw_country in country_manifests:
        if not isinstance(raw_country, dict):
            raise RuntimeError("Invalid country manifest entry")
        jurisdiction = str(raw_country.get("jurisdiction", ""))
        if not jurisdiction:
            raise RuntimeError("Country manifest is missing jurisdiction")
        iso3, map_id = COUNTRY_META.get(jurisdiction, (jurisdiction, ""))
        countries.append(
            {
                **raw_country,
                "iso3": iso3,
                "map_id": map_id,
                "coverage": coverage_by_country.get(jurisdiction, {}),
            }
        )

    source_records = sum(int(country.get("source_rows", 0)) for country in countries)
    release = {
        "release_id": release_id,
        "schema_version": "1.0",
        "title": "Federated multicountry pesticide registration knowledge graphs",
        "published_at": published_at or date.today().isoformat(),
        "cutoff": build_report.get("cutoff", ""),
        "status": build_report.get("status", "release_ready"),
        "distribution_status": distribution_status,
        "known_limitations": [],
        "license": "CC BY 4.0 for project-derived data",
        "inventory": {
            "jurisdictions": int(integrity["country_graphs"]),
            "source_records": source_records,
            "country_nodes": int(integrity["country_nodes"]),
            "country_edges": int(integrity["country_edges"]),
            "shared_nodes": int(integrity["shared_external_nodes"]),
            "alignment_edges": int(integrity["unique_alignment_edges"]),
        },
        "node_types": inventory.get("country_node_types", {}),
        "relation_types": inventory.get("country_relation_types", {}),
        "coverage": coverage,
        "integrity": integrity,
    }
    schema = {
        "schema_version": "1.0",
        "node_fields": [
            "id",
            "type",
            "label_original",
            "label_en",
            "jurisdiction",
            "source_record_id",
            "source_url",
            "properties_json",
        ],
        "edge_fields": [
            "id",
            "start_id",
            "predicate",
            "end_id",
            "jurisdiction",
            "source_record_id",
            "source_url",
            "properties_json",
        ],
        "node_types": inventory.get("country_node_types", {}),
        "relation_types": inventory.get("country_relation_types", {}),
        "federation_predicates": inventory.get("federation_predicates", {}),
        "rules": {
            "country_local_identity": "Local regulatory entities are never merged across jurisdictions.",
            "cross_country_alignment": "Cross-country traversal uses exactMatch or lexicalAlignment.",
            "formal_crop_target_pair": "Formal comparison defaults to official_pair_asserted.",
        },
    }

    release_path = release_dir / "release.json"
    countries_path = release_dir / "countries.json"
    schema_path = release_dir / "schema.json"
    write_json(release_path, release)
    write_json(countries_path, countries)
    write_json(schema_path, schema)
    return release_path, countries_path, schema_path


def ensure_portal_metadata(
    release_dir: Path,
    *,
    published_at: str | None = None,
    distribution_status: str = "ready",
) -> tuple[Path, Path, Path]:
    paths = tuple(
        release_dir / name for name in ("release.json", "countries.json", "schema.json")
    )
    if all(path.is_file() for path in paths):
        metadata = read_json(paths[0])
        if metadata.get("release_id") != release_dir.name:
            raise RuntimeError(
                "Existing release.json does not match the extracted release directory"
            )
        return paths
    if any(path.exists() for path in paths):
        missing = [path.name for path in paths if not path.is_file()]
        raise RuntimeError(f"Portal metadata is incomplete: {missing}")
    return build_portal_metadata(
        release_dir,
        published_at=published_at,
        distribution_status=distribution_status,
    )
