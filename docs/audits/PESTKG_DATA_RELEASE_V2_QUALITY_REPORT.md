# PestKG Data Release v2 — Final Quality Report

**Release:** 2.0.0-internal / INTERNAL_RESEARCH_RELEASE. **Raw Snapshot:** PESTKG_RAW_SNAPSHOT_2026-09-23. **Status:** PASS with documented limitations.

## Counts

| Measure | Count |
| --- | ---: |
| Frozen source files | 72,761 |
| Primary source rows | 821,183 |
| Canonical entities | 1,103,238 |
| GlobalChemical | 0 |
| Registration | 164,249 |
| RegistrationUse | 726,840 |
| KG nodes | 1,103,238 |
| KG edges | 6,030,734 |
| Linked names | 212,108 |
| Linked identifiers | 106,771 |
| Evidence | 819,907 |
| Uncertain component rows | 29,152 |

## Gates

- A1 frozen SHA-256 list and manifest passed, with DEC-RAW-001 project-baseline limitation.
- A3 streamed 821,183 source rows; 1,288 exact source-row duplicates were retained; one ChEBI GZIP was truncated and quarantined.
- A12 canonical validation: 37 checks PASS.
- A14 graph validation: endpoint, type, predicate, evidence and self-edge checks PASS.
- A16 record provenance: 821,183/821,183. Relationship provenance: 6,030,734/6,030,734. Linked name and identifier assertions have source-field locators.
- A17: INTERNAL allowed under DEC-002; PUBLIC blocked by rights review. 14/18 source classes have partial rights evidence, 4/18 unknown.
- A18 internal release manifest, copied-file hashes and SHA256SUMS PASS.

## Identifier conflicts and quarantine

- 750 grouped ChEBI CAS association candidates and 1,283 AGROVOC search candidates remain unlinked, not exact chemical identities.
- Two single-token US CAS values failed checksum in A6; original strings remain.
- 29,152 ambiguous ingredient rows are retained for review; no source row was deleted.
- One truncated ChEBI structures GZIP is quarantined; one legacy XLS lacks a row-level profile; one supplementary file is empty.

## Known limitations

- GlobalChemical count is zero: no chemical identity was auto-approved.
- Unstructured multi-value active ingredient strings remain uncertain and are excluded from composition edges.
- Registration keys reused across distinct products are product-scoped; this avoids unsupported merge.
- Use rows preserve original field groups without creating crop-target Cartesian products.
- Formulation ownership is unverified; no HAS_FORMULATION edges are materialized.
- Supplementary assets remain source-preserved/profiled and are not silently joined to primary regulatory facts.
- Critical Registration status/validity values retain row-level Evidence, but their representative Canonical rows do not expose a separate per-value source_field column; consult source records and mapping.
- The clean handoff is a curated internal subset; full audit and source-record material remain in the engineering release.
- Public redistribution is not approved.
