"""Build safe A11 canonical metadata tables from A10 registry only."""
import csv,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
B=Path(__file__).resolve().parents[2]
INV=json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
with (B/'dataset/canonical_registry/ID_REGISTRY.csv').open(encoding='utf-8-sig',newline='') as f:R=list(csv.DictReader(f))
by={(r['entity_type'],r['natural_key']):r for r in R}
out=B/'dataset/canonical/partial_metadata';out.mkdir(parents=True,exist_ok=True)
files={}
def write(name,header,rows):
 p=out/name
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=header);w.writeheader();w.writerows(rows)
 files[name]={'rows':len(rows),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
items=INV['primary_source_files']
jur=[];seen=set()
for x in items:
 code=x['jurisdiction']
 if code in seen:continue
 seen.add(code);r=by[('Jurisdiction',code)]
 jur.append({'jurisdiction_id':r['canonical_id'],'jurisdiction_code':code,'entity_status':r['entity_status'],'raw_snapshot_id':INV['snapshot_id'],'schema_version':'v0.2'})
write('jurisdictions.csv',['jurisdiction_id','jurisdiction_code','entity_status','raw_snapshot_id','schema_version'],jur)
src=[];snaps=[]
for x in items:
 sid=by[('Source',x['source'])]['canonical_id'];jid=by[('Jurisdiction',x['jurisdiction'])]['canonical_id'];snap=by[('SourceSnapshot',x['source']+'|'+x['sha256'])]['canonical_id']
 src.append({'source_id':sid,'source_key':x['source'],'jurisdiction_id':jid,'source_type':'OFFICIAL_REGULATORY_SNAPSHOT','license_status':'UNKNOWN','schema_version':'v0.2'})
 snaps.append({'source_snapshot_id':snap,'source_id':sid,'raw_snapshot_id':INV['snapshot_id'],'source_path':x['relative_path'],'source_sha256':x['sha256'],'size_bytes':x['size_bytes'],'source_record_count':x['declared_release_rows'],'integrity_status':'PROJECT_SNAPSHOT_HASH_VERIFIED','schema_version':'v0.2'})
write('sources.csv',['source_id','source_key','jurisdiction_id','source_type','license_status','schema_version'],src)
write('source_snapshots.csv',['source_snapshot_id','source_id','raw_snapshot_id','source_path','source_sha256','size_bytes','source_record_count','integrity_status','schema_version'],snaps)
ids={x['jurisdiction_id'] for x in jur};sids={x['source_id'] for x in src};assert len(ids)==len(sids)==len({x['source_snapshot_id'] for x in snaps})==12
assert all(x['jurisdiction_id'] in ids for x in src) and all(x['source_id'] in sids for x in snaps)
manifest={'snapshot_id':INV['snapshot_id'],'status':'PARTIAL_METADATA_ONLY','schema_version':'PESTKG_CANONICAL_DATA_MODEL_v0.2','registry_version':'1.0.0','tables':files,'row_count_total':36,'generated_at':datetime.now(timezone.utc).isoformat(),'limitations':'No product/registration/use/local ingredient/global chemical IDs or facts yet; DEC-001 and source grain/evidence review pending.'}
(out/'A11_PARTIAL_METADATA_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A11_PARTIAL_METADATA_DONE',manifest['row_count_total'],files)
