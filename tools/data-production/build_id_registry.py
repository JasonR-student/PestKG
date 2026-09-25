"""A10 append-only opaque ID registry for objectively keyed metadata entities."""
import csv,json,uuid,hashlib,os
from pathlib import Path
from datetime import datetime,timezone
B=Path(__file__).resolve().parents[2]
inv=json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
out=B/'dataset/canonical_registry';out.mkdir(parents=True,exist_ok=True)
p=out/'ID_REGISTRY.csv';meta=out/'REGISTRY_METADATA.json'
cols=['canonical_id','entity_type','entity_status','created_at','superseded_by','merged_into','decision_id','schema_version','registry_version','natural_key','source_file_sha256','source_snapshot_id']
rows=[]
if p.exists():
 with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 if any(list(r)!=cols for r in rows):raise RuntimeError('Existing registry schema mismatch')
seen={(r['entity_type'],r['natural_key']):r for r in rows};ids={r['canonical_id'] for r in rows}
if len(ids)!=len(rows) or len(seen)!=len(rows):raise RuntimeError('Registry ID/key collision')
new=0;now=datetime.now(timezone.utc).isoformat()
def add(typ,key,prefix,sha='',snapshot=''):
 global new
 k=(typ,key)
 if k in seen:
  r=seen[k]
  if sha and r['source_file_sha256']!=sha:raise RuntimeError('Source hash changed for key '+key)
  return r['canonical_id']
 cid=prefix+'_'+uuid.uuid4().hex
 if cid in ids:raise RuntimeError('UUID collision')
 r={'canonical_id':cid,'entity_type':typ,'entity_status':'active','created_at':now,'superseded_by':'','merged_into':'','decision_id':'','schema_version':'PESTKG_CANONICAL_DATA_MODEL_v0.2','registry_version':'1.0.0','natural_key':key,'source_file_sha256':sha,'source_snapshot_id':snapshot}
 rows.append(r);seen[k]=r;ids.add(cid);new+=1;return cid
for x in inv['primary_source_files']:
 jur=add('Jurisdiction',x['jurisdiction'],'JUR')
 source=add('Source',x['source'],'SRC')
 snap=add('SourceSnapshot',x['source']+'|'+x['sha256'],'SSNP',x['sha256'],inv['snapshot_id'])
if len(rows)!=36:raise RuntimeError(f'Unexpected metadata registry count {len(rows)}')
if new:
 work=p.with_suffix('.incomplete.csv')
 with work.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
 os.replace(work,p)
h=hashlib.sha256(p.read_bytes()).hexdigest()
meta.write_text(json.dumps({'registry_version':'1.0.0','schema_version':'PESTKG_CANONICAL_DATA_MODEL_v0.2','snapshot_id':inv['snapshot_id'],'row_count':len(rows),'entities_by_type':{t:sum(r['entity_type']==t for r in rows) for t in ['Jurisdiction','Source','SourceSnapshot']},'registry_sha256':h,'updated_at':now,'new_rows_this_run':new,'scope':'Metadata entities with explicit source codes/file SHA-256 only. No local ingredient, product, registration, use or global chemical ID allocated.'},indent=2)+'\n',encoding='utf-8')
print('A10_METADATA_REGISTRY_DONE',len(rows),'new',new,'sha256',h)
