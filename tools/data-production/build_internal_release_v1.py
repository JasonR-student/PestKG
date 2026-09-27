"""Create immutable A18 internal research release after A12/A14/A16 gates."""
import csv,hashlib,json,os,shutil,sqlite3
from datetime import datetime,timezone
from pathlib import Path
import pyarrow.parquet as pq
B=Path(__file__).resolve().parents[2]
CAN=B/'dataset/canonical/v1_0';KG=B/'dataset/kg/v1_0'
c=json.loads((CAN/'A11_CANONICAL_MANIFEST.json').read_text(encoding='utf-8'))
k=json.loads((KG/'A13_KG_MANIFEST.json').read_text(encoding='utf-8'))
q12=json.loads((B/'dataset/_audit_workspace/quality/A12_CANONICAL_QA.json').read_text(encoding='utf-8'))
q14=json.loads((B/'dataset/_audit_workspace/quality/A14_KG_QA.json').read_text(encoding='utf-8'))
q16=json.loads((B/'dataset/_audit_workspace/quality/A16_PROVENANCE_QA.json').read_text(encoding='utf-8'))
rights=json.loads((B/'dataset/license/A17_RIGHTS_GATE_SUMMARY.json').read_text(encoding='utf-8'))
assert q12['status']==q14['status']==k['status']=='PASS'
assert q16['status']=='PASS_WITH_DOCUMENTED_FIELD_LIMITATION'
assert rights['internal_release']=='ALLOWED' and rights['public_release']=='BLOCKED_BY_RIGHTS_REVIEW'
dest=B/'dataset/releases/2.0.0_internal'
work=B/'dataset/releases/2.0.0_internal.incomplete'
if dest.exists():raise RuntimeError('Final release already exists: no overwrite')
if work.exists():raise RuntimeError('Incomplete release exists: inspect before resuming')
work.mkdir(parents=True)
def h(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def info(p):
 rel=p.relative_to(work).as_posix()
 out={'path':rel,'size_bytes':p.stat().st_size,'sha256':h(p)}
 if p.suffix=='.parquet':out['row_count']=pq.ParquetFile(p).metadata.num_rows
 return out
copy=[]
for name in c['tables']:
 copy.append((CAN/(name+'.parquet'),work/'canonical'/(name+'.parquet')))
copy.extend([
 (KG/'nodes.parquet',work/'kg/nodes.parquet'),
 (KG/'edges.parquet',work/'kg/edges.parquet'),
 (B/'dataset/canonical_registry/ID_REGISTRY.csv',work/'metadata/ID_REGISTRY.csv'),
 (B/'dataset/raw_manifest/RAW_INPUT_MANIFEST.json',work/'metadata/RAW_INPUT_MANIFEST.json'),
 (B/'docs/design/PESTKG_CANONICAL_DATA_MODEL_v0.2.md',work/'schema/PESTKG_CANONICAL_DATA_MODEL_v0.2.md'),
 (B/'docs/design/PESTKG_KG_SCHEMA_v0.2.md',work/'schema/PESTKG_KG_SCHEMA_v0.2.md'),
 (B/'dataset/_audit_workspace/quality/A12_CANONICAL_QA.json',work/'quality/A12_CANONICAL_QA.json'),
 (B/'dataset/_audit_workspace/quality/A14_KG_QA.json',work/'quality/A14_KG_QA.json'),
 (B/'dataset/_audit_workspace/quality/A16_PROVENANCE_QA.json',work/'quality/A16_PROVENANCE_QA.json'),
 (B/'dataset/license/A17_SOURCE_LICENSE_MATRIX.csv',work/'quality/A17_SOURCE_LICENSE_MATRIX.csv')])
for i,(src,p) in enumerate(copy,1):
 p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,p)
 if h(src)!=h(p):raise RuntimeError('Copy hash mismatch '+src.name)
 print('A18_COPY',i,len(copy),src.name,flush=True)
(work/'VERSION').write_text('2.0.0-internal\n',encoding='utf-8')
(work/'README.md').write_text('# PestKG A-Line Internal Research Release v2\n\nRaw Snapshot: PESTKG_RAW_SNAPSHOT_2026-09-23. Type: INTERNAL_RESEARCH_RELEASE. Public distribution: BLOCKED_BY_RIGHTS_REVIEW (DEC-002).\n\ncanonical contains complete source-backed tables and original source rows; kg contains graph nodes and edges; metadata contains registry and snapshot manifests; schema contains approved v0.2 models; quality contains machine gates and rights matrix. No GlobalChemical or exact identity was invented. Ambiguous ingredient rows remain in the engineering quarantine ledger.\n',encoding='utf-8')
files=[info(p) for p in sorted(work.rglob('*')) if p.is_file()]
counts=q12['counts']
inv=json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
db=sqlite3.connect(CAN/'_build/canonical_build.sqlite')
source_versions=[]
for item in inv['primary_source_files']:
 row=db.execute("SELECT canonical_id FROM registry WHERE entity_type='SourceSnapshot' AND natural_key=?",(item['source']+'|'+item['sha256'],)).fetchone()
 if not row:raise RuntimeError('Missing source snapshot registry ID')
 source_versions.append({'source_key':item['source'],'jurisdiction':item['jurisdiction'],'source_snapshot_id':row[0],'source_sha256':item['sha256']})
db.close()
stamp=datetime.now(timezone.utc).isoformat()
m={'release_name':'PestKG A-Line Internal Research Release v2','release_version':'2.0.0-internal','release_type':'INTERNAL_RESEARCH_RELEASE','raw_snapshot_id':c['snapshot_id'],'raw_snapshot_manifest_sha256':h(B/'dataset/raw_manifest/RAW_INPUT_MANIFEST.json'),'archive_sha256':None,'archive_sha256_reason':'Active Raw Input is an approved directory snapshot, not a verified replacement archive.','schema_version':c['schema_version'],'kg_schema_version':k['schema_version'],'pipeline_version':c['pipeline_version']+' + '+k['pipeline_version'],'canonical_registry_version':c['canonical_registry_version'],'created_at':stamp,'release_timestamp':stamp,'data_version':'2.0.0-internal','source_snapshot_versions':source_versions,'files':files,'counts':{'source_rows':c['source_rows'],'canonical_entities':counts['canonical_entities'],'global_chemicals':counts['entity_types'].get('GlobalChemical',0),'registrations':counts['registrations'],'registration_uses':counts['registration_uses'],'kg_nodes':k['node_count'],'kg_edges':k['edge_count']},'known_limitations':q12['limitations'],'distribution_status':{'internal':'ALLOWED_DEC_002','public':'BLOCKED_BY_RIGHTS_REVIEW'}}
(work/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (work/'SHA256SUMS').open('w',encoding='utf-8') as f:
 for x in files+[info(work/'manifest.json')]:f.write(x['sha256']+'  '+x['path']+'\n')
for x in files:
 p=work/x['path'];assert h(p)==x['sha256']
 if 'row_count' in x:assert pq.ParquetFile(p).metadata.num_rows==x['row_count']
for line in (work/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
 sha,rel=line.split('  ',1);assert h(work/rel)==sha
os.replace(work,dest)
print('A18_INTERNAL_RELEASE_DONE',len(files)+2,flush=True)

