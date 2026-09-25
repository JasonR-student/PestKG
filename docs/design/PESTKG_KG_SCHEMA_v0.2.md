# PestKG Knowledge Graph Schema v0.2

## 1. Status

**Status:** Human-reviewed KG design baseline. This document records approved design decisions for human review; it is not an implemented graph release or a full-data validation report.

**Upstream baseline:** [PESTKG_CANONICAL_DATA_MODEL_v0.2.md](PESTKG_CANONICAL_DATA_MODEL_v0.2.md). The earlier [PESTKG_KG_SCHEMA_PROPOSAL_v0.1.md](PESTKG_KG_SCHEMA_PROPOSAL_v0.1.md) remains historical input. Where they differ, the Canonical Data Model v0.2 and this schema's explicit decisions govern v0.2 design.

**Validation boundary:** The complete RAR remains **CRC FAIL**. Actual counts, cardinalities, coverage, Formulation grain, relationship distribution, duplicate rates, and alignment quality are **REQUIRES FULL DATA VALIDATION**. Examples and priorities below are design policy, not measured findings.

**Approved design decisions:** GlobalChemical/local entity separation; RegistrationUse as an entity; Source, SourceSnapshot and Evidence as distinct provenance concepts; IdentityDecision in the governance layer; composition/use separation; three chemical alignment levels; UPPER_SNAKE_CASE predicates; one canonical direction per relationship; Canonical Dataset/Full Research KG/Display Graph separation; progressive exploration; and preservation of Canonical Dataset information.

## 2. Design Goals

- Give every graph node and relationship a stable meaning, direction, identity, jurisdiction context where relevant, and traceable provenance.
- Support research queries and cross-jurisdiction comparison without erasing source-local regulatory facts.
- Keep the research graph expressive but compact, and give the website a deliberate, bounded display projection.
- Make the distinction between source assertions, derived links, and reviewed identity decisions explicit.
- Define testable contracts before deciding import mappings or display limits from full data.

## 3. Non-Goals

This document does not clean data, resolve entities, migrate legacy predicates, rebuild Neo4j, prescribe every Canonical Dataset column as a graph property, or mandate that every graph element appear in the website. It does not fix observed cardinalities or quality thresholds from a damaged archive. It does not introduce a complex OWL ontology.

## 4. Relationship to Canonical Data Model v0.2

The Canonical Data Model v0.2 owns entity scope, opaque stable PestKG IDs, original and normalized values, names and external identifiers, source context, identity decisions, lifecycle, and information preservation. This KG schema maps selected canonical entities and assertions into graph semantics. It must not collapse `LocalActiveIngredient` records merely because they align to one `GlobalChemical`, or rewrite local regulatory facts as global facts.

`Name` and `ExternalIdentifier` remain canonical assertion concepts. Their original values, language, identifier scheme, provenance, and review state remain in relational/tabular side tables and searchable indexes at first; graph node materialization is optional only for a demonstrated query need. CAS, PubChem identifiers, URLs, dates, and ordinary strings are not graph nodes by default. Measurements, units, use conditions, and other detailed attributes remain preserved in the canonical layer even when the graph projects only selected properties.

## 5. Three-Layer Data Architecture

| Layer | Authority and purpose | Typical contents |
| --- | --- | --- |
| **Canonical Dataset** | Information-preserving source of truth for structured, normalized, traceable records. | Source-local records; original and normalized values; identifiers; names; measurements; evidence; identity decisions; assertion tables. |
| **Full Research Knowledge Graph** | Stable semantic extraction from canonical entities and assertions for research, comparison, analysis, graph algorithms, and releases. | Approved business nodes, verified relationships, selected provenance and candidate/governance links with status. |
| **Display Graph Projection** | Query-time or release-time subset of the Full Research KG for user exploration. It is never an independent fact source. | Bounded neighborhoods, ranked nodes and edges, display labels, filters, and expansion tokens. |

Flow: `Canonical Dataset -> Full Research KG -> Display Graph Projection`. A source record with many fields can remain complete in the Canonical Dataset while only stable semantic entities and relations enter the KG and only a useful subset reaches the UI. Simplifying either graph layer must never delete valuable canonical information. Neither all canonical fields nor all KG nodes/edges must be materialized or displayed.

## 6. Node Categories

| Category | Members | Default ordinary Display Graph behavior |
| --- | --- | --- |
| Business graph nodes | `GlobalChemical`, `LocalActiveIngredient`, `PesticideProduct`, `Registration`, `RegistrationUse`, `CropTerm`, `TargetTerm`, `FormulationTerm`, `Jurisdiction`, `CountryOrTerritory`, `RegulatoryOrganization` | Eligible, subject to filters and priority. |
| Provenance nodes | `Source`, `SourceSnapshot`, `Evidence` | Hidden by default; accessible through provenance details or research mode. |
| Governance/audit object | `IdentityDecision` | Queryable and auditable; hidden by default. Graph materialization is optional. |
| Canonical side-table/assertion concepts | `Name`, `ExternalIdentifier`, `RelationshipAssertion` | Not mandatory graph nodes. |

## 7. Core Node Types

| Node type | Stable semantic scope | Initial display priority |
| --- | --- | --- |
| `GlobalChemical` | Reviewed global chemical identity at a specified chemical granularity, never a replacement for local records. | HIGH |
| `LocalActiveIngredient` | Source/jurisdiction-local regulated active ingredient entity, retaining its original context. | HIGH |
| `PesticideProduct` | Source-local product entity and its source-asserted composition. | HIGH |
| `Registration` | Registration/authorization fact in a jurisdiction; product cardinality is unverified. | MEDIUM |
| `RegistrationUse` | First-class statement-like, source-asserted use fact with conditions. | MEDIUM |
| `CropTerm` | Crop concept used by a registration use, with source term retained canonically. | MEDIUM |
| `TargetTerm` | Pest/target concept used by a registration use. | MEDIUM |
| `FormulationTerm` | Formulation concept; owner and grain remain provisional. | LOW |
| `Jurisdiction` | Regulatory authority scope, distinct from territory itself. | HIGH |
| `CountryOrTerritory` | Geographic/territorial entity, distinct from `Jurisdiction`. | LOW |
| `RegulatoryOrganization` | Organization acting as regulator/source authority. | LOW |

Every node has a stable PestKG `node_id`, `node_type`, lifecycle/status metadata, and resolvable canonical record. Local nodes retain jurisdiction and source context. The actual entity and relationship counts are **REQUIRES FULL DATA VALIDATION**.

## 8. Provenance Nodes

`Source` denotes an abstract data source, database, regulatory public-data entry point, or publication source. `SourceSnapshot` denotes one immutable acquired version of that source. `Evidence` denotes a specific record, field, document locator, page, or other cited item supporting an assertion. They are distinct: `Source != SourceSnapshot != Evidence`.

`Source -HAS_SNAPSHOT-> SourceSnapshot` is the canonical source hierarchy. Each snapshot must resolve to its Source. Each Evidence item must resolve to its source snapshot, via stable IDs in the canonical provenance model and, where useful, a research KG linkage. A source record ID or evidence locator is not itself a global chemical identity. Snapshot immutability and acquisition metadata belong to the canonical provenance contract.

## 9. Governance Layer

`IdentityDecision` records candidate review, entity resolution, exact identity approval or rejection, reviewer/rule version, evidence, timestamps, and decision outcome as specified in the Canonical Data Model v0.2. It is a governance/audit object, not an ordinary business display node. It may be queried through canonical tables or selectively materialized in a research/governance graph. `EXACT_CHEMICAL_IDENTITY` must resolve to an IdentityDecision or an equivalent auditable decision record. A candidate cannot silently become exact through display or import logic.

## 10. Directed Edge Contract

The table defines one stored direction. “Inverse reading” describes a query interpretation, **not** a second stored edge. Cardinalities are expectations for modeling only; observed maxima/minima and compulsory participation are **REQUIRES FULL DATA VALIDATION**. All source-fact edges need the provenance contract in §15; alignment edges have the stronger requirements in §13. Display priorities are policy defaults, not measured frequencies.

| Canonical predicate | Source -> target | Meaning / inverse reading | Cardinality expectation | Provenance requirement | Display priority |
| --- | --- | --- | --- | --- | --- |
| `HAS_REGISTRATION` | `Jurisdiction -> Registration` | Registration is governed in jurisdiction / registration belongs to jurisdiction. | Jurisdiction many; registration jurisdiction context required; actual multiplicity unverified. | Registration source assertion and snapshot. | HIGH |
| `REGISTERS_PRODUCT` | `Registration -> PesticideProduct` | Registration covers product / product is registered by registration. | Potential many-to-many; **no 1:1 rule**. | Explicit record/link and snapshot. | HIGH |
| `HAS_USE` | `Registration -> RegistrationUse` | Registration has use statement / use belongs to registration. | Registration many; each use has resolvable parent; exceptions to validate. | Use record and snapshot. | HIGH |
| `USES_PRODUCT` | `RegistrationUse -> PesticideProduct` | Use statement names product / product participates in use. | Source-dependent; do not infer from registration alone without status. | Explicit source assertion or clearly marked derivation. | HIGH |
| `CONTAINS_ACTIVE_INGREDIENT` | `PesticideProduct -> LocalActiveIngredient` | Product composition contains local ingredient / ingredient is in product. | Product may contain many; actual grain unverified. | Explicit composition evidence. | HIGH |
| `USES_ACTIVE_INGREDIENT` | `RegistrationUse -> LocalActiveIngredient` | Source binds ingredient to this particular use / ingredient is used in this use. | Optional; coverage **REQUIRES FULL DATA VALIDATION**. | Explicit use-level evidence for `source_asserted`; any inference is `derived`. | MEDIUM |
| `FOR_CROP` | `RegistrationUse -> CropTerm` | Use applies to crop / crop is covered by use. | Potential many; actual grain unverified. | Use-level evidence. | HIGH |
| `FOR_TARGET` | `RegistrationUse -> TargetTerm` | Use addresses target / target is covered by use. | Potential many; actual grain unverified. | Use-level evidence. | HIGH |
| `HAS_FORMULATION` | `RegistrationUse -> FormulationTerm` **PROVISIONAL** | Use states formulation / formulation describes use. Product ownership may also exist after validation. | **REQUIRES FULL DATA VALIDATION**. | Explicit source field and owner/grain assessment. | LOW |
| `EXACT_CHEMICAL_IDENTITY` | `LocalActiveIngredient -> GlobalChemical` | Reviewed same chemical identity / global chemical has local manifestation. | Potential many locals to one global; conflicts checked. | Identifier evidence plus decision/auditable approval. | HIGH |
| `CANDIDATE_CHEMICAL_ALIGNMENT` | `LocalActiveIngredient -> GlobalChemical` | Stronger unresolved identity candidate / global chemical is candidate for local entity. | Multiple candidates allowed pending review. | Candidate evidence and review status. | HIDDEN_BY_DEFAULT |
| `LEXICAL_ALIGNMENT` | `LocalActiveIngredient -> GlobalChemical` | Name/text candidate only / global chemical is text match candidate. | Multiple candidates allowed. | Matching text, rule/version and source context. | HIDDEN_BY_DEFAULT |
| `IN_TERRITORY` | `Jurisdiction -> CountryOrTerritory` | Jurisdiction covers territory / territory is covered by jurisdiction. | Geography may be complex; actual coverage unverified. | Authoritative jurisdiction/geography source. | LOW |
| `REGULATES` | `RegulatoryOrganization -> Jurisdiction` | Organization regulates jurisdiction / jurisdiction is regulated by organization. | Potential many-to-many over time. | Authority source and validity period. | LOW |
| `HAS_SNAPSHOT` | `Source -> SourceSnapshot` | Source has immutable snapshot / snapshot comes from source. | Source many; snapshot has one primary Source. | Acquisition manifest and stable IDs. | HIDDEN_BY_DEFAULT |

No inverse edge such as `RegistrationUse -USE_OF-> Registration` is stored merely to ease traversal. Duplicate edges must be evaluated by subject, canonical predicate, object, assertion identity, validity window, and provenance, so independent source assertions are not erased as false duplicates. Accidental self-edges are invalid unless a future explicit predicate contract permits them.

## 11. Product Composition vs Use Context

`PesticideProduct -CONTAINS_ACTIVE_INGREDIENT-> LocalActiveIngredient` means composition. `RegistrationUse -USES_ACTIVE_INGREDIENT-> LocalActiveIngredient` means the source explicitly binds that ingredient to that use context. Composition does not imply that every use statement explicitly names each ingredient. A computed use-to-ingredient association may be offered as `derived` only with source assertion IDs, rule ID, pipeline version, and clear display/API labeling; it must never be emitted as a `source_asserted` use fact. Product, ingredient, and use records remain local to their source and jurisdiction.

## 12. RegistrationUse Model

`Registration -HAS_USE-> RegistrationUse` is the parent link. RegistrationUse is a first-class statement-like entity because crop, target, dose, method, timing, formulation, conditions, evidence, source context, validity, and original wording may differ per use. These details must remain in canonical records even if only a selection becomes graph properties. `USES_PRODUCT`, `FOR_CROP`, and `FOR_TARGET` express its explicit semantic participants. `USES_ACTIVE_INGREDIENT` is emitted as source-asserted only when source evidence supports it. `HAS_FORMULATION` is **PROVISIONAL**: whether formulation belongs to Product, RegistrationUse, or both is **REQUIRES FULL DATA VALIDATION**. `REGISTERS_PRODUCT` and `USES_PRODUCT` do not establish a forced 1:1 Registration-to-Product model.

## 13. Chemical Alignment Model

All three alignment predicates point `LocalActiveIngredient -> GlobalChemical`; they are separate semantic states, not interchangeable labels.

1. `LEXICAL_ALIGNMENT`: name/text-based candidate. Record matching text and method. It never triggers an automatic merge or confirmed identity.
2. `CANDIDATE_CHEMICAL_ALIGNMENT`: one or more stronger signals exist, but identity has not been approved. Preserve competing candidates, reasons, and review state.
3. `EXACT_CHEMICAL_IDENTITY`: approved identity at the **same chemical granularity**, supported by identifier evidence, applicable rule/human review, Evidence, and an IdentityDecision or equivalent auditable approval. Check conflicts before release.

Ordinary Display Graph shows only `EXACT_CHEMICAL_IDENTITY`. Candidate and lexical links are available only in explicitly labeled research/governance views. A global identity link does not merge local records or transfer a source-local regulatory claim to another jurisdiction. Actual identifier alignment quality is **REQUIRES FULL DATA VALIDATION**.

## 14. Predicate Vocabulary

Release v2 uses **UPPER_SNAKE_CASE** for canonical relationship types. The approved core vocabulary is `HAS_REGISTRATION`, `REGISTERS_PRODUCT`, `HAS_USE`, `USES_PRODUCT`, `CONTAINS_ACTIVE_INGREDIENT`, `USES_ACTIVE_INGREDIENT`, `FOR_CROP`, `FOR_TARGET`, `HAS_FORMULATION`, `EXACT_CHEMICAL_IDENTITY`, `CANDIDATE_CHEMICAL_ALIGNMENT`, `LEXICAL_ALIGNMENT`, `IN_TERRITORY`, `REGULATES`, and `HAS_SNAPSHOT`. An additional provenance link type, if materialized, needs its own typed contract and must not point a relationship at an Evidence node.

Maintain `predicate_mapping(legacy_predicate, canonical_predicate, schema_version, notes)` for imports and audit. A mapping is conditional when the old endpoint types or assertion semantics are ambiguous. Legacy camelCase and uppercase import names are historical inputs, not v0.2 synonyms. This document specifies the target convention; it does **not** migrate existing graph data.

## 15. Provenance on Relationships

A normal Neo4j relationship is not a node and cannot be targeted by `Evidence -SUPPORTS-> edge`. At runtime, each materialized graph relationship carries at least `edge_id`, `source_snapshot_id`, `source_record_id`, `evidence_id`, `assertion_status`, `valid_from`, and `valid_to`, with nullability explicitly validated by origin class. These stable IDs resolve to canonical records; additional provenance fields may include `assertion_id`, decision ID, import/release ID, and derivation metadata. `source_snapshot_id` must resolve to a `SourceSnapshot`, and a source assertion's `evidence_id` must resolve to an `Evidence` locator. A graph edge must not claim provenance that its canonical assertion lacks.

Multiple independent assertions about the same subject-predicate-object may be retained in canonical assertion records. A graph release can either materialize separate identified relationships or a documented aggregation with assertion ID references; aggregation must preserve provenance and conflicting status. Edge identity is stable within a published release or follows a documented release-stable identity scheme.

## 16. Relationship Assertion Model

Maintain `RelationshipAssertion` (or an equivalent relational table) in the canonical/research assertion layer with at least `assertion_id`, `subject_id`, `predicate`, `object_id`, `evidence_id`, `source_snapshot_id`, `assertion_status`, `confidence`, `valid_from`, and `valid_to`. It also needs `source_record_id` when available, and review/derivation references as applicable. Subject and object IDs must resolve to permitted types from §10. The assertion's predicate is canonical or is accompanied by a versioned mapping.

`RelationshipAssertion` is an auditable record, **not** a requirement to materialize one Neo4j node per assertion. This avoids unnecessary graph-node growth at research scale. Evidence may be reached from an assertion record or edge property by `evidence_id`; neither design pretends to create a Neo4j relationship to an edge. `confidence` is an assessment field, not a substitute for evidence or review. The number of assertions and materialization strategy must be validated against the recovered full dataset.

## 17. Derived Relationships

`assertion_status` distinguishes `source_asserted`, `derived`, and `reviewed`. `source_asserted` means the source directly supports that specific relation. `derived` means a reproducible rule produced it from identified source assertions and must retain `derivation_rule_id`, input/source assertion IDs, and pipeline version. `reviewed` records a human/rule approval with decision reference and evidence. These statuses may need additional lifecycle fields, but they must not be collapsed into an unexplained confidence score.

For example, a source-stated product composition is `source_asserted`; a use-to-ingredient association inferred from product composition is `derived` and labeled as such at query and display boundaries. A derived relation cannot be silently promoted to source fact. Reviewed exact identity follows §13 and §9. Re-running derivation must be reproducible from the recorded inputs and version.

## 18. Full Research KG

The Full Research KG contains the graph-appropriate subset of canonical data for research queries, cross-country comparison, knowledge discovery, statistics, graph algorithms, and graph releases. It can include all verified business nodes and relationships, selected provenance linkage, candidate alignment, and governance linkage. Inclusion follows stable semantics and query value, not the mere existence of a string, URL, date, or identifier. Research/governance queries must be able to inspect hidden-by-default links without changing what ordinary users see. Each graph release declares its canonical dataset version, schema version, predicate mapping, extraction version, and provenance resolution method.

## 19. Display Graph Projection

The Display Graph is a filtered and ranked query or release projection of the Full Research KG. It cannot invent, edit, or independently own facts. It supports a center entity, node-type, jurisdiction, and relation-type filters; bounded initial neighborhoods; click-to-expand; and documented node/edge/depth limits. It hides governance objects, candidate/lexical alignment, and internal provenance nodes by default. Exact identity is eligible for ordinary display only when its evidence and decision contract passes. A visible edge retains a route to its provenance details, even when Evidence nodes are hidden. Empty, truncated, and further-expandable states must be distinguishable to clients.

## 20. Progressive Expansion Policy

Never return every neighbor of a high-degree entity in a single ordinary display response. Request and response concepts include `center_node_id`, requested `expand_node_id`, current depth, node and edge limits, relation filters, jurisdiction filters, deterministic ranking/cursor, and `has_more` or equivalent continuation. Limits and ranking values are **PROVISIONAL** until real degree distributions are validated.

| Expanded type | Initial/next preferred neighborhood | Default exclusions |
| --- | --- | --- |
| `GlobalChemical` | Exact-aligned `LocalActiveIngredient`, grouped/filtered by `Jurisdiction`; then local entities. | Candidate/lexical links and audit nodes. |
| `LocalActiveIngredient` | Reviewed `GlobalChemical`, `PesticideProduct`, relevant `Registration`. | Unreviewed identity candidates. |
| `PesticideProduct` | Constituent `LocalActiveIngredient`, `Registration`, linked `RegistrationUse`. | Bulk evidence/internal provenance. |
| `Registration` | `PesticideProduct`, then paged `RegistrationUse`. | All use neighbors at once. |
| `RegistrationUse` | `CropTerm`, `TargetTerm`, `PesticideProduct`, explicit ingredient if present. | Inferred ingredient shown as asserted. |
| `Evidence`, `IdentityDecision` | Research/governance drill-down only. | Ordinary display graph. |

For a GlobalChemical search, the first view should surface jurisdiction and local-ingredient context; the user then expands a selected local entity to products, registrations, uses, crops, and targets. `Jurisdiction` can be represented by its node and eligible `HAS_REGISTRATION`/`IN_TERRITORY` paths or by projection grouping, without inventing a direct GlobalChemical-to-Jurisdiction fact. This is a v0.2 display policy baseline; actual sort order and caps can be tuned after full-data validation and user testing.

## 21. Display Metadata

The projection contract supplies `node_id`, `node_type`, `display_label`, `display_label_zh`, `display_label_en`, `jurisdiction_id`, `entity_status`, `short_summary`, and `display_priority`. These are display metadata, not a demand that all Canonical Dataset fields enter Neo4j. The client should never guess a label from an arbitrary raw field. Language-specific labels can be absent when unavailable, with a documented fallback to `display_label`; their actual coverage is **REQUIRES FULL DATA VALIDATION**.

Node and edge priority values are `HIGH`, `MEDIUM`, `LOW`, and `HIDDEN_BY_DEFAULT`. §7 and §10 give initial per-type priorities: for example, GlobalChemical and PesticideProduct are HIGH, RegistrationUse MEDIUM, Evidence and `LEXICAL_ALIGNMENT` HIDDEN_BY_DEFAULT. Priority guides ranking and visibility; it does not assert scientific importance. Display responses should provide edge IDs, canonical predicate, origin/status, and a provenance detail reference when an edge is shown.

## 22. Quality Gates

Every release candidate should report checks and exceptions for:

1. Unique stable node IDs and release-stable edge IDs.
2. Allowed source/target type pairs for each canonical predicate; no broken endpoints or accidental self-edge.
3. Duplicate edge/assertion detection with provenance-aware keys, preserving independent sources.
4. Canonical UPPER_SNAKE_CASE predicate vocabulary and complete legacy mapping for included inputs.
5. Exact identity conflict detection, compatible chemical granularity, evidence coverage, and auditable decision coverage.
6. Relationship provenance coverage, resolvable Evidence and SourceSnapshot links, and acquisition lineage.
7. Jurisdiction/source context on local entities and relations; valid lifecycle/entity status.
8. Display label and language fallback coverage.
9. RegistrationUse parent linkage and allowed use participants.
10. No automatic merge from lexical alignment; no candidate promoted without decision.
11. Derived relation traceability to rule, input assertions, and pipeline version.
12. Immutable published release manifest and reproducible extraction/version references.

Suggested numerical thresholds, severities, permitted null rates, and high-degree display limits are **PROVISIONAL** and **REQUIRES FULL DATA VALIDATION**. Until the RAR is recovered, report observed results only for explicitly identified accessible samples; never extrapolate their rates to the full dataset.

## 23. Ontology Boundary

The current contract is a lightweight property graph schema with typed nodes, directed predicates, properties, and validation rules. RDF export, ontology mapping, and later research extensions remain possible. Introduce complex OWL/RDFS reasoning only when concrete competency questions require it and the added maintenance cost is justified. The immediate goals are stable, queryable, displayable, maintainable, and traceable relationships.

## 24. Model Invariants

1. Every graph node has a stable PestKG ID.
2. Every graph edge has a stable `edge_id` or documented release-stable identity.
3. Every local regulatory entity retains jurisdiction and source context.
4. `EXACT_CHEMICAL_IDENTITY` requires evidence and auditable approval.
5. `LEXICAL_ALIGNMENT` never causes automatic merge.
6. Candidate alignment never becomes confirmed identity without a decision.
7. Original regulatory facts are never rewritten as global facts.
8. The Canonical Dataset remains the information-preserving source of truth.
9. The Display Graph is a projection, never an independent data source.
10. Inverse edges are not duplicated without an explicit, separately reviewed semantic reason.
11. Derived relations are traceable to inputs, rule, and pipeline version.
12. Published graph releases are immutable and versioned.
13. Product composition and use-context assertions remain distinct.
14. Each `RegistrationUse` resolves to a parent `Registration` or a documented source exception.
15. A displayed exact identity retains a path to its evidence and decision.

## 25. CURRENT → v0.2 Mapping

This is a **design mapping**, not a migration. Verify legacy endpoint types, record grain, source meaning, and provenance before conversion; quarantine ambiguous rows. The mapping table is represented by `predicate_mapping(legacy_predicate, canonical_predicate, schema_version, notes)`. Current tracked sample/release metadata include camelCase predicates, while full-import outputs also use uppercase variants; both need inventory after RAR recovery.

| Legacy predicate | v0.2 candidate | Conversion condition / caution |
| --- | --- | --- |
| `hasRegistration` | `HAS_REGISTRATION` | Only `Jurisdiction -> Registration` with valid jurisdiction context. |
| `hasProduct` | `REGISTERS_PRODUCT` | Verify `Registration -> PesticideProduct` endpoint and grain; no forced 1:1. |
| `hasRegistrationUse` | `HAS_USE` | Verify `Registration -> RegistrationUse` and parent linkage. |
| `usesProduct` | `USES_PRODUCT` | Verify `RegistrationUse -> PesticideProduct` and origin; existing sample duplicates do not establish full duplicate rate. |
| `containsActiveIngredient` | `CONTAINS_ACTIVE_INGREDIENT` | Product composition only after product/ingredient endpoints and source assertion are checked. |
| `hasActiveIngredient` | Conditional `USES_ACTIVE_INGREDIENT` or `CONTAINS_ACTIVE_INGREDIENT` | Decide from endpoints and source field; never map blindly or convert composition into source-asserted use. |
| `registeredForCrop` | `FOR_CROP` | Use-level endpoint required; reconstruct/flag cases attached only to Registration. |
| `registeredForTarget` | `FOR_TARGET` | Use-level endpoint required; preserve original source grain. |
| `hasFormulation` | `HAS_FORMULATION` **PROVISIONAL** | Owner (Product/Use/both) and grain **REQUIRES FULL DATA VALIDATION**. |
| `regulatesIn` | `REGULATES` and/or `IN_TERRITORY` | Split by actual endpoint types and meaning; do not conflate organization, jurisdiction, territory. |
| `exactMatch` | Conditional `EXACT_CHEMICAL_IDENTITY` | Legacy label alone is insufficient; require granularity, identifier evidence, and decision audit. |
| `lexicalAlignment` | `LEXICAL_ALIGNMENT` | Text candidate only; no merge or promotion. |

Any other uppercase import predicate must be inventoried against §10, not accepted solely for its casing. Mapping rows need schema version and rationale; rejected/uncertain transformations remain visible in migration planning. No current nodes, edges, imports, or releases are changed by this document.

## 26. Open Questions

These are data-dependent questions, not reopened design principles:

- What are observed Registration-to-Product and Registration-to-Use cardinalities by source and jurisdiction? Are there source-specific grain exceptions?
- Does Formulation belong to Product, RegistrationUse, or both in each source, and at what grain?
- What fraction of use records explicitly bind an active ingredient, and how often can product composition only support a derived association?
- How many existing `exactMatch`/candidate links satisfy chemical granularity, identifier, evidence, and decision requirements? What conflicts occur?
- What are full relationship distributions, duplicate rates, provenance coverage, and display-label/language coverage?
- Which display caps, sorting signals, and jurisdiction grouping work for actual high-degree entities and user tasks?

Each answer is **REQUIRES FULL DATA VALIDATION** and may refine extraction and display policy without weakening approved invariants.

## 27. Full RAR Validation Requirements

The complete RAR is currently **CRC FAIL**. Once it is recovered in a separately authorized task, validate full input manifests and checksums; enumerate source records, node/edge types and counts; profile endpoint pairs, cardinalities, relationship distribution, duplicate assertions, and provenance coverage; inspect Registration/Product/Use and Formulation grain by source; audit lexical/candidate/exact alignment evidence and conflicts; measure labels and jurisdiction context; and tune quality thresholds and display limits from observed degree distributions. Record reproducible queries, source versions, exceptions, and decisions. Until then, these are **REQUIRES FULL DATA VALIDATION**, and this design must not be represented as a fully validated or implemented release.
