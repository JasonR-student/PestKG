"""A8 source-backed external identifier assertions; no chemical identity joins."""
import csv,gzip,json,re,hashlib,os
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import pyarrow as pa,pyarrow.parquet as pq
B=Path(__file__).resolve().parents[2]
INV=json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
ROOT=Path(INV['root_path']);SNAP=INV['snapshot_id']
IDX={r['relative_path']:r for r in csv.DictReader((B/'dataset/_audit_workspace/profiles/supplementary/SUPPLEMENTARY_PROFILE_INDEX.csv').open(encoding='utf-8-sig',newline=''))}
OUT=B/'dataset/identifiers';OUT.mkdir(parents=True,exist_ok=True)
DEST=OUT/'SOURCE_EXTERNAL_IDENTIFIERS.parquet'; META=OUT/'A8_IDENTIFIER_MANIFEST.json'
BASE='data/01_raw_sources/外部参考数据/ChEBI/official_raw_release_2026-08-14/'
SCHEMA=pa.schema([('snapshot_id',pa.string()),('source_path',pa.string()),('source_file_sha256',pa.string()),('source_row_number',pa.int64()),('source_field',pa.string()),('subject_scope',pa.string()),('source_subject_key',pa.string()),('scheme',pa.string()),('original_value',pa.large_string()),('normalized_value',pa.large_string()),('validation_status',pa.string()),('source_status',pa.string()),('token_ordinal',pa.int32())])
CAS=re.compile(r'^(\d{2,7})-(\d{2})-(\d)$')
def cas(value):
 m=CAS.fullmatch(value.strip())
 if not m:return None,'NOT_CAS_SYNTAX'
 body=m.group(1)+m.group(2);check=sum((i+1)*int(c) for i,c in enumerate(reversed(body)))%10
 return ('-'.join(m.groups()),'CHECKSUM_VALID') if check==int(m.group(3)) else (None,'CHECKSUM_INVALID')
if DEST.exists() or META.exists():
 if not DEST.exists() or not META.exists():raise RuntimeError('Partial final A8 output')
 m=json.loads(META.read_text(encoding='utf-8'))
 if pq.ParquetFile(DEST).metadata.num_rows!=m['assertion_count']:raise RuntimeError('A8 prior metadata mismatch')
 print('A8_SKIP_VERIFIED',m['assertion_count']);raise SystemExit
working=OUT/('SOURCE_EXTERNAL_IDENTIFIERS.'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.incomplete.parquet')
w=pq.ParquetWriter(working,SCHEMA,compression='zstd',compression_level=6);batch={k:[] for k in SCHEMA.names};counts=Counter();n=0
sources={}
for rel in ['compounds.tsv.gz','database_accession.tsv.gz','secondary_ids.tsv.gz','source.tsv.gz']:
 key=BASE+rel
 if key not in IDX or IDX[key]['status']!='DONE':raise RuntimeError('A8 missing valid source '+key)
 sources[rel]=IDX[key]
def emit(source_path,sha,rownum,field,scope,key,scheme,original,normalized,status,source_status='',ordinal=1):
 global n
 if original is None or str(original).strip()=='':return
 vals={'snapshot_id':SNAP,'source_path':source_path,'source_file_sha256':sha,'source_row_number':rownum,'source_field':field,'subject_scope':scope,'source_subject_key':key,'scheme':scheme,'original_value':str(original),'normalized_value':normalized,'validation_status':status,'source_status':source_status,'token_ordinal':ordinal}
 for k,v in vals.items():batch[k].append(v)
 counts[(scope,scheme,status)]+=1;n+=1
 if len(batch['source_row_number'])>=20000:flush()
def flush():
 if batch['source_row_number']:
  w.write_table(pa.Table.from_pydict(batch,schema=SCHEMA))
  for v in batch.values():v.clear()
try:
 # US local source row CAS: split only the observed source delimiter, never infer ingredient-token alignment.
 us=next(x for x in INV['primary_source_files'] if x['jurisdiction']=='US')
 a6=json.loads((B/'dataset/normalized/A6_NORMALIZED_MANIFEST.json').read_text(encoding='utf-8'))
 usnorm=next(x for x in a6['source_files'] if x['source_path']==us['relative_path'])
 for chunk in pq.ParquetFile(B/usnorm['relative_output_path']).iter_batches(columns=['source_row_number','raw_fields_json'],batch_size=10000):
  for rownum,raw in zip(chunk.column(0).to_pylist(),chunk.column(1).to_pylist()):
   text=json.loads(raw).get('ActiveIngredientCASNumber') or ''
   if not text.strip():continue
   for i,token in enumerate(text.split('|'),1):
    token=token.strip();norm,status=cas(token)
    emit(us['relative_path'],us['sha256'],rownum,'ActiveIngredientCASNumber','LOCAL_SOURCE_ROW',str(rownum),'CAS_RN',token,norm,status,'UNLINKED_TO_LOCAL_INGREDIENT',i)
 # Official ChEBI compound primary identifier and lookup for linked accession rows.
 compound={}; rel=BASE+'compounds.tsv.gz';sha=sources['compounds.tsv.gz']['sha256']
 with gzip.open(ROOT/rel,'rt',encoding='utf-8',newline='') as f:
  for i,x in enumerate(csv.DictReader(f,delimiter='\t'),1):
   accession=x['chebi_accession'];compound[x['id']]=accession
   status='CHEBI_SYNTAX_VALID' if re.fullmatch(r'CHEBI:\d+',accession or '') else 'CHEBI_SYNTAX_OTHER'
   emit(rel,sha,i,'chebi_accession','REFERENCE_CHEBI_COMPOUND',x['id'],'CHEBI',accession,accession if status=='CHEBI_SYNTAX_VALID' else None,status,x['status_id'])
 # Official ChEBI secondary identifiers.
 rel=BASE+'secondary_ids.tsv.gz';sha=sources['secondary_ids.tsv.gz']['sha256']
 with gzip.open(ROOT/rel,'rt',encoding='utf-8',newline='') as f:
  for i,x in enumerate(csv.DictReader(f,delimiter='\t'),1):
   v=x['secondary_id'];key=compound.get(x['compound_id'],'')
   status='CHEBI_SECONDARY_NUMERIC' if v.isdigit() and key else 'UNRESOLVED_SOURCE_KEY_OR_SYNTAX'
   emit(rel,sha,i,'secondary_id','REFERENCE_CHEBI_COMPOUND',key or x['compound_id'],'CHEBI_SECONDARY',v,'CHEBI:'+v if status=='CHEBI_SECONDARY_NUMERIC' else None,status)
 # ChEBI accession types are taken from its own type column; citations are evidence, not external chemical identifiers.
 with gzip.open(ROOT/(BASE+'source.tsv.gz'),'rt',encoding='utf-8',newline='') as f:source_map={x['id']:x for x in csv.DictReader(f,delimiter='\t')}
 rel=BASE+'database_accession.tsv.gz';sha=sources['database_accession.tsv.gz']['sha256']
 with gzip.open(ROOT/rel,'rt',encoding='utf-8',newline='') as f:
  for i,x in enumerate(csv.DictReader(f,delimiter='\t'),1):
   typ=x['type'];v=x['accession_number'];subject=compound.get(x['compound_id'],'')
   if typ=='CITATION':continue
   if typ=='CAS':scheme='CAS_RN';norm,status=cas(v)
   elif typ in ('MANUAL_X_REF','REGISTRY_NUMBER'):
    prefix=source_map.get(x['source_id'],{}).get('prefix') or 'source_id_'+x['source_id']
    scheme=('XREF:' if typ=='MANUAL_X_REF' else 'REGISTRY:')+prefix
    norm=v.strip() if v.strip() else None;status='SOURCE_DECLARED'
   else:continue
   if not subject:status='UNRESOLVED_CHEBI_SUBJECT'
   emit(rel,sha,i,'accession_number','REFERENCE_CHEBI_COMPOUND',subject or x['compound_id'],scheme,v,norm,status,x['status_id'])
 # Candidate structure descriptors are reference metadata, not confirmed local identity mappings.
 rel='data/01_raw_sources/外部参考数据/ChEBI/unresolved_all_candidates/candidate_entity_details/02_candidate_chebi_entities_complete.csv';sha=IDX[rel]['sha256']
 with (ROOT/rel).open('r',encoding='utf-8-sig',newline='') as f:
  for i,x in enumerate(csv.DictReader(f),1):
   subject=x['ChEBI_ID']
   for field,scheme in [('InChI','INCHI'),('InChIKey','INCHIKEY'),('SMILES','SMILES')]:
    v=x.get(field) or ''
    if v.strip():emit(rel,sha,i,field,'CANDIDATE_CHEBI_REFERENCE',subject,scheme,v,v.strip(),'SOURCE_DECLARED_UNVERIFIED_STRUCTURE','CANDIDATE_REFERENCE')
 flush()
finally:w.close()
assert pq.ParquetFile(working).metadata.num_rows==n
os.replace(working,DEST)
h=hashlib.sha256()
with DEST.open('rb') as f:
 for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
meta={'snapshot_id':SNAP,'pipeline_version':'a-line-external-identifiers-v1.0.0','assertion_count':n,'counts_by_scope_scheme_status':{'|'.join(k):v for k,v in sorted(counts.items())},'output_path':'dataset/identifiers/SOURCE_EXTERNAL_IDENTIFIERS.parquet','output_sha256':h.hexdigest(),'output_size_bytes':DEST.stat().st_size,'completed_at':datetime.now(timezone.utc).isoformat(),'policy':'No source identifier is a PestKG canonical ID. CAS checksum and source-declared accessions do not verify chemical identity; local-to-ChEBI joins are not inferred.'}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A8_ASSERTIONS_DONE',n,DEST.stat().st_size,flush=True)
