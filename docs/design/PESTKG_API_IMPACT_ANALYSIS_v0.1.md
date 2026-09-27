# PestKG API Impact Analysis v0.1 — proposal for human review

**Scope:** React/TypeScript + FastAPI/Python + DuckDB/Neo4j is the formal stack. This is an API requirement analysis, not an endpoint implementation or contract change. Java/Vaadin remains a frozen experimental reference. Full RAR identifier and provenance coverage is unknown after CRC failure.

| CURRENT API / code | Current behavior | Future requirement if Canonical Model is approved |
| --- | --- | --- |
| `GET /api/v1/search` in [`search.py`](../../apps/api/src/pestkg_api/routers/search.py), [`repository.py`](../../apps/api/src/pestkg_api/repository.py) | ID, original/English label substring; entity type, jurisdiction, limit | Search original/preferred names and synonyms across languages, normalized forms and explicit identifiers (CAS, PubChem CID, ChEBI, InChIKey) with match type, source and confidence. Keep local vs global result types visible. |
| `GET /api/v1/entities/{node_id}` | One local/shared node with source URL/record ID | Preserve old node IDs or provide versioned redirects/aliases; return canonical links, names, external IDs, evidence summary, unresolved/conflicting identity state. |
| `GET /api/v1/graph/neighborhood`, `/graph/path` | Bounded local graph, optional Neo4j with DuckDB fallback | Typed traversal policies; distinguish reviewed exact chemical identity from candidate lexical alignment; include edge evidence and release context. Avoid treating candidate alignment as equivalence in paths. |
| `GET /api/v1/compare/{question}` | Q1–Q5 prepared comparisons; source pairing status in rows | Record which canonical/identifier mapping and official pairing rule produced each comparison; expose uncertainty and source record links, preserve jurisdiction-local facts. |
| `POST /api/v1/registration-uses/query` | Filters plus cursor; row combines use, product, crop/target and status | Add optional canonical chemical/identifier filters, date/validity and evidence filters only after full-data coverage is measured. Preserve source `use_id` and pairing status. |
| Registration API | No independent `/registrations` endpoint in current FastAPI routes | Decide whether a dedicated registration detail/history endpoint is justified; do not advertise one as existing. |
| `GET /api/v1/stats/*`, `/schema` | Release counts, coverage and current schema | Report coverage by identifier, evidence level, source/jurisdiction and Schema version; distinguish source missingness from transform failure. |
| `/downloads/{release_id}/...`, release APIs | Versioned metadata and artifacts with checksums | Release v2 descriptor with archive hash, schema/pipeline/source versions, quality report, rights decision and immutable artifact manifest. Block downloads for failed gates. |

## Search requirement tiers

1. **Exact identity lookup:** internal ID, source record ID, verified external identifier, registration number. Return namespace and jurisdiction; never treat a bare number as globally unique.
2. **Normalized term lookup:** Unicode NFKC, case folding, whitespace and punctuation handling in a separate search index. Retain the original text, language and source. Use name normalization only to generate candidates.
3. **Synonym/name lookup:** canonical, original, translated and curated synonyms with language tag and provenance. Trade/product names must not be conflated with chemical identity.
4. **Fuzzy discovery:** optional and clearly ranked as approximate; do not output `exactMatch` from similarity alone. Show why the result matched and surface competing candidates.

The tracked comparison sample contains `CHEBI:` IDs, but the `nodes` sample has no top-level CAS/PubChem/ChEBI/InChIKey columns. Search index and API response design must wait for trustworthy full-data identifier profiling. Any future API version should keep `/api/v1` behavior stable while introducing explicit canonical fields or new versioned endpoints; generated TypeScript contract changes require tests before adoption.

## Migration questions for review

- Are old local IDs permanent public URLs? If so, mappings/redirects must be part of every release.
- Should a global chemical page show regulatory statuses as jurisdiction-scoped facts, with no synthesized global status?
- Which provenance level is mandatory for search hits, graph edges, exports and comparisons?
- Should identifiers with conflicts return all candidate entities and a conflict status rather than one default entity?
