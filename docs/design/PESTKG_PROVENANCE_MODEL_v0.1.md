# PestKG Provenance Model v0.1 — proposal for human review

**Status:** design only; no source data or API changed. The original RAR failed CRC testing, so full-release provenance coverage is **UNKNOWN**. Evidence here comes from tracked metadata, sample and code.

## Current evidence by level

| Level | CURRENT evidence | Limitation |
| --- | --- | --- |
| Dataset/release | [`release.json`](../../data/releases/2026.08.3_federated/release.json) includes release ID, cutoff, publication date, license notice, source counts | Current RAR cannot be verified against the release; no archive SHA in tracked release metadata |
| Source/file | [`countries.json`](../../data/releases/2026.08.3_federated/countries.json) records site, official URL, source file path and SHA-256 | Paths refer to another machine; access dates and terms snapshots absent from this metadata |
| Record | `source_record_id` and `source_url` in tracked nodes, edges and registration-use rows | Source URL often points to site-level landing page; stable record-level resolver not proved |
| Entity | 178/202 sample nodes have both `source_record_id` and `source_url`; 24 without both are administrative/shared candidates requiring type-specific policy | Node provenance does not prove every property value's source |
| Relation | 235/235 sample edge rows have these fields, but 10 rows are exact duplicates | May identify source record, not the precise assertion or pairing evidence |
| Attribute | Some `properties_json` values and labels are exposed without a field-specific evidence key | Cannot reliably answer where a particular CAS, name, status or date value came from |
| Literature | No fixed DOI/citation fields in current release schema; external references exist in comparisons | Literature provenance coverage unknown |

The [`RDF exporter`](../../tools/release-pipeline/export_graph_formats.py) emits reified relationship statements with relationship ID, source record ID and source URL. This is a useful base for edge provenance, but it does not by itself bind every property value to a source version.

## Proposed objects and fields

`Source`: `source_id`, `source_name`, `organization`, `jurisdiction_id`, `source_type`, canonical URL, terms URL, redistribution review state. `SourceSnapshot`: immutable `snapshot_id`, `source_id`, exact file or capture hash, original path/URL, `retrieved_at` or explicit `UNKNOWN`, source version, content format, license text location. `SourceRecord`: `source_record_id`, snapshot ID, native record key, original record locator, parsing status. `Evidence`: `evidence_id`, snapshot/record ID, field or document locator, `evidence_type` (`official_record`, `document`, `publication`, `curated_review`), DOI/citation when applicable, confidence and reviewer for curated claims. `Assertion`: subject, predicate/field, original value or object, evidence ID, valid time, observed/retrieved time, release ID and derivation method.

Every assertion must be able to answer: **which source**, **which immutable snapshot**, **which record/field**, **which transformation or reviewer**, and **which release**. Use hashes and stable locators; a mutable homepage URL alone is insufficient. Store `license` and redistribution decisions at snapshot/source scope, then propagate them to derived artifacts without converting a source's rights into a blanket project-wide permission.

## Two adoption levels

| Level | Required implementation concept | Cost / benefit |
| --- | --- | --- |
| Minimum viable provenance | Every local `RegistrationUse`, product, registration and consequential edge has source ID, snapshot ID/hash, source record key, source URL, retrieved date if known, release ID. Preserve original values alongside parsed forms. | Moderate extension of existing `source_record_id/source_url`; supports citation to a source record and reproducing a release. Missing dates remain explicit UNKNOWN. |
| Research-grade provenance | Immutable evidence records for each identity mapping, relationship and critical field (status, dates, CAS, chemical identifier, dose); DOI/citation for publications; transformation lineage and human review decisions; bitemporal assertion history. | More storage and pipeline work; enables claim-level explanation, conflict review and reproducible scholarly citation. |

For `LocalActiveIngredient → GlobalChemical`, exact identity must include evidence and review decision. `lexicalAlignment` remains a candidate assertion with its own method and score, never a chemical fact. For `RegistrationUse → Crop/Target`, evidence must preserve whether the official source asserted that **pair**, not merely mentioned both in the same record. A field-level CAS assertion needs the source field and original string even after syntax and checksum checks.

## Coverage gates to propose, not to enact now

Publishable official `RegistrationUse` and their core participant edges: 100% valid source snapshot + record locator or documented exception. Curated exact chemical alignments: 100% evidence and reviewer/approved rule version. Critical regulatory fields: 100% original text and source record; parsed value may be null if ambiguous. Record counts and coverage must be measured per jurisdiction after a replacement archive passes integrity tests. No source-license decision is inferred from this document.
