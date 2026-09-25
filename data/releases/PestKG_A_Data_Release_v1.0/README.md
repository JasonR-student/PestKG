# PestKG A-Line Data Release v1.0

**Type:** INTERNAL RESEARCH RELEASE. **Raw Snapshot:** PESTKG_RAW_SNAPSHOT_2026-09-23.

This package contains source-backed Canonical data and the Full Research KG built with the approved v0.2 models. Internal research use is allowed; public redistribution is BLOCKED_BY_RIGHTS_REVIEW.

| Folder | Purpose |
| --- | --- |
| canonical/ | Entities, names, identifiers, registrations and uses |
| kg/ | Directed nodes and edges for graph analysis |
| docs/ | Short field, schema and quality guides |
| metadata/ | Manifest and SHA-256 checksums |

For graph queries, read kg/nodes.parquet and kg/edges.parquet. For entity and registration analysis, read canonical/.

Canonical IDs are opaque registry-issued PestKG IDs. Local entity IDs retain jurisdiction and source context. CAS, ChEBI and other external identifiers are attributes, never internal primary keys.

| Measure | Count |
| --- | ---: |
| Canonical entities | 1,103,238 |
| GlobalChemical | 0 |
| Registrations | 164,249 |
| Registration uses | 726,840 |
| KG nodes | 1,103,238 |
| KG edges | 6,030,734 |

**Key limits:** No GlobalChemical or exact chemical identity was invented. Ambiguous multi-ingredient records remain unresolved for review. One truncated ChEBI structures file is excluded. The approved Raw Snapshot does not prove the old archive was complete. Source rights have not been cleared for public redistribution. See docs/QUALITY_REPORT.md.
