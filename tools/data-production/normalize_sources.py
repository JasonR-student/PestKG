"""A6 deterministic, lossless source-row normalization, v1."""
from __future__ import annotations
import argparse,csv,json,re,unicodedata,hashlib,os
from datetime import datetime,timezone
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

B=Path(__file__).resolve().parents[2]
INV=json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
ROOT=Path(INV['root_path'])
OUT=B/'dataset/normalized/v1_2';OUT.mkdir(parents=True,exist_ok=True)
VERSION='a-line-normalization-v1.2.0'
DATE_FIELDS={'Registration.first_registration_date_original','Registration.expiry_date_original'}
NAME_FIELDS={'LocalActiveIngredient.original_name','LocalActiveIngredient.translated_name','PesticideProduct.original_name','PesticideProduct.trade_name','RegistrationUse.crop_original','RegistrationUse.target_original','RegistrationUse.formulation_original'}
CAS=re.compile(r'^\s*(\d{2,7})-(\d{2})-(\d)\s*$')
def cas_check(value):
 m=CAS.fullmatch(value)
 if not m:return {'original':value,'normalized':None,'parse_status':'NOT_SINGLE_CAS_SYNTAX'}
 digits=m.group(1)+m.group(2)
 chk=sum((i+1)*int(c) for i,c in enumerate(reversed(digits)))%10
 return {'original':value,'normalized':'-'.join(m.groups()) if chk==int(m.group(3)) else None,'parse_status':'CHECKSUM_VALID' if chk==int(m.group(3)) else 'CHECKSUM_INVALID'}
def date_check(value,jurisdiction):
 x=value.strip()
 if x.lower()=='n.v.t.':return {'original':value,'parsed_date':None,'precision':None,'source_locale':jurisdiction,'parse_status':'NOT_APPLICABLE_SOURCE_TOKEN'}
 if x.replace(' ','')=='--':return {'original':value,'parsed_date':None,'precision':None,'source_locale':jurisdiction,'parse_status':'MISSING_SOURCE_TOKEN'}
 # Source-locale rules are explicit; raw text remains attached in every result.
 if jurisdiction=='TW':
  m=re.fullmatch(r'(\d{2,3})[-/](\d{1,2})[-/](\d{1,2})',x)
  if not m:m=re.fullmatch(r'(\d{3})(\d{2})(\d{2})',x)
  if not m:m=re.fullmatch(r'(\d{2})(\d{2})(\d{2})',x)
  if m:
   try:
    d=datetime(int(m.group(1))+1911,int(m.group(2)),int(m.group(3)))
    return {'original':value,'parsed_date':d.strftime('%Y-%m-%d'),'precision':'DAY','source_locale':'TW_ROC_YEAR','parse_status':'PARSED_SOURCE_LOCALE'}
   except ValueError:return {'original':value,'parsed_date':None,'precision':None,'source_locale':'TW_ROC_YEAR','parse_status':'INVALID_DATE'}
 if jurisdiction in ('CN','JP'):
  m=re.fullmatch(r'(\d{4})/(\d{1,2})/(\d{1,2})',x)
  if m:
   try:
    d=datetime(*map(int,m.groups()))
    return {'original':value,'parsed_date':d.strftime('%Y-%m-%d'),'precision':'DAY','source_locale':jurisdiction+'_YMD','parse_status':'PARSED_SOURCE_LOCALE'}
   except ValueError:return {'original':value,'parsed_date':None,'precision':None,'source_locale':jurisdiction+'_YMD','parse_status':'INVALID_DATE'}
 if jurisdiction in ('GB','GB-NI','NZ','NL','US'):
  sep='-' if jurisdiction=='NL' else '/'
  m=re.fullmatch(r'(\d{1,2})'+re.escape(sep)+r'(\d{1,2})'+re.escape(sep)+r'(\d{4})',x)
  if m:
   a,b,y=map(int,m.groups())
   if y==9999:return {'original':value,'parsed_date':None,'precision':None,'source_locale':jurisdiction,'parse_status':'SENTINEL_YEAR'}
   day,month=(b,a) if jurisdiction=='US' else (a,b)
   try:
    d=datetime(y,month,day)
    return {'original':value,'parsed_date':d.strftime('%Y-%m-%d'),'precision':'DAY','source_locale':jurisdiction+('_MDY' if jurisdiction=='US' else '_DMY'),'parse_status':'PARSED_SOURCE_LOCALE'}
   except ValueError:return {'original':value,'parsed_date':None,'precision':None,'source_locale':jurisdiction,'parse_status':'INVALID_DATE'}
 for pattern,fmt,precision in [(r'\d{4}-\d{2}-\d{2}','%Y-%m-%d','DAY'),(r'\d{4}/\d{2}/\d{2}','%Y/%m/%d','DAY'),(r'\d{8}','%Y%m%d','DAY'),(r'\d{4}-\d{2}','%Y-%m','MONTH'),(r'\d{4}','%Y','YEAR')]:
  if re.fullmatch(pattern,x):
   try:
    d=datetime.strptime(x,fmt)
    return {'original':value,'parsed_date':d.strftime('%Y-%m-%d') if precision=='DAY' else None,'precision':precision,'source_locale':'ISO_OR_YEAR_FIRST','parse_status':'PARSED' if precision=='DAY' else 'PARTIAL_PRECISION'}
   except ValueError:return {'original':value,'parsed_date':None,'precision':None,'source_locale':'ISO_OR_YEAR_FIRST','parse_status':'INVALID_DATE'}
 return {'original':value,'parsed_date':None,'precision':None,'source_locale':'UNKNOWN','parse_status':'UNRESOLVED_LOCALE_OR_FORMAT'}
def name_check(value):
 n=unicodedata.normalize('NFKC',value)
 n=' '.join(n.split())
 return {'original':value,'search_normalized':n.casefold(),'normalization':'NFKC_WHITESPACE_CASEFOLD'}
def build_mappings():
 out={}
 with (B/'dataset/mappings/source_field_mapping.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   if r['source'].startswith('supplementary::'):continue
   if r['canonical_entity']=='SourceFieldAssertion':continue
   out.setdefault(r['source_table'],{})[r['source_field']]=r['canonical_entity']+'.'+r['canonical_field']
 return out
MAPPING=build_mappings()
SCHEMA=pa.schema([('snapshot_id',pa.string()),('source_file_sha256',pa.string()),('source_row_number',pa.int64()),('jurisdiction',pa.string()),('source',pa.string()),('raw_fields_json',pa.large_string()),('derived_fields_json',pa.large_string())])
def run_item(item):
 relative=item['relative_path']; key=f"{item['jurisdiction']}_{item['source']}"; dest=OUT/(key+'.parquet'); meta=OUT/(key+'.meta.json')
 p=json.loads((B/'dataset/_audit_workspace/profiles'/f'{key}.json').read_text(encoding='utf-8'))
 if p['source_sha256']!=item['sha256']:raise RuntimeError('Profile hash mismatch '+key)
 if dest.exists() or meta.exists():
  if not dest.exists() or not meta.exists():raise RuntimeError('Incomplete final output: '+key)
  old=json.loads(meta.read_text(encoding='utf-8'))
  if old['source_sha256']!=item['sha256'] or old['row_count']!=p['row_count'] or old['pipeline_version']!=VERSION or pq.ParquetFile(dest).metadata.num_rows!=p['row_count']:
   raise RuntimeError('Existing output requires separate investigation: '+key)
  print('A6_SKIP_VERIFIED',key,p['row_count'],flush=True);return
 working=OUT/(key+'.'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.incomplete.parquet')
 writer=pq.ParquetWriter(working,SCHEMA,compression='zstd',compression_level=6)
 count=0; parse_counts={};batch={x:[] for x in SCHEMA.names}
 def flush():
  if batch['source_row_number']:
   writer.write_table(pa.Table.from_pydict(batch,schema=SCHEMA))
   for v in batch.values():v.clear()
 try:
  with (ROOT/relative).open('r',encoding='utf-8-sig',newline='') as f:
   reader=csv.DictReader(f)
   if reader.fieldnames!=p['header']:raise RuntimeError('Header mismatch '+key)
   fields=MAPPING.get(relative,{})
   for row in reader:
    count+=1
    if None in row:raise RuntimeError(f'Row width mismatch {key}:{count}')
    derived={}
    for field,target in fields.items():
     value=row.get(field) or ''
     if not value.strip():continue
     if target in NAME_FIELDS:derived[field]={'canonical_target':target,**name_check(value)}
     elif target in DATE_FIELDS:
      x=date_check(value,item['jurisdiction']);derived[field]={'canonical_target':target,**x};parse_counts[x['parse_status']]=parse_counts.get(x['parse_status'],0)+1
     elif target=='ExternalIdentifier.CAS_original_value':
      x=cas_check(value);derived[field]={'canonical_target':target,**x};parse_counts[x['parse_status']]=parse_counts.get(x['parse_status'],0)+1
    values={'snapshot_id':INV['snapshot_id'],'source_file_sha256':item['sha256'],'source_row_number':count,'jurisdiction':item['jurisdiction'],'source':item['source'],'raw_fields_json':json.dumps(row,ensure_ascii=False,separators=(',',':')),'derived_fields_json':json.dumps(derived,ensure_ascii=False,separators=(',',':'))}
    for k,v in values.items():batch[k].append(v)
    if count%10000==0:flush()
  flush()
 finally:writer.close()
 if count!=p['row_count'] or pq.ParquetFile(working).metadata.num_rows!=count:raise RuntimeError(f'Output count mismatch {key}: {count} != {p["row_count"]}; incomplete file retained')
 os.replace(working,dest)
 metadata={'snapshot_id':INV['snapshot_id'],'source_path':relative,'source_sha256':item['sha256'],'row_count':count,'pipeline_version':VERSION,'parquet_file':dest.name,'parquet_size_bytes':dest.stat().st_size,'parse_status_counts':parse_counts,'completed_at':datetime.now(timezone.utc).isoformat()}
 meta.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('A6_DONE',key,count,dest.stat().st_size,flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--jurisdiction',default='ALL');a=ap.parse_args()
 for item in INV['primary_source_files']:
  if a.jurisdiction!='ALL' and item['jurisdiction']!=a.jurisdiction:continue
  run_item(item)
if __name__=='__main__':main()
