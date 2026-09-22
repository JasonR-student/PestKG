# Multicountry Pesticide Knowledge Graph Portal

An open, bilingual research portal for exploring the federated multicountry
pesticide registration knowledge graph release `2026.08.3_federated`.

The repository contains the web application, read-only API, release validation
and conversion pipeline, deployment configuration, and a small real-data
sample. The 1.6 GiB research archive and full graph exports are intentionally
kept outside Git and mounted at runtime.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".\apps\api[dev]"
npm --prefix apps/web install

$env:PESTKG_DATA_DIR="data/releases"
.\.venv\Scripts\python -m uvicorn pestkg_api.main:app --app-dir apps/api/src --reload --port 8000
npm --prefix apps/web run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. The Vite development server proxies `/api` and
`/downloads` to the API on port 8000.

The selected immutable release is stored in the URL as `?release=...`; every
release-aware API request also sends `X-PestKG-Release`. Shared links, filters,
tables, graph reads, and exports therefore stay on one request-scoped version.

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
- `apps/api`: FastAPI, DuckDB and optional Neo4j query service.
- `packages/api-contract`: versioned OpenAPI snapshot and generated contract tooling.
- `tools/release-pipeline`: release extraction, validation, sampling and Parquet conversion.
- `research/figures`: reproducible research-figure source and tests.
- `infra`: container, reverse-proxy, deployment and Neo4j configuration.
- `data/releases`: tracked metadata and real-data sample only.
- `docs`: architecture, API, design, operations and release documentation.
- `artifacts`: ignored generated deliveries, images and migration evidence.
- `runtime`: ignored mutable service state and caches.

## Licensing

Source code is MIT licensed. Project-derived knowledge graph data is prepared
for CC BY 4.0 release. Raw official snapshots and third-party reference files
must pass a separate redistribution-rights audit before public distribution.

## Deployment

The Linux image build/export, first deployment, release upgrade, health checks,
and rollback runbook is in `docs/operations/DEPLOYMENT.md`. The stable API contract is in
`docs/api/API_CONTRACT_V1.1.md` and frozen as `packages/api-contract/openapi-v1.1.json`.
