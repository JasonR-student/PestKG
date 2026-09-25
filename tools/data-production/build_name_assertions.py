"""Build source-backed A7 name assertions from the immutable A6 manifest."""
import json,hashlib,os
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import pyarrow as pa,pyarrow.parquet as pq
B=Path(__file__).resolve().parents[2]
manifest=json.loads((B/'dataset/normalized/A6_NORMALIZED_MANIFEST.json').read_text(encoding='utf-8'))
source_lookup={x['relative_path']:x for x in json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))['primary_source_files']}
out=B/'dataset/names';out.mkdir(parents=True,exist_ok=True)
path=out/'SOURCE_NAME_ASSERTIONS.parquet';meta=out/'A7_NAME_ASSERTIONS_MANIFEST.json'
schema=pa.schema([('snapshot_id',pa.string()),('source_file_sha256',pa.string()),('source_row_number',pa.int64()),('jurisdiction',pa.string()),('source',pa.string()),('source_field',pa.string()),('entity_concept',pa.string()),('name_type',pa.string()),('language',pa.string()),('original_value',pa.large_string()),('search_normalized',pa.large_string()),('assertion_status',pa.string())])
if path.exists() or meta.exists():
 if not path.exists() or not meta.exists():raise RuntimeError('Partial prior A7 final output')
 prior=json.loads(meta.read_text(encoding='utf-8'))
 if pq.ParquetFile(path).metadata.num_rows!=prior['assertion_count']:raise RuntimeError('A7 metadata mismatch')
 print('A7_SKIP_VERIFIED',prior['assertion_count']);raise SystemExit
work=out/('SOURCE_NAME_ASSERTIONS.'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.incomplete.parquet')
writer=pq.ParquetWriter(work,schema,compression='zstd',compression_level=6)
batch={k:[] for k in schema.names};counts=Counter();n=0
def flush():
 if batch['source_row_number']:
  writer.write_table(pa.Table.from_pydict(batch,schema=schema))
  for v in batch.values():v.clear()
try:
 for src in manifest['source_files']:
  p=B/src['relative_output_path']
  pf=pq.ParquetFile(p)
  for chunk in pf.iter_batches(columns=['source_row_number','derived_fields_json'],batch_size=10000):
   rows=chunk.column(0).to_pylist();dlist=chunk.column(1).to_pylist()
   for rownum,txt in zip(rows,dlist):
    d=json.loads(txt)
    for field,x in d.items():
     target=x.get('canonical_target','')
     if 'search_normalized' not in x:continue
     if not target.startswith(('LocalActiveIngredient.','PesticideProduct.','RegistrationUse.')):continue
     concept,attr=target.split('.',1)
     typ='translated_name' if attr=='translated_name' else 'trade_name' if attr=='trade_name' else 'original_name'
     if concept=='RegistrationUse':
      if attr.startswith('crop_'):concept='CropTerm'
      elif attr.startswith('target_'):concept='TargetTerm'
      elif attr.startswith('formulation_'):concept='FormulationTerm'
      else:continue
     v={'snapshot_id':manifest['snapshot_id'],'source_file_sha256':src['source_sha256'],'source_row_number':rownum,'jurisdiction':source_lookup[src['source_path']]['jurisdiction'], 'source':source_lookup[src['source_path']]['source'],'source_field':field,'entity_concept':concept,'name_type':typ,'language':'en' if typ=='translated_name' else 'und','original_value':x['original'],'search_normalized':x['search_normalized'],'assertion_status':'SOURCE_ATTESTED_UNRESOLVED_ENTITY'}
     for k,val in v.items():batch[k].append(val)
     counts[(concept,typ)]+=1;n+=1
     if len(batch['source_row_number'])>=20000:flush()
 flush()
finally:writer.close()
assert pq.ParquetFile(work).metadata.num_rows==n
os.replace(work,path)
h=hashlib.sha256()
with path.open('rb') as f:
 for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
summary={'snapshot_id':manifest['snapshot_id'],'pipeline_version':'a-line-name-processing-v1.0.0','source_a6_manifest':'dataset/normalized/A6_NORMALIZED_MANIFEST.json','assertion_count':n,'counts_by_concept_and_type':{f'{k[0]}.{k[1]}':v for k,v in sorted(counts.items())},'output_path':'dataset/names/SOURCE_NAME_ASSERTIONS.parquet','output_sha256':h.hexdigest(),'output_bytes':path.stat().st_size,'completed_at':datetime.now(timezone.utc).isoformat(),'policy':'No preferred or canonical name inferred; no entity merge; original and derived search name stored separately.'}
meta.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A7_DONE',n,dict(counts))
