# Multicountry Pesticide Knowledge Graph Portal

An open, bilingual research portal for exploring a federated multicountry
pesticide registration knowledge graph. The active data package is the
`PestKG_A_Data_Release_v1.0` full release (1.1M canonical entities, 6.0M kg
edges); the earlier `2026.08.3_federated` release remains the historical
federated context.

The repository contains the web application, the release-aware Java API
(Spring Boot 3 / Java 21 / DuckDB over Parquet), the release validation and
conversion pipeline, deployment configuration, and small real-data samples.
The full research archive and graph exports are intentionally kept outside
Git and mounted at runtime.

## Quick start

```powershell
# backend: Java 17+ (built with 21), Maven 3.9+ — one-shot launcher
.\tools\start-api.ps1        # builds/uses apps\java jar and starts API on http://127.0.0.1:18088

# frontend: Node 18+
npm --prefix apps/web install
npm --prefix apps/web run dev -- --host 127.0.0.1            # Vite on http://127.0.0.1:5173
```

The launcher sets the runtime environment (`PESTKG_DATA_DIR=data\releases`,
`PESTKG_STATE_DIR=data\state`,
`PESTKG_RELEASE_ID=PestKG_A_Data_Release_v1.0`) and polls port 18088 until the
API is ready. The API reads the full v1.0 Parquet release directly through
DuckDB (no database required). Every release-aware API request sends
`X-PestKG-Release`; shared links, filters, tables, graph reads, and exports
stay on one request-scoped version. A full end-to-end verification script
lives at `tools/verify.ps1` (`tools/verify.sh` on Linux/macOS).

## Frontend and API contract

The web application (`apps/web`) is the original MyPestKg-Beta frontend,
restored verbatim from the project zip (the vite dev proxy is the only local
deviation: `8000 -> 18088`). It speaks the original `/api/v1` contract
(`/stats/overview`, `/stats/countries`, `/schema`, `/search`, `/compare/{q}`,
`/graph/...` with `node_id`/`start_id`/`end_id`, single-step
`POST /exports/registration-uses`, `/downloads/{release_id}/...`,
`/releases/active`, `/health`).

The Java backend serves **both** contracts on port 18088:
- the new Java paths (`/datasets/*`, `/entities/search|{id}`, `/comparisons/q1..q5`,
  `/registration-uses/query`, two-step `POST /exports` -> `/artifacts/{jobId}/download`,
  `/releases/{id}/files/*`), and
- a compatibility layer (`CompatibilityController`) exposing every legacy
  path above with the original response shapes, so the original frontend runs
  unchanged. `/stats/overview` returns the original `version` headline-metric
  shape (`jurisdictions`, `source_records`, `country_nodes`, `country_edges`,
  `shared_nodes`, `alignment_edges`) computed live from the Parquet graph.
  The download index (`/downloads/{release_id}/index.json` + `SHA256SUMS`) is
  generated at runtime; path traversal outside the release directory returns 404.

## Repository layout

- `apps/web`: React, TypeScript, ECharts and Cytoscape research interface
  (original MyPestKg-Beta code).
- `apps/java`: Java 21, Spring Boot 3 and the release-aware API
  (`pestkg-domain`, `pestkg-release`, `pestkg-graph`, `pestkg-ingest`,
  `pestkg-presentation`, `pestkg-admin`, `pestkg-api`). It serves the
  `PestKG_A_Data_Release_v1.0` full Parquet package in `full` mode (no database
  needed). The legacy FastAPI service (`apps/api`) has been dropped.
- `packages/api-contract`: versioned OpenAPI snapshot and generated contract tooling.
- `tools`: `start-api.ps1` (launcher), `verify.ps1` / `verify.sh`
  (end-to-end verification), `prepare_v1_release.py` (release preparation).
- `research/figures`: reproducible research-figure source and tests.
- `infra`: container, reverse-proxy, deployment and Neo4j configuration.
- `data/releases`: tracked metadata and real-data sample only.
- `docs`: architecture, API, design, operations and release documentation.
- `artifacts` / `runtime`: ignored generated deliveries, images, migration
  evidence and mutable service state.

The Java v1 migration contract and temporal schema are documented in
`docs/architecture/JAVA_V1_MIGRATION.md` and `docs/api/API_CONTRACT_V1.md`.

## Release history

- `2026-08` Python/FastAPI + Neo4j prototype with the `2026.08.3_federated`
  release; blocked from public distribution by the manifest audit
  (`docs/releases/RELEASE_AUDIT_2026-08-28.md`).
- `2026-09` Java rewrite (all Python backend code replaced), DuckDB direct
  read of the v1.0 Parquet data package, original frontend restored from the
  MyPestKg-Beta zip, legacy-contract compatibility layer, port 18088.

## Licensing

Source code is MIT licensed. Project-derived knowledge graph data is prepared
for CC BY 4.0 release. Raw official snapshots and third-party reference files
must pass a separate redistribution-rights audit before public distribution.

## Deployment

The Linux image build/export, first deployment, release upgrade, health checks,
and rollback runbook is in `docs/operations/DEPLOYMENT.md`. The stable API contract is in
`docs/api/API_CONTRACT_V1.1.md` and frozen as `packages/api-contract/openapi-v1.1.json`.
