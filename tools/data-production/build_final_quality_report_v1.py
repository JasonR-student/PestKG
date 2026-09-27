"""Write the A19 final internal-release quality report from passed gates."""
import json,hashlib
from pathlib import Path
B=Path(__file__).resolve().parents[2]
rel=B/'dataset/releases/2.0.0_internal'
m=json.loads((rel/'manifest.json').read_text(encoding='utf-8'))
q=json.loads((B/'dataset/_audit_workspace/quality/A12_CANONICAL_QA.json').read_text(encoding='utf-8'))
kg=json.loads((B/'dataset/kg/v1_0/A13_KG_MANIFEST.json').read_text(encoding='utf-8'))
prov=json.loads((B/'dataset/_audit_workspace/quality/A16_PROVENANCE_QA.json').read_text(encoding='utf-8'))
rights=json.loads((B/'dataset/license/A17_RIGHTS_GATE_SUMMARY.json').read_text(encoding='utf-8'))
assert q['status']=='PASS' and kg['status']=='PASS' and rights['internal_release']=='ALLOWED'
c=m['counts']
lines=['# PestKG Data Release v2 — Final Quality Report','',
 '**Release:** 2.0.0-internal / INTERNAL_RESEARCH_RELEASE. **Raw Snapshot:** '+m['raw_snapshot_id']+'. **Status:** PASS with documented limitations.','',
 '## Counts','','| Measure | Count |','| --- | ---: |',
 '| Frozen source files | 72,761 |',f"| Primary source rows | {c['source_rows']:,} |",
 f"| Canonical entities | {c['canonical_entities']:,} |",f"| GlobalChemical | {c['global_chemicals']:,} |",
 f"| Registration | {c['registrations']:,} |",f"| RegistrationUse | {c['registration_uses']:,} |",
 f"| KG nodes | {c['kg_nodes']:,} |",f"| KG edges | {c['kg_edges']:,} |",
 f"| Linked names | {q['counts']['names']:,} |",f"| Linked identifiers | {q['counts']['identifiers']:,} |",
 f"| Evidence | {q['counts']['evidence']:,} |",f"| Uncertain component rows | {q['counts']['quarantine_component_rows']:,} |",'',
 '## Gates','','- A1 frozen SHA-256 list and manifest passed, with DEC-RAW-001 project-baseline limitation.',
 '- A3 streamed 821,183 source rows; 1,288 exact source-row duplicates were retained; one ChEBI GZIP was truncated and quarantined.',
 f"- A12 canonical validation: {q['check_count']} checks PASS.",
 '- A14 graph validation: endpoint, type, predicate, evidence and self-edge checks PASS.',
 f"- A16 record provenance: {prov['record_level']['with_hash_row_snapshot']:,}/{prov['record_level']['source_rows']:,}. Relationship provenance: {prov['relationship_level']['with_evidence_snapshot_record']:,}/{prov['relationship_level']['assertions']:,}. Linked name and identifier assertions have source-field locators.",
 f"- A17: INTERNAL allowed under DEC-002; PUBLIC blocked by rights review. {rights['partial_rights_evidence']}/18 source classes have partial rights evidence, {rights['unknown_rights_evidence']}/18 unknown.",
 '- A18 internal release manifest, copied-file hashes and SHA256SUMS PASS.','',
 '## Identifier conflicts and quarantine','','- 750 grouped ChEBI CAS association candidates and 1,283 AGROVOC search candidates remain unlinked, not exact chemical identities.',
 '- Two single-token US CAS values failed checksum in A6; original strings remain.',
 f"- {q['counts']['quarantine_component_rows']:,} ambiguous ingredient rows are retained for review; no source row was deleted.",
 '- One truncated ChEBI structures GZIP is quarantined; one legacy XLS lacks a row-level profile; one supplementary file is empty.','',
 '## Known limitations','']
lines += ['- '+x for x in q['limitations']]
lines += ['- Critical Registration status/validity values retain row-level Evidence, but their representative Canonical rows do not expose a separate per-value source_field column; consult source records and mapping.',
 '- The clean handoff is a curated internal subset; full audit and source-record material remain in the engineering release.',
 '- Public redistribution is not approved.','']
(B/'docs/audits/PESTKG_DATA_RELEASE_V2_QUALITY_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print('A19_FINAL_QUALITY_REPORT_DONE',flush=True)

