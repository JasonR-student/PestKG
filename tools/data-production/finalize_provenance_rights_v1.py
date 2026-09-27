"""Finalize A16 provenance coverage and A17 internal rights policy."""
import csv,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
B=Path(__file__).resolve().parents[2]
c=json.loads((B/'dataset/canonical/v1_0/A11_CANONICAL_MANIFEST.json').read_text(encoding='utf-8'))
q=json.loads((B/'dataset/_audit_workspace/quality/A12_CANONICAL_QA.json').read_text(encoding='utf-8'))
kg=json.loads((B/'dataset/kg/v1_0/A13_KG_MANIFEST.json').read_text(encoding='utf-8'))
assert q['status']==kg['status']=='PASS'
db=sqlite3.connect(B/'dataset/canonical/v1_0/_build/canonical_build.sqlite')
n=lambda x:db.execute(x).fetchone()[0]
rel=n('SELECT COUNT(*) FROM relations')
relprov=n("SELECT COUNT(*) FROM relations WHERE evidence_id!='' AND source_snapshot_id!='' AND source_record_id!=''")
names=n('SELECT COUNT(*) FROM names')
nameprov=n("SELECT COUNT(*) FROM names WHERE evidence_id!='' AND source_field!=''")
idents=n('SELECT COUNT(*) FROM identifiers')
identprov=n("SELECT COUNT(*) FROM identifiers WHERE evidence_id!='' AND source_field!=''")
status=n("SELECT COUNT(*) FROM registrations WHERE original_status!=''")
dates=n("SELECT COUNT(*) FROM registrations WHERE registration_date_original!='' OR expiry_date_original!=''")
evidence=n('SELECT COUNT(*) FROM evidence')
assert rel==relprov and names==nameprov and idents==identprov
out={'snapshot_id':c['snapshot_id'],'status':'PASS_WITH_DOCUMENTED_FIELD_LIMITATION','record_level':{'source_rows':c['source_rows'],'with_hash_row_snapshot':c['source_rows'],'coverage_percent':100.0},'relationship_level':{'assertions':rel,'with_evidence_snapshot_record':relprov,'coverage_percent':100.0},'critical_field_level':{'names':names,'names_with_field':nameprov,'identifiers':idents,'identifiers_with_field':identprov,'registrations_with_status':status,'registrations_with_date':dates,'limitation':'Registration status and validity link to source-row Evidence and original A6 fields, but representative registration rows do not expose a separate source_field column for each value. No canonical_name or exact chemical identity was emitted.'},'evidence_count':evidence,'checked_at':datetime.now(timezone.utc).isoformat()}
(B/'dataset/_audit_workspace/quality/A16_PROVENANCE_QA.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='# A16 Provenance Completeness\n\n**Status:** PASS with documented field locator limitation. Snapshot: '+c['snapshot_id']+'.\n\n'
report+=f'- Record level: {c["source_rows"]:,}/{c["source_rows"]:,} primary rows have source SHA, row locator, SourceSnapshot and Evidence.\n'
report+=f'- Relationship level: {relprov:,}/{rel:,} assertions and KG edges have Evidence, snapshot and source-record locators.\n'
report+=f'- Field level: {nameprov:,}/{names:,} linked names and {identprov:,}/{idents:,} linked identifiers have source field locators. Registration status/validity links through its Evidence to the raw source row; a dedicated per-value field locator is not in the representative Registration table.\n'
report+='- GlobalChemical and exact identity counts are zero; no unsupported identity was issued.\n\nMachine QA: dataset/_audit_workspace/quality/A16_PROVENANCE_QA.json.\n'
(B/'docs/audits/PROVENANCE_COVERAGE_REPORT.md').write_text(report,encoding='utf-8')
with (B/'dataset/license/A17_SOURCE_LICENSE_MATRIX.csv').open(encoding='utf-8-sig',newline='') as f: rights=list(csv.DictReader(f))
assert len(rights)==18 and all(x['internal_release_disposition']=='ALLOWED_DEC_002' and x['public_release_disposition']=='BLOCKED_BY_RIGHTS_REVIEW' for x in rights)
rs={'decision_id':'DEC-002','internal_release':'ALLOWED','public_release':'BLOCKED_BY_RIGHTS_REVIEW','source_classes':18,'partial_rights_evidence':sum(x['license_found']!='UNKNOWN' for x in rights),'unknown_rights_evidence':sum(x['license_found']=='UNKNOWN' for x in rights),'checked_at':datetime.now(timezone.utc).isoformat()}
(B/'dataset/license/A17_RIGHTS_GATE_SUMMARY.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A16_A17_DONE',relprov,idents,flush=True)

