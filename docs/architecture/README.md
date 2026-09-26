# PestKG architecture

PestKG is a release-aware, read-only research portal. React renders the
bilingual workspace (original MyPestKg-Beta frontend, restored verbatim),
the Java Spring Boot API exposes `/api/v1` on port 18088, DuckDB reads the
selected immutable Parquet release, and Neo4j is an optional acceleration
path for graph reads (not wired in the current build).

```mermaid
flowchart LR
  Browser[React workspace<br/>(MyPestKg-Beta original)] -->|OpenAPI typed HTTP| API[Java Spring Boot API :18088]
  API --> Manager[Release manager]
  Manager --> DuckDB[DuckDB / Parquet v1.0]
  Manager -. matching active release .-> Neo4j[Neo4j - optional]
  Pipeline[Release pipeline] --> Releases[data/releases]
  API -->|legacy paths| Compat[Compatibility layer]
  Compat --> DuckDB
  Browser -. legacy contract .-> Compat
  Contract[OpenAPI contract] --> Browser
  API --> Contract
```

## Invariants

- Each request resolves one immutable release and reports it through
  `X-PestKG-Release`.
- Neo4j is used only when its loaded release matches the active request; the
  current build reads everything through DuckDB and needs no database.
- Source entities remain jurisdiction-local; cross-country traversal uses
  published semantic-alignment relationships.
- The original frontend speaks the legacy contract; the compatibility layer
  serves those paths unchanged, alongside the new Java contract paths.

See [file governance](FILE_GOVERNANCE.md), the
[API contract](../api/API_CONTRACT_V1.1.md), and the
[deployment runbook](../operations/DEPLOYMENT.md).
