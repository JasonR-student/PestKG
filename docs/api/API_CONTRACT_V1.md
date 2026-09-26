# PestKG Java API v1

All successful data responses contain `api_version`, `release_id`,
`schema_version`, `valid_at`, `transaction_at`, `data`, `meta`, `links` and
`provenance`. Requests may select a release with `?release=` or
`X-PestKG-Release`; if both are provided they must match.

Public reads include release catalog, dataset overview/coverage/schema, entity
search/detail/history/provenance, registration-use queries, graph neighborhood
and path queries, Q1-Q5 comparisons, export jobs and artifact downloads.

Errors use an `error` object with `code`, `message`, `details` and `requestId`.
Every request receives `X-Request-ID`.

The current implementation (2026-09) runs against the full `PestKG_A_Data_Release_v1.0` Parquet package in `full` mode on port 18088; Parquet/Neo4j adapters preserve the same release and temporal filters. A compatibility layer additionally serves the original Python v1.1 wire paths for the restored MyPestKg-Beta frontend.
