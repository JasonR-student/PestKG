from __future__ import annotations

import csv
import io
import json
import threading
from pathlib import Path
from typing import Any, Iterable

import duckdb

from .models import RegistrationUseFilters


NODE_COLUMNS = (
    "id",
    "type",
    "label_original",
    "label_en",
    "jurisdiction",
    "source_record_id",
    "source_url",
    "properties_json",
)

COMPARISON_QUESTIONS = ("q1", "q2", "q3", "q4", "q5")

_COMPARISON_FILES = {
    "q1": "Q1_crop_active_ingredients_cross_country.csv.gz",
    "q2": "Q2_same_target_products_cross_country.csv.gz",
    "q3": "Q3_shared_crop_target_combinations.csv.gz",
    "q4": "Q4_active_ingredient_formulations.csv.gz",
    "q5": "Q5_active_ingredient_country_use_profiles.csv.gz",
}

_EMPTY_COVERAGE = {
    "jurisdiction": "",
    "source_language": "",
    "records": "",
    "crop_source": "",
    "target_source": "",
    "active_source": "",
    "formulation_source": "",
    "crop_english": "",
    "target_english": "",
    "active_english": "",
    "formulation_english": "",
    "crop_english_given_source": "",
    "target_english_given_source": "",
    "active_english_given_source": "",
    "formulation_english_given_source": "",
}


class DataRepository:
    def __init__(self, release_dir: Path) -> None:
        self.release_dir = release_dir
        self._local = threading.local()

        manifest_path = release_dir / "metadata" / "manifest.json"
        if manifest_path.is_file() and (release_dir / "kg" / "nodes.parquet").is_file():
            self.layout = "v1_manifest"
            self._init_v1_manifest(manifest_path)
        else:
            self.layout = "legacy"
            self._init_legacy()

    def _init_legacy(self) -> None:
        release_dir = self.release_dir
        self.metadata = self._read_json("release.json")
        download_index = release_dir / "downloads/index.json"
        if download_index.exists():
            with download_index.open("r", encoding="utf-8") as handle:
                self.metadata = {**self.metadata, "artifacts": json.load(handle)["artifacts"]}
        else:
            self.metadata = {**self.metadata, "artifacts": []}
        self.schema = self._read_json("schema.json")
        self.countries = self._read_json("countries.json")

        analytics_dir = release_dir / "analytics"
        sample_dir = release_dir / "sample"
        partitioned_nodes = analytics_dir / "nodes"
        if partitioned_nodes.exists():
            self.mode = "full"
            self.nodes_source = partitioned_nodes
            self.edges_source = analytics_dir / "edges"
            self.uses_source = analytics_dir / "registration_uses"
            self.source_format = "parquet"
        elif (analytics_dir / "nodes.parquet").exists():
            self.mode = "full"
            self.nodes_source = analytics_dir / "nodes.parquet"
            self.edges_source = analytics_dir / "edges.parquet"
            self.uses_source = analytics_dir / "registration_uses.parquet"
            self.source_format = "parquet"
        else:
            self.mode = "sample"
            self.nodes_source = sample_dir / "nodes.csv"
            self.edges_source = sample_dir / "edges.csv"
            self.uses_source = sample_dir / "registration_uses.csv"
            self.source_format = "csv"

        for source in (self.nodes_source, self.edges_source, self.uses_source):
            if not source.exists():
                raise FileNotFoundError(f"Required data file not found: {source}")

    def _init_v1_manifest(self, manifest_path: Path) -> None:
        """Initialise from a v1.0 manifest layout (kg/ + canonical/ parquet)."""
        release_dir = self.release_dir
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        release_id = release_dir.name
        distribution = manifest.get("distribution_status", {})
        if isinstance(distribution, dict):
            dist_status = distribution.get("internal", "unknown")
        else:
            dist_status = str(distribution)
        self._manifest = manifest
        self.metadata = {
            "release_id": release_id,
            "title": manifest.get("release_name", release_id),
            "schema_version": manifest.get("schema_version", "1.0"),
            "published_at": manifest.get("created_at", ""),
            "cutoff": manifest.get("raw_snapshot_id", ""),
            "status": manifest.get("release_type", "unknown"),
            "distribution_status": dist_status,
            "known_limitations": manifest.get("known_limitations", []),
            "license": manifest.get("release_type", "INTERNAL_RESEARCH_RELEASE"),
            "inventory": {
                "jurisdictions": 0,
                "source_records": manifest.get("row_counts", {}).get("canonical_entities", 0),
                "country_nodes": 0,
                "country_edges": 0,
                "shared_nodes": 0,
                "alignment_edges": 0,
            },
            "integrity": {"passed": True, "checks": {}},
            "node_types": {},
            "relation_types": {},
            "coverage": [],
            "artifacts": [],
        }
        self.schema = {
            "schema_version": manifest.get(
                "kg_schema_version", manifest.get("schema_version", "PESTKG_KG_SCHEMA_v0.2")
            ),
            "node_fields": list(NODE_COLUMNS),
            "edge_fields": [
                "id", "start_id", "predicate", "end_id",
                "jurisdiction", "source_record_id", "source_url", "properties_json",
            ],
            "node_types": {},
            "relation_types": {},
            "federation_predicates": {},
            "rules": {},
        }
        self.countries = []  # derived lazily once the duckdb connection is built
        self.mode = "full"
        self.source_format = "parquet"
        self.nodes_source = release_dir / "kg" / "nodes.parquet"
        self.edges_source = release_dir / "kg" / "edges.parquet"
        self.uses_source = release_dir / "canonical" / "registration_uses.parquet"
        self._v1_derived = False
        for source in (self.nodes_source, self.edges_source, self.uses_source):
            if not source.exists():
                raise FileNotFoundError(f"Required data file not found: {source}")
        # Eagerly build the connection so node_types/relation_types/countries
        # are derived and the overview/countries endpoints see populated data.
        self._connection()

    def _read_json(self, name: str) -> Any:
        path = self.release_dir / name
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _path_literal(path: Path) -> str:
        return str(path.resolve()).replace("\\", "/").replace("'", "''")

    def _parquet_source(self, path: Path) -> str:
        source = path / "**/*.parquet" if path.is_dir() else path
        return self._path_literal(source)

    def _connection(self) -> duckdb.DuckDBPyConnection:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            return connection

        connection = duckdb.connect(database=":memory:")
        if self.layout == "v1_manifest":
            self._create_v1_views(connection)
        elif self.source_format == "parquet":
            connection.execute(
                "CREATE VIEW nodes AS SELECT * FROM "
                f"read_parquet('{self._parquet_source(self.nodes_source)}', hive_partitioning=true)"
            )
            connection.execute(
                "CREATE VIEW edges AS SELECT * FROM "
                f"read_parquet('{self._parquet_source(self.edges_source)}', hive_partitioning=true)"
            )
            connection.execute(
                "CREATE VIEW registration_uses AS SELECT * "
                f"FROM read_parquet('{self._parquet_source(self.uses_source)}', hive_partitioning=true)"
            )
        else:
            connection.execute(
                "CREATE VIEW nodes AS SELECT * "
                f"FROM read_csv_auto('{self._path_literal(self.nodes_source)}', header=true, all_varchar=true)"
            )
            connection.execute(
                "CREATE VIEW edges AS SELECT * "
                f"FROM read_csv_auto('{self._path_literal(self.edges_source)}', header=true, all_varchar=true)"
            )
            connection.execute(
                "CREATE VIEW registration_uses AS SELECT * "
                f"FROM read_csv_auto('{self._path_literal(self.uses_source)}', header=true, all_varchar=true)"
            )
        self._register_comparison_views(connection)
        self._local.connection = connection
        if self.layout == "v1_manifest" and not self._v1_derived:
            self._derive_v1_dynamic(connection)
            self._v1_derived = True
        return connection

    def _register_comparison_views(
        self, connection: duckdb.DuckDBPyConnection
    ) -> None:
        """Pre-register competency-question CSVs as views.

        Avoids repeated ``read_csv_auto`` schema inference on every
        ``/api/v1/compare/{question}`` request.
        """
        for question, filename in _COMPARISON_FILES.items():
            path = self._comparison_path(question, filename)
            if path.exists():
                connection.execute(
                    f"CREATE VIEW comparison_{question} AS SELECT * "
                    f"FROM read_csv_auto('{self._path_literal(path)}', header=true, all_varchar=true)"
                )

    def _create_v1_views(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Create column-mapping views over the v1.0 parquet layout.

        The v1.0 schema (node_id/node_type/...) is projected onto the legacy
        contract (id/type/label_original/...) so the rest of the repository
        code is unchanged.
        """
        nodes_src = self._parquet_source(self.nodes_source)
        edges_src = self._parquet_source(self.edges_source)
        uses_src = self._parquet_source(self.uses_source)
        connection.execute(
            f"""
            CREATE VIEW nodes AS SELECT
                node_id AS id,
                node_type AS type,
                display_label AS label_original,
                display_label AS label_en,
                jurisdiction_id AS jurisdiction,
                '' AS source_record_id,
                '' AS source_url,
                extension_properties AS properties_json
            FROM read_parquet('{nodes_src}', hive_partitioning=true)
            """
        )
        connection.execute(
            f"""
            CREATE VIEW edges AS SELECT
                edge_id AS id,
                source_id AS start_id,
                predicate,
                target_id AS end_id,
                '' AS jurisdiction,
                source_record_id,
                '' AS source_url,
                json_object(
                    'assertion_status', assertion_status,
                    'evidence_id', evidence_id,
                    'source_snapshot_id', source_snapshot_id,
                    'origin_kind', origin_kind,
                    'derivation_rule_id', derivation_rule_id,
                    'pipeline_version', pipeline_version,
                    'display_priority', display_priority,
                    'default_hidden', default_hidden
                ) AS properties_json
            FROM read_parquet('{edges_src}', hive_partitioning=true)
            """
        )
        registrations_path = self.release_dir / "canonical" / "registrations.parquet"
        if registrations_path.exists():
            reg_src = self._parquet_source(registrations_path)
            connection.execute(
                f"""
                CREATE VIEW registration_uses AS SELECT
                    u.registration_use_id AS use_id,
                    u.jurisdiction_id AS jurisdiction,
                    u.product_id,
                    '' AS product_label_original,
                    '' AS product_label_en,
                    '' AS product_label_search,
                    '' AS active_ingredients_search,
                    u.crop_original AS crops_search,
                    u.target_original AS targets_search,
                    u.formulation_original AS formulations_search,
                    '[]' AS active_ingredients_json,
                    '[]' AS crops_json,
                    '[]' AS targets_json,
                    '[]' AS formulations_json,
                    coalesce(r.original_status, '') AS registration_status,
                    u.pairing_status,
                    coalesce(r.registration_date_normalized, '') AS registration_date,
                    coalesce(r.expiry_date_normalized, '') AS expiry_date,
                    u.source_record_id,
                    '' AS source_url
                FROM read_parquet('{uses_src}', hive_partitioning=true) u
                LEFT JOIN read_parquet('{reg_src}', hive_partitioning=true) r
                    ON u.registration_id = r.registration_id
                """
            )
        else:
            connection.execute(
                f"""
                CREATE VIEW registration_uses AS SELECT
                    registration_use_id AS use_id,
                    jurisdiction_id AS jurisdiction,
                    product_id,
                    '' AS product_label_original,
                    '' AS product_label_en,
                    '' AS product_label_search,
                    '' AS active_ingredients_search,
                    crop_original AS crops_search,
                    target_original AS targets_search,
                    formulation_original AS formulations_search,
                    '[]' AS active_ingredients_json,
                    '[]' AS crops_json,
                    '[]' AS targets_json,
                    '[]' AS formulations_json,
                    '' AS registration_status,
                    pairing_status,
                    '' AS registration_date,
                    '' AS expiry_date,
                    source_record_id,
                    '' AS source_url
                FROM read_parquet('{uses_src}', hive_partitioning=true)
                """
            )

    def _derive_v1_dynamic(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Fill node_types/relation_types/countries from the parquet data."""
        node_types = dict(
            connection.execute("SELECT type, count(*) FROM nodes GROUP BY type").fetchall()
        )
        relation_types = dict(
            connection.execute(
                "SELECT predicate, count(*) FROM edges GROUP BY predicate"
            ).fetchall()
        )
        self.metadata["node_types"] = node_types
        self.metadata["relation_types"] = relation_types
        self.metadata["inventory"]["jurisdictions"] = node_types.get("Jurisdiction", 0)
        self.metadata["inventory"]["country_nodes"] = node_types.get("CountryOrTerritory", 0)
        self.schema["node_types"] = node_types
        self.schema["relation_types"] = relation_types
        self.countries = self._derive_countries(connection)

    def _derive_countries(self, connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        """Project Jurisdiction/CountryOrTerritory nodes onto CountryData records."""
        rows = connection.execute(
            """
            SELECT id, type, label_original, jurisdiction
            FROM nodes
            WHERE type IN ('Jurisdiction', 'CountryOrTerritory')
            """
        ).fetchall()
        jurisdiction_names: dict[str, str] = {}
        for node_id, node_type, label, _jurisdiction_id in rows:
            if node_type == "Jurisdiction":
                jurisdiction_names[node_id] = label or ""
        countries: list[dict[str, Any]] = []
        for node_id, node_type, label, jurisdiction_id in rows:
            if node_type != "CountryOrTerritory":
                continue
            countries.append(
                {
                    "jurisdiction": jurisdiction_id or "",
                    "jurisdiction_name": jurisdiction_names.get(
                        jurisdiction_id or "", jurisdiction_id or ""
                    ),
                    "sovereign_country": label or "",
                    "site_id": "",
                    "official_url": "",
                    "source_file": "",
                    "source_sha256": "",
                    "source_snapshot_eligible": False,
                    "source_rows": 0,
                    "skipped_rows": 0,
                    "nodes": 0,
                    "edges": 0,
                    "broken_edges": 0,
                    "graph_scope": "v1_manifest",
                    "language": "und",
                    "iso3": "",
                    "map_id": node_id,
                    "coverage": dict(_EMPTY_COVERAGE),
                }
            )
        return countries

    def _create_v1_views(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Create column-mapping views over the v1.0 parquet layout.

        The v1.0 schema (node_id/node_type/...) is projected onto the legacy
        contract (id/type/label_original/...) so the rest of the repository
        code is unchanged.
        """
        nodes_src = self._parquet_source(self.nodes_source)
        edges_src = self._parquet_source(self.edges_source)
        uses_src = self._parquet_source(self.uses_source)
        connection.execute(
            f"""
            CREATE VIEW nodes AS SELECT
                node_id AS id,
                node_type AS type,
                display_label AS label_original,
                display_label AS label_en,
                jurisdiction_id AS jurisdiction,
                '' AS source_record_id,
                '' AS source_url,
                extension_properties AS properties_json
            FROM read_parquet('{nodes_src}', hive_partitioning=true)
            """
        )
        connection.execute(
            f"""
            CREATE VIEW edges AS SELECT
                edge_id AS id,
                source_id AS start_id,
                predicate,
                target_id AS end_id,
                '' AS jurisdiction,
                source_record_id,
                '' AS source_url,
                json_object(
                    'assertion_status', assertion_status,
                    'evidence_id', evidence_id,
                    'source_snapshot_id', source_snapshot_id,
                    'origin_kind', origin_kind,
                    'derivation_rule_id', derivation_rule_id,
                    'pipeline_version', pipeline_version,
                    'display_priority', display_priority,
                    'default_hidden', default_hidden
                ) AS properties_json
            FROM read_parquet('{edges_src}', hive_partitioning=true)
            """
        )
        registrations_path = self.release_dir / "canonical" / "registrations.parquet"
        if registrations_path.exists():
            reg_src = self._parquet_source(registrations_path)
            connection.execute(
                f"""
                CREATE VIEW registration_uses AS SELECT
                    u.registration_use_id AS use_id,
                    u.jurisdiction_id AS jurisdiction,
                    u.product_id,
                    '' AS product_label_original,
                    '' AS product_label_en,
                    '' AS product_label_search,
                    '' AS active_ingredients_search,
                    u.crop_original AS crops_search,
                    u.target_original AS targets_search,
                    u.formulation_original AS formulations_search,
                    '[]' AS active_ingredients_json,
                    '[]' AS crops_json,
                    '[]' AS targets_json,
                    '[]' AS formulations_json,
                    coalesce(r.original_status, '') AS registration_status,
                    u.pairing_status,
                    coalesce(r.registration_date_normalized, '') AS registration_date,
                    coalesce(r.expiry_date_normalized, '') AS expiry_date,
                    u.source_record_id,
                    '' AS source_url
                FROM read_parquet('{uses_src}', hive_partitioning=true) u
                LEFT JOIN read_parquet('{reg_src}', hive_partitioning=true) r
                    ON u.registration_id = r.registration_id
                """
            )
        else:
            connection.execute(
                f"""
                CREATE VIEW registration_uses AS SELECT
                    registration_use_id AS use_id,
                    jurisdiction_id AS jurisdiction,
                    product_id,
                    '' AS product_label_original,
                    '' AS product_label_en,
                    '' AS product_label_search,
                    '' AS active_ingredients_search,
                    crop_original AS crops_search,
                    target_original AS targets_search,
                    formulation_original AS formulations_search,
                    '[]' AS active_ingredients_json,
                    '[]' AS crops_json,
                    '[]' AS targets_json,
                    '[]' AS formulations_json,
                    '' AS registration_status,
                    pairing_status,
                    '' AS registration_date,
                    '' AS expiry_date,
                    source_record_id,
                    '' AS source_url
                FROM read_parquet('{uses_src}', hive_partitioning=true)
                """
            )

    def _derive_v1_dynamic(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Fill node_types/relation_types/countries from the parquet data."""
        node_types = dict(
            connection.execute("SELECT type, count(*) FROM nodes GROUP BY type").fetchall()
        )
        relation_types = dict(
            connection.execute(
                "SELECT predicate, count(*) FROM edges GROUP BY predicate"
            ).fetchall()
        )
        self.metadata["node_types"] = node_types
        self.metadata["relation_types"] = relation_types
        self.metadata["inventory"]["jurisdictions"] = node_types.get("Jurisdiction", 0)
        self.metadata["inventory"]["country_nodes"] = node_types.get("CountryOrTerritory", 0)
        self.schema["node_types"] = node_types
        self.schema["relation_types"] = relation_types
        self.countries = self._derive_countries(connection)

    def _derive_countries(self, connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        """Project Jurisdiction/CountryOrTerritory nodes onto CountryData records."""
        rows = connection.execute(
            """
            SELECT id, type, label_original, jurisdiction
            FROM nodes
            WHERE type IN ('Jurisdiction', 'CountryOrTerritory')
            """
        ).fetchall()
        jurisdiction_names: dict[str, str] = {}
        for node_id, node_type, label, _jurisdiction_id in rows:
            if node_type == "Jurisdiction":
                jurisdiction_names[node_id] = label or ""
        countries: list[dict[str, Any]] = []
        for node_id, node_type, label, jurisdiction_id in rows:
            if node_type != "CountryOrTerritory":
                continue
            countries.append(
                {
                    "jurisdiction": jurisdiction_id or "",
                    "jurisdiction_name": jurisdiction_names.get(
                        jurisdiction_id or "", jurisdiction_id or ""
                    ),
                    "sovereign_country": label or "",
                    "site_id": "",
                    "official_url": "",
                    "source_file": "",
                    "source_sha256": "",
                    "source_snapshot_eligible": False,
                    "source_rows": 0,
                    "skipped_rows": 0,
                    "nodes": 0,
                    "edges": 0,
                    "broken_edges": 0,
                    "graph_scope": "v1_manifest",
                    "language": "und",
                    "iso3": "",
                    "map_id": node_id,
                    "coverage": dict(_EMPTY_COVERAGE),
                }
            )
        return countries

    def _comparison_path(self, question: str, full_filename: str) -> Path:
        sample_path = self.release_dir / "sample" / "comparisons" / f"{question}.csv"
        full_path = self.release_dir / "06_competency_questions" / full_filename
        return full_path if self.mode == "full" and full_path.exists() else sample_path

    @staticmethod
    def _records(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    @staticmethod
    def _parse_json(value: Any, fallback: Any) -> Any:
        if value in (None, ""):
            return fallback
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return fallback

    def overview(self) -> dict[str, Any]:
        inventory = self.metadata["inventory"]
        return {
            "title": self.metadata["title"],
            "version": self.metadata["release_id"],
            "published_at": self.metadata["published_at"],
            "cutoff": self.metadata["cutoff"],
            "status": self.metadata["status"],
            "distribution_status": self.metadata["distribution_status"],
            "known_limitations": self.metadata["known_limitations"],
            "mode": self.mode,
            **inventory,
            "node_types": self.metadata["node_types"],
            "relation_types": self.metadata["relation_types"],
            "coverage": self.metadata["coverage"],
        }

    def search(
        self, query: str, entity_type: str | None, jurisdiction: str | None, limit: int
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if query:
            clauses.append("(label_original ILIKE ? OR label_en ILIKE ? OR id ILIKE ?)")
            needle = f"%{query}%"
            params.extend([needle, needle, needle])
        if entity_type:
            clauses.append("type = ?")
            params.append(entity_type)
        if jurisdiction:
            clauses.append("jurisdiction = ?")
            params.append(jurisdiction.upper())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        if query:
            sql = f"""
            SELECT id, type, label_original, label_en, jurisdiction,
                   source_record_id, source_url, properties_json
            FROM nodes
            {where}
            ORDER BY CASE WHEN lower(label_en) = lower(?) THEN 0 ELSE 1 END,
                     coalesce(nullif(label_en, ''), label_original)
            LIMIT ?
            """
            query_params = [*params, query, limit]
        else:
            sql = f"""
            SELECT id, type, label_original, label_en, jurisdiction,
                   source_record_id, source_url, properties_json
            FROM nodes
            {where}
            ORDER BY coalesce(nullif(label_en, ''), label_original)
            LIMIT ?
            """
            query_params = [*params, limit]
        cursor = self._connection().execute(sql, query_params)
        return [self._normalize_node(row) for row in self._records(cursor)]

    def comparison(
        self, question: str, query: str | None, jurisdiction: str | None, limit: int
    ) -> list[dict[str, Any]]:
        question = question.lower()
        if question not in COMPARISON_QUESTIONS:
            raise ValueError("Unknown competency question")
        path = self._comparison_path(question, _COMPARISON_FILES[question])
        if not path.exists():
            return []
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            columns = {
                "q1": ("crop_label_en", "active_ingredient_label_en"),
                "q2": ("target_label_en", "product_name"),
                "q3": ("crop_label_en", "target_label_en", "countries"),
                "q4": ("active_ingredient_label_en", "formulation_label_en"),
                "q5": (
                    "active_ingredient_label_en",
                    "crop_examples",
                    "target_examples",
                    "formulation_examples",
                ),
            }[question]
            clauses.append("(" + " OR ".join(f"{column} ILIKE ?" for column in columns) + ")")
            params.extend([f"%{query}%"] * len(columns))
        if jurisdiction and question != "q3":
            clauses.append("jurisdiction = ?")
            params.append(jurisdiction.upper())
        elif jurisdiction and question == "q3":
            clauses.append("countries ILIKE ?")
            params.append(f"%{jurisdiction.upper()}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        # Query the pre-registered view instead of re-reading the CSV on
        # every request.  The view is created once per connection in
        # _register_comparison_views.
        cursor = self._connection().execute(
            f"SELECT * FROM comparison_{question} {where} LIMIT ?",
            [*params, limit],
        )
        return self._records(cursor)

    def entity(self, node_id: str) -> dict[str, Any] | None:
        cursor = self._connection().execute(
            "SELECT * FROM nodes WHERE id = ? LIMIT 1", [node_id]
        )
        records = self._records(cursor)
        return self._normalize_node(records[0]) if records else None

    def query_registration_uses(
        self, filters: RegistrationUseFilters, offset: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        where, params = self._use_filter_sql(filters)
        connection = self._connection()
        # Combine count and page into a single query using a window
        # function.  count(*) OVER() is computed before LIMIT/OFFSET so
        # it yields the filtered total.  When the page is empty we fall
        # back to an explicit count (only needed for the 0-row edge case).
        cursor = connection.execute(
            f"""
            SELECT *, count(*) OVER() AS _total_count
            FROM registration_uses
            {where}
            ORDER BY jurisdiction, product_label_en, use_id
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        )
        records = self._records(cursor)
        if records:
            total = int(records[0]["_total_count"])
            for row in records:
                row.pop("_total_count", None)
        else:
            total = int(
                connection.execute(
                    f"SELECT count(*) FROM registration_uses {where}", params
                ).fetchone()[0]
            )
        return [self._normalize_use(row) for row in records], total

    def iter_registration_uses(
        self, filters: RegistrationUseFilters, limit: int
    ) -> tuple[Iterable[bytes], int]:
        where, params = self._use_filter_sql(filters)
        connection = self._connection()
        total = int(
            connection.execute(
                f"SELECT count(*) FROM registration_uses {where}", params
            ).fetchone()[0]
        )
        cursor = connection.execute(
            f"SELECT * FROM registration_uses {where} ORDER BY jurisdiction, use_id LIMIT ?",
            [*params, limit],
        )
        columns = [item[0] for item in cursor.description]

        def generate() -> Iterable[bytes]:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            yield output.getvalue().encode("utf-8-sig")
            output.seek(0)
            output.truncate(0)
            while True:
                rows = cursor.fetchmany(1_000)
                if not rows:
                    break
                writer.writerows(rows)
                yield output.getvalue().encode("utf-8")
                output.seek(0)
                output.truncate(0)

        return generate(), total

    def neighborhood(
        self, node_id: str, depth: int, node_limit: int, edge_limit: int
    ) -> dict[str, Any]:
        connection = self._connection()
        # Previously this issued a separate entity() lookup for the root
        # node before starting BFS.  That round-trip is redundant because
        # the root is always part of the final node fetch.  If the node
        # does not exist, BFS finds no edges and the final fetch returns
        # an empty list, producing the same {"nodes": [], "edges": []}.
        visited = {node_id}
        frontier = {node_id}
        edge_records: dict[str, dict[str, Any]] = {}
        for _ in range(depth):
            if not frontier or len(visited) >= node_limit or len(edge_records) >= edge_limit:
                break
            ids = sorted(frontier)
            placeholders = ",".join("?" for _ in ids)
            cursor = connection.execute(
                f"""
                SELECT * FROM edges
                WHERE start_id IN ({placeholders}) OR end_id IN ({placeholders})
                LIMIT ?
                """,
                [*ids, *ids, edge_limit - len(edge_records)],
            )
            frontier = set()
            for row in self._records(cursor):
                edge_records[row["id"]] = self._normalize_edge(row)
                for candidate in (row["start_id"], row["end_id"]):
                    if candidate not in visited and len(visited) < node_limit:
                        visited.add(candidate)
                        frontier.add(candidate)

        ids = sorted(visited)
        placeholders = ",".join("?" for _ in ids)
        nodes = self._records(
            connection.execute(f"SELECT * FROM nodes WHERE id IN ({placeholders})", ids)
        )
        return {
            "nodes": [self._normalize_node(row) for row in nodes],
            "edges": list(edge_records.values()),
        }

    def shortest_path(self, start_id: str, end_id: str, max_depth: int) -> dict[str, Any]:
        if start_id == end_id:
            node = self.entity(start_id)
            return {"nodes": [node] if node else [], "edges": []}

        connection = self._connection()
        # Batched BFS with parent pointers.
        # Previous implementation issued one SQL query per visited node
        # (N+1 queries) and used list.pop(0) (O(n)) plus per-step list
        # copies for the path.  We now issue one query per BFS level,
        # use a parent map to reconstruct the path, and stop as soon as
        # the target is reached.
        parent: dict[str, tuple[str, dict[str, Any]]] = {}
        visited = {start_id}
        frontier = {start_id}
        for _ in range(max_depth):
            if not frontier:
                break
            ids = sorted(frontier)
            placeholders = ",".join("?" for _ in ids)
            cursor = connection.execute(
                f"""
                SELECT * FROM edges
                WHERE start_id IN ({placeholders}) OR end_id IN ({placeholders})
                """,
                [*ids, *ids],
            )
            next_frontier: set[str] = set()
            found = False
            for row in self._records(cursor):
                start = row["start_id"]
                end = row["end_id"]
                if start in frontier:
                    neighbor, anchor = end, start
                elif end in frontier:
                    neighbor, anchor = start, end
                else:
                    continue
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                parent[neighbor] = (anchor, self._normalize_edge(row))
                if neighbor == end_id:
                    found = True
                    break
                next_frontier.add(neighbor)
            if found:
                break
            frontier = next_frontier

        if end_id not in parent:
            return {"nodes": [], "edges": []}

        # Reconstruct path from parent pointers.
        path_nodes: list[str] = [end_id]
        path_edges: list[dict[str, Any]] = []
        current = end_id
        while current != start_id:
            anchor, edge = parent[current]
            path_nodes.append(anchor)
            path_edges.append(edge)
            current = anchor
        path_nodes.reverse()
        path_edges.reverse()

        placeholders = ",".join("?" for _ in path_nodes)
        nodes = self._records(
            connection.execute(
                f"SELECT * FROM nodes WHERE id IN ({placeholders})", path_nodes
            )
        )
        node_map = {row["id"]: self._normalize_node(row) for row in nodes}
        return {
            "nodes": [node_map[node] for node in path_nodes if node in node_map],
            "edges": path_edges,
        }

    @staticmethod
    def _use_filter_sql(filters: RegistrationUseFilters) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if filters.jurisdictions:
            placeholders = ",".join("?" for _ in filters.jurisdictions)
            clauses.append(f"jurisdiction IN ({placeholders})")
            params.extend(filters.jurisdictions)

        text_filters = {
            "product_label_search": filters.product,
            "active_ingredients_search": filters.active_ingredient,
            "crops_search": filters.crop,
            "targets_search": filters.target,
            "formulations_search": filters.formulation,
            "registration_status": filters.registration_status,
            "pairing_status": filters.pairing_status,
        }
        for column, value in text_filters.items():
            if value:
                clauses.append(f"{column} ILIKE ?")
                params.append(f"%{value}%")

        if filters.query:
            clauses.append(
                "(" + " OR ".join(
                    f"{column} ILIKE ?"
                    for column in (
                        "product_label_search",
                        "active_ingredients_search",
                        "crops_search",
                        "targets_search",
                        "formulations_search",
                    )
                ) + ")"
            )
            params.extend([f"%{filters.query}%"] * 5)

        if filters.valid_on:
            date_formats = "['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']"
            clauses.append(
                "coalesce(cast(try_strptime(nullif(registration_date, ''), "
                f"{date_formats}) AS DATE), DATE '-infinity') <= cast(? AS DATE)"
            )
            clauses.append(
                "coalesce(cast(try_strptime(nullif(expiry_date, ''), "
                f"{date_formats}) AS DATE), DATE 'infinity') >= cast(? AS DATE)"
            )
            params.extend([str(filters.valid_on), str(filters.valid_on)])

        return (f"WHERE {' AND '.join(clauses)}" if clauses else "", params)

    def _normalize_node(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        row["properties"] = self._parse_json(row.pop("properties_json", "{}"), {})
        return row

    def _normalize_edge(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        row["properties"] = self._parse_json(row.pop("properties_json", "{}"), {})
        return row

    def _normalize_use(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        for key in (
            "active_ingredients",
            "crops",
            "targets",
            "formulations",
        ):
            row[key] = self._parse_json(row.pop(f"{key}_json", "[]"), [])
        return row
