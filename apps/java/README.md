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

The API listens on `http://127.0.0.1:8081`. The sample release directory is
resolved from `PESTKG_DATA_DIR` and the active release from
`PESTKG_STATE_DIR/active-release.json`, with the tracked release as fallback.

The Java service is a private validation build while the supplied release has
`blocked_pending_manifest_rebuild` status.
