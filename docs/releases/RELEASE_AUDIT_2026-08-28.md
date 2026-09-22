# Release audit: 2026-08-28

## Scope

- Input archive: `multicountry_pesticide_kg_research.rar`
- Candidate release: `2026.08.3_federated`
- Audit date: 2026-08-28

## Passed

- `06_neo4j_import/nodes.csv.gz` matches its declared byte count and SHA-256.
- `06_neo4j_import/relationships.csv.gz` matches its declared byte count and SHA-256.
- All compressed Q1-Q5 result files match their declared byte counts and SHA-256 values.
- Full Parquet materialization completed from 1,253,222 nodes and 9,791,548 relationships.
- The materialized release contains 820,231 RegistrationUse rows across 12 jurisdictions.
- Materialized validation found zero broken edges, zero duplicate alignment edges, zero non-alignment cross-jurisdiction links, and zero RegistrationUse rows missing provenance.
- The analytics output contains 39 Parquet files totaling 478,671,047 bytes.

## Blocking finding

The top-level `manifest_sha256.csv` does not match multiple text files inside
the supplied RAR. Examples include country `manifest.json` files, validation
reports, deployment documentation and scripts. The differences are not fully
explained by CRLF/LF normalization. The archive must not be published as an
immutable, checksummed release in this state.

## Required correction

1. Rebuild the RAR from the intended final release directory without modifying files after manifest generation.
2. Generate `manifest_sha256.csv` from the exact bytes that will be archived.
3. Re-extract the final archive with 7-Zip on Windows or a Unicode-safe extractor on Linux.
4. Run `tools/release-pipeline/prepare_release.py` without bypassing strict manifest verification.
5. Publish only after the full preparation, analytics validation, API smoke tests and browser tests pass.

The external knowledge-base source files remain excluded until their
redistribution rights are audited separately.
