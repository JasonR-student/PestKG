"""A17 evidence-only rights inventory; no legal conclusion or public release approval."""
import csv,json
from pathlib import Path
from datetime import datetime,timezone
B=Path(__file__).resolve().parents[2]
inv=json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
countries={x['site_id']:x for x in json.loads((B/'data/releases/2026.08.3_federated/countries.json').read_text(encoding='utf-8'))}
rows=[]
for x in inv['primary_source_files']:
 c=countries[x['source']]
 rows.append({'source_key':x['source'],'jurisdiction':x['jurisdiction'],'source_class':'OFFICIAL_REGULATORY_SNAPSHOT','source_path':x['relative_path'],'source_sha256':x['sha256'],'official_url':c.get('official_url') or 'UNKNOWN','terms_url':'UNKNOWN','license_found':'UNKNOWN','license_text_location':'UNKNOWN','redistribution_right':'UNKNOWN','commercial_use_right':'UNKNOWN','release_disposition':'RESTRICTED_UNTIL_REVIEW','basis':'Source matrix v0.1 and release downloads exclusion; source-specific terms not verified','reviewed_at':'NOT_REVIEWED'})
for name in ['BCPC','ChEBI','AGROVOC','FRAC','HRAC','IRAC']:
 rows.append({'source_key':name,'jurisdiction':'CROSS_JURISDICTION','source_class':'EXTERNAL_REFERENCE','source_path':'NOT_ASSERTED_IN_THIS_MATRIX','source_sha256':'','official_url':'UNKNOWN','terms_url':'UNKNOWN','license_found':'UNKNOWN','license_text_location':'UNKNOWN','redistribution_right':'UNKNOWN','commercial_use_right':'UNKNOWN','release_disposition':'RESTRICTED_UNTIL_REVIEW','basis':'Explicitly excluded pending license audit in downloads/index.json','reviewed_at':'NOT_REVIEWED'})
out=B/'dataset/license';out.mkdir(parents=True,exist_ok=True);p=out/'A17_SOURCE_LICENSE_MATRIX.csv'
with p.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
assert len(rows)==18 and all(r['release_disposition']=='RESTRICTED_UNTIL_REVIEW' for r in rows)
report=f'''# A17 License and Distribution Gate\n\n**Snapshot:** {inv['snapshot_id']}. **Status:** INVENTORY_DONE / PUBLIC_DISTRIBUTION_RESTRICTED_UNTIL_REVIEW.\n\nThe source rights matrix contains **12** official regulatory snapshots and **6** external reference resources. Source-specific terms URL, license text, redistribution and commercial-use rights are **UNKNOWN** for all 18 based on repository evidence. `data/releases/2026.08.3_federated/downloads/index.json` already excludes raw snapshots and BCPC/ChEBI/AGROVOC/FRAC/HRAC/IRAC pending audit. The project-level CC BY notice for project-derived data does not establish third-party raw/source redistribution permission. This inventory makes no legal conclusion about any source's actual rights.\n\nMachine matrix: `dataset/license/A17_SOURCE_LICENSE_MATRIX.csv`. Public Release v2 is restricted pending source-specific terms evidence and human scope decision. An INTERNAL release may be prepared after data quality and canonical/KG gates pass, provided it does not imply public redistribution approval. Full release is currently also blocked by incomplete A11/A13, independently of rights.\n'''
(B/'docs/audits/A17_LICENSE_DISTRIBUTION_GATE.md').write_text(report,encoding='utf-8')
print('A17_MATRIX_DONE',len(rows))
