# PestKG API contract v1.1

This document defines the compatibility contract for `/api/v1`. The canonical
machine-readable snapshot is `packages/api-contract/openapi-v1.1.json`.

## Compatibility rules

- `api_version` changes only when the HTTP behavior changes. `schema_version`
  identifies the release data schema and may evolve independently.
- Additive response fields are backward compatible. Removing or renaming a
  field, changing its type, or changing filter semantics requires a new API
  version or a documented deprecation period.
- Node IDs, relationship IDs, `source_record_id`, jurisdiction codes, and
  source values are emitted unchanged from the selected immutable release.
- Every successful `/api/v1` data response is an envelope containing
  `api_version`, `release_id`, `schema_version`, `data`, `meta`, and `links`.
- Every response carries `X-Request-ID`. Release-aware responses also carry
  `X-PestKG-Release` and `Vary: X-PestKG-Release`.

## Release selection

Release-aware endpoints accept either `?release=<release_id>` or the
`X-PestKG-Release` request header. When neither is present, the server resolves
the current active release at the start of the request. When both are present,
their values must match or the request fails with
`release_selector_conflict`.

A resolved release is fixed for the lifetime of one request. Hot activation
therefore cannot mix two releases within a response. An unknown, malformed, or
unavailable release fails closed rather than silently falling back.

## Pagination and limits

- Search returns at most 100 entities.
- Registration-use pages contain 1 to 200 rows.
- Cursors are opaque, URL-safe values bound to the selected `release_id` and a
  canonical hash of all filters. Cross-release and cross-filter reuse fails.
- Neighborhood responses are limited to two hops, 1,000 nodes, and 2,000
  relationships.
- Shortest paths are limited to three hops.
- Synchronous CSV exports are limited to 100,000 rows. Larger requests return
  `export_too_large` and a versioned bulk-download location.

## Entity boundaries

Country-local entities are never merged directly across jurisdictions.
Cross-country traversal is possible only through published `exactMatch` or
`lexicalAlignment` relationships and their shared semantic nodes. The API
parses stored `properties_json` into the structured `properties` object but
does not rename source properties.

## Errors

Errors use a stable `error` object:

```json
{
  "detail": {"code": "release_not_found"},
  "error": {
    "code": "release_not_found",
    "message": "Release directory not found",
    "details": {"release_id": "example"},
    "request_id": "correlation-id"
  }
}
```

`detail` remains during the v1 compatibility window for existing clients.
New clients should use `error.code`, `error.message`, `error.details`, and the
matching `X-Request-ID` response header.

## Release lifecycle

`GET /api/v1/releases` lists discovered versions and registry state.
`GET /api/v1/releases/active` reports the active immutable version.
Registration and activation are administrative CLI operations and are not
exposed through the anonymous public API.

Neo4j is accepted for graph queries only when its loaded release matches the
active request release. Otherwise graph reads use the selected release's
DuckDB/Parquet repository, preventing cross-version graph results.
