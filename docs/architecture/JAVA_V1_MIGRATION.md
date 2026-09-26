# PestKG Java v1 migration

## Purpose

Java v1 moves application code to Java 21, Spring Boot 3 and Spring MVC while
preserving the research semantics already present in the repository:
immutable releases, release-bound cursors, jurisdiction-local identity,
explicit cross-country alignment and source-level provenance.

## Runtime boundaries

The canonical facts are stored as immutable Parquet artifacts in the release
package (`kg/nodes.parquet`, `kg/edges.parquet`, `canonical/*.parquet`) and
read directly through DuckDB. Neo4j remains a release-scoped read projection
option for bounded graph traversal but is **not** wired in the current build;
PostgreSQL/Flyway boundaries exist as modules but are optional and not on the
API classpath. Presentation datasets are materialized/aggregated values served
by the API, not ad hoc values computed by the browser.

## Current implementation status (2026-09-26)

The Java service serves the supplied full data package
`PestKG_A_Data_Release_v1.0` end to end in `full` mode:

- All API reads run against the v1.0 Parquet layout through DuckDB.
- Comparison questions Q1–Q5 aggregate live from `kg/edges.parquet` +
  `canonical/registration_uses.parquet`; countries are derived from the 12
  `Jurisdiction` nodes with live edge counts; overview coverage is computed
  from kg edges.
- JSON output uses snake_case to match the web contract
  (`label_original`, `published_at`, `release_id`, ...).
- The web app (`apps/web`) is the original MyPestKg-Beta frontend restored
  verbatim; it speaks the legacy contract, which the backend serves through a
  compatibility layer (`CompatibilityController`) with the original response
  shapes (`/stats/overview` returns `version` plus
  `jurisdictions/source_records/country_nodes/country_edges/shared_nodes/
  alignment_edges`, `/downloads/{release_id}/index.json` + `SHA256SUMS` are
  generated at runtime).
- The API listens on **port 18088** (`server.port: ${PORT:18088}`); the vite
  dev proxy targets `http://127.0.0.1:18088`; `tools/start-api.ps1` launches
  it with the v1.0 environment and `tools/verify.ps1` smoke-tests the same port.

## Migration order (historical)

1. Rebuild the incoming source package and manifest; keep the release private
   while its distribution status is blocked.
2. Register the release and persist artifact/source snapshot metadata.
3. Load canonical entity, edge and registration-use tables with record hashes.
4. Build the release-specific Neo4j projection and verify graph counts
   (optional; DuckDB direct read covers the current profile).
5. Materialize overview, coverage and Q1–Q5 presentation datasets.
6. Activate the release atomically after API, graph and provenance checks.

## Compatibility notes

The Java service exposes a new v1 contract (`/datasets/*`, `/entities/*`,
`/comparisons/*`, two-step exports) **and** a compatibility layer that
reproduces the Python v1.1 wire paths (`/stats/*`, `/schema`, `/search`,
`/compare/{q}`, `/graph/*` with `node_id`/`start_id`/`end_id`, single-step
`/exports/registration-uses`, `/downloads/{release_id}/*`, `/releases/active`,
`/health`) so the original frontend runs without modification. Both share the
same release-aware envelope and version-isolation semantics.
