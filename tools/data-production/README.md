# PestKG A-Line Data Production Pipeline

**Input baseline:** PESTKG_RAW_SNAPSHOT_2026-09-23. **Internal release:** dataset/releases/2.0.0_internal. **Clean handoff:** delivery/PestKG_A_Data_Release_v1.0. **Status:** A1–A20 DONE for INTERNAL_RESEARCH_RELEASE. Public distribution remains BLOCKED_BY_RIGHTS_REVIEW.

## Completed stages and scripts

- A1 raw freeze: resume_raw_snapshot.py / freeze_raw_snapshot.py. Completed 72,761 hashes; never rerun without an integrity trigger.
- A2 inventory: inventory_snapshot.py. Completed.
- A3 profiling: profile_sources.py, profile_supplementary.py, profile_json_collections.py, summarize_profiles.py. Completed.
- A4/A5 field map: map_source_fields.py and extend_supplementary_mapping.py. Completed.
- A6 normalized source rows: normalize_sources.py; active A6_NORMALIZED_MANIFEST.json selects validated v1.1/v1.2 outputs.
- A7 names: build_name_assertions.py. A preserved interrupted attempt is not an accepted output.
- A8 external identifiers: build_identifier_assertions.py and audit_identifier_candidates.py.
- A9/A9b lexical candidates/rules: cluster_ingredient_terms.py and apply_identity_rules.py; no automatic chemical merge.
- A10/A11: build_canonical_dataset_v1.py. DEC-001 conservative structured-component policy; original combinations, raw fields and uncertain rows are preserved. Persistent UUID4 registry and all Canonical tables are emitted.
- A12–A15: validate_and_build_kg_v1.py. Canonical QA, v0.2 Full Research KG, KG QA and display projection metadata.
- A16/A17: finalize_provenance_rights_v1.py. Provenance coverage and DEC-002 internal-only rights scope.
- A18: build_internal_release_v1.py. Immutable internal engineering package; refuses to overwrite an existing final package.
- A19: build_final_quality_report_v1.py. Full technical report.
- A20: build_clean_handoff_v1.py and verify_clean_handoff_v1.py. Seven-Parquet clean handoff and independent final verification.
- Cross-stage completed-artifact checker: verify_pipeline_artifacts.py. It does not rehash raw input.

## Replay contract

Read A_LINE_TASK_STATE.md, A_LINE_CHANGELOG.md, A_LINE_DECISION_QUEUE.md and A_LINE_HUMAN_DECISIONS.md before new work. The release scripts refuse to overwrite immutable final directories; use a new reviewed version and output location for a changed input/schema/decision set. Registry IDs persist in dataset/canonical_registry/ID_REGISTRY.csv and the internal SQLite build workspace. A re-run with the same registry preserves IDs; label matching alone never merges chemical entities.

The current A-Line scope is complete. Do not rerun A1 hashing, A2 inventory, A3 full profiling, A6 normalization or other verified expensive stages without a concrete defect or changed input. Keep raw data, failed archive, partial files and audit workspace untouched. No commit or push was made.
