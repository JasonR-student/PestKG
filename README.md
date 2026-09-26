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
# backend: Maven 3.9+ and JDK 21
$env:PESTKG_DATA_DIR="data/releases"
$env:PESTKG_STATE_DIR="data/state"
$env:PESTKG_RELEASE_ID="PestKG_A_Data_Release_v1.0"
mvn -f apps/java/pom.xml spring-boot:run -pl pestkg-api -am   # API on http://127.0.0.1:18088

# frontend: Node 18+
npm --prefix apps/web install
npm --prefix apps/web run dev -- --host 127.0.0.1            # Vite on http://127.0.0.1:5173
```

The API reads the full v1.0 Parquet release directly through DuckDB (no
database required). Every release-aware API request sends `X-PestKG-Release`;
shared links, filters, tables, graph reads, and exports stay on one
request-scoped version. A full end-to-end verification script lives at
`tools/verify.ps1`.

## Full release preparation

```powershell
.\.venv\Scripts\python tools/release-pipeline/prepare_release.py `
  --archive "E:\下载\multicountry_pesticide_kg_research.rar" `
  --output runtime/releases
```

The command extracts only the immutable federated release, verifies every
entry in `manifest_sha256.csv`, builds and revalidates jurisdiction-partitioned
Parquet tables, creates sample JSON-LD/GraphML plus full N-Triples, and builds a
versioned download index. Use `--skip-rdf` for a faster preflight run.

On Windows, RAR preparation requires 7-Zip on `PATH` or through `SEVEN_ZIP`;
Windows `bsdtar` does not preserve all filenames safely for this archive.

## Current distribution gate

The supplied archive dated 2026-08-26 is not yet eligible for public
distribution: the Neo4j and Q1-Q5 machine files match their declared hashes,
but multiple text entries differ from the top-level manifest. The strict
pipeline intentionally stops before publishing. See
`docs/releases/RELEASE_AUDIT_2026-08-28.md` and rebuild the archive plus manifest first.

## Repository layout

- `apps/web`: React, TypeScript, ECharts and Cytoscape research interface.
- `apps/java`: Java 21, Spring Boot 3 and the release-aware API. It serves the
  `PestKG_A_Data_Release_v1.0` full Parquet package in `full` mode (no database
  needed). The legacy FastAPI service (`apps/api`) has been dropped.
- `packages/api-contract`: versioned OpenAPI snapshot and generated contract tooling.
- `tools/release-pipeline`: release extraction, validation, sampling and Parquet conversion.
- `research/figures`: reproducible research-figure source and tests.
- `infra`: container, reverse-proxy, deployment and Neo4j configuration.
- `data/releases`: tracked metadata and real-data sample only.
- `docs`: architecture, API, design, operations and release documentation.
- `artifacts`: ignored generated deliveries, images and migration evidence.
- `runtime`: ignored mutable service state and caches.

The Java v1 migration contract and temporal schema are documented in
`docs/architecture/JAVA_V1_MIGRATION.md` and
`docs/api/API_CONTRACT_V1.md`. Run it from the repository root with Maven:

```powershell
mvn -f apps/java/pom.xml spring-boot:run -pl pestkg-api -am
```

## Licensing

Source code is MIT licensed. Project-derived knowledge graph data is prepared
for CC BY 4.0 release. Raw official snapshots and third-party reference files
must pass a separate redistribution-rights audit before public distribution.

## Deployment

The Linux image build/export, first deployment, release upgrade, health checks,
and rollback runbook is in `docs/operations/DEPLOYMENT.md`. The stable API contract is in
`docs/api/API_CONTRACT_V1.1.md` and frozen as `packages/api-contract/openapi-v1.1.json`.
