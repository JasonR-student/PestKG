# PestKG Java v1 migration

## Purpose

Java v1 moves application code to Java 21, Spring Boot 3, Spring MVC and Vaadin
24 while preserving the research semantics already present in the repository:
immutable releases, release-bound cursors, jurisdiction-local identity,
explicit cross-country alignment and source-level provenance.

## Runtime boundaries

The canonical facts are stored as immutable Parquet/object-store artifacts and
append-only PostgreSQL temporal rows. Neo4j is a release-scoped read projection
for bounded graph traversal. Presentation datasets are materialized artifacts,
not ad hoc values computed by the browser.

## Current implementation status

The first Java foundation reads the tracked sample CSV files and exposes the v1
REST endpoints plus Vaadin Overview, Explore, Graph, Releases and Methods pages.
The production adapters for Parquet, PostgreSQL, Neo4j bulk import and OIDC
identity are represented by module boundaries and schemas but are not enabled
until the full data package is received.

## Migration order

1. Rebuild the incoming source package and manifest; keep the current release
   private while its distribution status is blocked.
2. Register the release and persist artifact/source snapshot metadata.
3. Load canonical entity, edge and registration-use tables with record hashes.
4. Build the release-specific Neo4j projection and verify graph counts.
5. Materialize overview, coverage and Q1-Q5 presentation datasets with a
   presentation manifest.
6. Activate the release atomically after API, graph and provenance checks.

## Compatibility notes

The Java service uses a new v1 contract as requested. It intentionally does not
claim wire compatibility with the Python v1.1 contract, but it retains the
semantics that prevent release mixing and unverifiable research results.
