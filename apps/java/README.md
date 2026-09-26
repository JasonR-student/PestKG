# PestKG Java v1 foundation

This directory contains the first Java 21 implementation of the release-aware
PestKG portal. It is intentionally runnable against the tracked sample release
before the incoming full data package is mapped.

## Modules

- `pestkg-domain`: API and temporal domain records.
- `pestkg-release`: PostgreSQL/Flyway-compatible temporal schema.
- `pestkg-graph`: Neo4j driver boundary.
- `pestkg-ingest`: Spring Batch ingestion boundary.
- `pestkg-presentation`: reproducible presentation dataset manifest.
- `pestkg-admin`: secured administration boundary.
- `pestkg-api`: Spring MVC API, sample repository and Vaadin UI.
- `pestkg-ui`: Vaadin dependency boundary for a future split deployment.

## Local run

Install Maven 3.9+ and run from the repository root:

```powershell
mvn -f apps/java/pom.xml spring-boot:run -pl pestkg-api -am
```

The API listens on `http://127.0.0.1:18088`. Release directories are resolved
from `PESTKG_DATA_DIR`, and the active release from
`PESTKG_STATE_DIR/active-release.json`, with the tracked release as fallback.

## Data adaptation status (2026-09-26)

The Java service now serves the supplied full data package
`PestKG_A_Data_Release_v1.0` end to end (mode `full`, not `sample`):

- All API reads run against the v1.0 Parquet layout through DuckDB
  (`kg/nodes.parquet`, `kg/edges.parquet`, `canonical/*.parquet`).
- `registration-uses` rows are enriched on first query: product labels from
  `kg` nodes, and structured crop/target/active-ingredient refs from
  `FOR_CROP` / `FOR_TARGET` / `CONTAINS_ACTIVE_INGREDIENT` edges.
- Search, neighborhood and shortest-path endpoints treat user input as a
  literal (LIKE wildcards escaped) and no longer fail on an empty query.
- JSON output uses snake_case (`label_original`, `published_at`, ...) to match
  the established web contract; internal refs parsing is annotation-driven.
- The API needs no database: the PostgreSQL/Flyway deps in `pestkg-release`
  are optional and do not reach the API classpath (no DataSource
  auto-configuration), so startup requires no datasource URL.
- The web app (`apps/web`) is fully switched to the Java contract: every
  client call uses `/api/v1` Java paths (`/datasets/overview`,
  `/entities/search`, `/registration-uses/query`, ...), the CSV export uses
  the two-step job flow (`POST /api/v1/exports` -> GET
  `/api/v1/artifacts/{jobId}/download`), and the pages render Java-only
  fields (overview `inventory`, release `active`/`integrity`, ...).
- The API listens on **port 18088** (`server.port: ${PORT:18088}` in
  `pestkg-api/src/main/resources/application.yml`); the Vite dev proxy
  (`apps/web/vite.config.ts`) targets `http://127.0.0.1:18088` and
  `tools/verify.ps1` smoke-tests the same port.

No PostgreSQL or Neo4j adapter is wired yet; those remain module boundaries.
