# PestKG V1.1 acceptance record

Date: 2026-08-29

## Automated verification

- Python API and pipeline: 25 tests passed.
- OpenAPI: `packages/api-contract/openapi-v1.1.json` exactly matched the generated application
  contract.
- Python bytecode compilation: passed for `apps/api/src` and
  `tools/release-pipeline`.
- Release CLI: deep download checksum validation and repository smoke test
  passed for `2026.08.3_federated`.
- Frontend lint: passed with no warnings.
- Frontend unit tests: 3 passed.
- Frontend production build: passed.
- Playwright against the built Nginx/Caddy images: 9 passed; the mobile-only
  overflow test was intentionally skipped in the desktop project.
- Docker Compose development and production configurations: parsed.
- Bash syntax: passed for build, export, release, rollback, and smoke scripts.
- API, Web, and Caddy containers: healthy.

## Container delivery

| Image | Local image ID | Size |
| --- | --- | ---: |
| `pestkg/api:1.1.0-local` | `sha256:c316695472be6b7da20af7fe1404bb99939a14e585c56ad2e1303e738ae41c8f` | 112,851,825 bytes |
| `pestkg/web:1.1.0-local` | `sha256:b8dc078d16184a8263237d110d379166e6698a14d5bc9287f56be5432dc50369` | 26,822,118 bytes |
| `caddy:2.11.4-alpine` | `sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648` | 23,925,148 bytes |
| `neo4j:2026.02.2` | `sha256:5ab4ab0358cfbc0bd44cd381d54010d017d53fe7a3326fd995f672a0c48b18b2` | 384,596,838 bytes |

Offline bundle:

- File: `runtime/images/pestkg-images-1.1.0-local.tar.gz`
- Size: 546,697,929 bytes
- SHA-256: `115de2fadc3c93b2f840b6fe676a2a5fcd6cbc168c37c1924874ca8df0461b96`
- `sha256sum -c` and `gzip -t`: passed.
- Docker image manifest: `runtime/images/pestkg-images-1.1.0-local.manifest.json`.

The bundle is intentionally outside Git under `runtime/`.

## Proxy and release checks

The built stack was exercised through Caddy at `http://localhost:18081`:

- Readiness returned `ready` and release `2026.08.3_federated`.
- Overview returned the requested release in both body and
  `X-PestKG-Release`.
- A supplied `X-Request-ID` was preserved.
- Registration-use filtering returned a row.
- The versioned download index returned the matching release.
- Page URLs acquired and preserved `?release=2026.08.3_federated`.

## Sample-mode latency baseline

Measurements used warmed local containers and the tracked real-data sample.
They are regression baselines, not full-release capacity results.

| Operation | Requests | P50 | P95 | Max |
| --- | ---: | ---: | ---: | ---: |
| Overview | 30 | 13.3 ms | 17.5 ms | 23.9 ms |
| Search | 30 | 32.1 ms | 37.1 ms | 37.3 ms |
| Combined filter | 30 | 59.5 ms | 75.2 ms | 77.8 ms |
| One-hop graph | 20 | 81.3 ms | 92.8 ms | 93.3 ms |
| Sample CSV export | 10 | 51.3 ms | 61.1 ms | 61.1 ms |

## Visual verification

- Concept and design inventory: `docs/design/FRONTEND_CONCEPT_V1.1.md`.
- Fidelity ledger: `docs/design/FIDELITY_LEDGER_V1.1.md`.
- Native desktop viewport: 1440 x 1000.
- Native mobile viewport: 390 x 844.
- Both final overview renders had `scrollWidth === innerWidth`.
- The explore render showed a populated table, selected row, and nonblank
  Cytoscape graph with 52 nodes and 51 relationships.

## Remaining release gates

- Public distribution remains blocked. The 2026-08-26 RAR contains text files
  that do not match its top-level manifest. Rebuild the archive and manifest
  before publishing data or enabling public downloads.
- The full 9,739,818-relation Neo4j import was not executed from the tracked
  sample repository. Run the documented full-profile release procedure after
  a corrected immutable release is available.
- The 100,000-row, 60-second export target and full-data P95 targets require the
  corrected full release on the intended 8-core, 32 GB, 500 GB SSD host.
- Vite reports a large lazy-loaded ECharts bundle. This does not block current
  workflows, but route-level chart payload optimization remains available.
- FastAPI tests emit an upstream Starlette deprecation warning about the test
  client dependency; it does not affect runtime responses.
