"""Build conservative source-backed canonical entities and assertions from A6.

DEC-001: structured constituent rows are used only after name-set agreement.
The registry issues UUID4 identifiers and persists the source-scoped lookup keys.
No name-only chemical merge or GlobalChemical identity is inferred.
"""
from __future__ import annotations
import csv, hashlib, json, os, sqlite3, sys, unicodedata, uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

B=Path(__file__).resolve().parents[2]
A6=json.loads((B/'dataset/normalized/A6_NORMALIZED_MANIFEST.json').read_text(encoding='utf-8'))
INV=json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
OUT=B/'dataset/canonical/v1_0'
REG=B/'dataset/canonical_registry'
WORK=OUT/'_build'
OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
PIPELINE='a-line-canonical-v1.0.0'
SCHEMA='PESTKG_CANONICAL_DATA_MODEL_v0.2'
REGISTRY_VERSION='1.0.0'
NOW=datetime.now(timezone.utc).isoformat()
def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def norm(s):return ' '.join(unicodedata.normalize('NFKC',str(s)).casefold().split())
def key(*parts):return json.dumps(parts,ensure_ascii=False,separators=(',',':'))
def useful(v):return v is not None and str(v).strip() not in ('','-','--','/','N/A','n/a','null','NULL')
def get(row,fields):
 for f in fields:
  if useful(row.get(f)):return str(row[f]).strip(),f
 return '', ''
def fieldmap():
 d={}
 with (B/'dataset/mappings/source_field_mapping.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   if r['source'].startswith('supplementary::'):continue
   target=r['canonical_entity']+'.'+r['canonical_field']
   d.setdefault(r['source'],{}).setdefault(target,[]).append(r['source_field'])
 return d
MAP=fieldmap()
PREF={'hse_pestreg_gb':['MAPP_No'],'hse_pestreg_ni':['MAPP_No'],'apvma_pubcris':['APVMAProductNumber'],'aphia_pesticide':['permit_number'],'ctgb_authorisations':['Toelatingsnummer']}
def mapped(source,row,target):
 fields=PREF.get(source,[]) + MAP[source].get(target,[]) if target=='Registration.source_registration_key' else MAP[source].get(target,[])
 return get(row,dict.fromkeys(fields))
def batch_rows(item):
 pf=pq.ParquetFile(B/item['relative_output_path'])
 for batch in pf.iter_batches(batch_size=8192):
  yield from batch.to_pylist()
def source(item):return Path(item['relative_output_path']).stem.split('_',1)[1]
def rowhash(r):return digest(r['raw_fields_json'])
def record_id(r):return 'REC_'+digest(r['source_file_sha256']+'|'+str(r['source_row_number']))[:32]
def regbase(s,raw,r):
 val,_=mapped(s,raw,'Registration.source_registration_key')
 if useful(val):return val,False
 return 'MISSING_RECORD_'+rowhash(r),True
def ingredient_source(s,raw):
 return mapped(s,raw,'LocalActiveIngredient.original_name')
def components(s,raw,full):
 if not full:return 'NO_SOURCE_INGREDIENT',[],None
 if s in ('epa_ppls','apvma_pubcris'):
  value=raw.get('ActiveIngredientsJSON') or ''
  try:arr=json.loads(value)
  except (TypeError,ValueError):return 'UNCERTAIN_STRUCTURED_JSON',[],None
  if not isinstance(arr,list):return 'UNCERTAIN_STRUCTURED_JSON',[],None
  if s=='epa_ppls':
   filtered=[e for e in arr if isinstance(e,dict) and useful(e.get('active_ing'))]
   names=[str(e['active_ing']).strip() for e in filtered]
  else:
   filtered=[e for e in arr if isinstance(e,dict) and e.get('ConstituentTypeCode')=='A' and useful(e.get('ActiveIngredientEnglish'))]
   names=[str(e['ActiveIngredientEnglish']).strip() for e in filtered]
  source_names={norm(v) for v in full.split(' | ') if useful(v)}
  structured_names={norm(v) for v in names}
  if not names or source_names!=structured_names:return 'UNCERTAIN_NAME_SET_MISMATCH',[],arr
  out=[]
  for e,n in zip(filtered,names):
   out.append({'name':n,'code':str(e.get('pc_code') or e.get('ConstituentCode') or '').strip(),'cas':str(e.get('cas_number') or '').strip(),'json':e})
  return 'STRUCTURED_COMPONENTS_VERIFIED',out,arr
 if any(mark in full for mark in (' | ',';',' + ')):
  return 'UNCERTAIN_UNSTRUCTURED_COMBINATION',[],None
 return 'SOURCE_SINGLE_TERM',[{'name':full,'code':'','cas':'','json':{}}],None
def cas_valid(v):
 import re
 m=re.fullmatch(r'(\d{2,7})-(\d{2})-(\d)',v)
 if not m:return False
 digits=m.group(1)+m.group(2)
 return sum((i+1)*int(c) for i,c in enumerate(reversed(digits)))%10==int(m.group(3))

# Pass 1: detect source registration keys reused across distinct product labels.
conflicts=set();first={};grain=Counter();examples=[]
for item in A6['source_files']:
 s=source(item)
 for r in batch_rows(item):
  raw=json.loads(r['raw_fields_json']);rb,missing=regbase(s,raw,r)
  product,_=mapped(s,raw,'PesticideProduct.original_name')
  grain[(s,'rows')]+=1
  if missing:grain[(s,'missing_key')]+=1
  if product:
   k=(s,rb)
   old=first.setdefault(k,product)
   if old!=product:
    conflicts.add(k)
    if len(examples)<25:examples.append({'source':s,'registration_key':rb,'first_product':old,'other_product':product})
  else:grain[(s,'missing_product')]+=1
  full,_=ingredient_source(s,raw)
  if full and ' | ' in full:grain[(s,'pipe_ingredient')]+=1
  if grain[(s,'rows')]%100000==0:print('A10_GRAIN_SCAN',s,grain[(s,'rows')],flush=True)
audit={'snapshot_id':INV['snapshot_id'],'pipeline_version':PIPELINE,'conflict_key_count':len(conflicts),'conflict_examples':examples,'sources':{s:{k:v for (src,k),v in grain.items() if src==s} for s in sorted({x[0] for x in grain})},'policy':'Registration key reused across product labels is scoped by source key and product label; missing keys use source-record content digest. No cross-product merge.','created_at':NOW}
(B/'dataset/_audit_workspace/quality/A10_GRAIN_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A10_GRAIN_DONE',sum(v for (s,k),v in grain.items() if k=='rows'),'conflict_keys',len(conflicts),flush=True)

db=sqlite3.connect(WORK/'canonical_build.sqlite')
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA synchronous=NORMAL')
db.execute('PRAGMA temp_store=MEMORY')
db.executescript("""
CREATE TABLE IF NOT EXISTS registry(
 canonical_id TEXT PRIMARY KEY,entity_type TEXT NOT NULL,entity_status TEXT NOT NULL,
 created_at TEXT,superseded_by TEXT,merged_into TEXT,decision_id TEXT,schema_version TEXT,
 registry_version TEXT,natural_key TEXT NOT NULL,source_file_sha256 TEXT,source_snapshot_id TEXT,
 UNIQUE(entity_type,natural_key));
CREATE TABLE IF NOT EXISTS entities(
 entity_id TEXT PRIMARY KEY,entity_type TEXT,entity_status TEXT,jurisdiction_id TEXT,
 source_id TEXT,source_snapshot_id TEXT,source_record_id TEXT,display_label TEXT,
 grain_status TEXT,extension_properties TEXT,evidence_id TEXT);
CREATE TABLE IF NOT EXISTS names(
 name_key TEXT PRIMARY KEY,entity_id TEXT,name TEXT,name_type TEXT,language TEXT,
 normalized_name TEXT,source_id TEXT,evidence_id TEXT,source_record_id TEXT,source_field TEXT);
CREATE TABLE IF NOT EXISTS identifiers(
 identifier_key TEXT PRIMARY KEY,entity_id TEXT,identifier_type TEXT,identifier_value TEXT,
 status TEXT,source_id TEXT,evidence_id TEXT,source_record_id TEXT,source_field TEXT);
CREATE TABLE IF NOT EXISTS registrations(
 registration_id TEXT PRIMARY KEY,source_registration_key TEXT,product_id TEXT,
 jurisdiction_id TEXT,source_id TEXT,source_snapshot_id TEXT,evidence_id TEXT,
 original_status TEXT,registration_date_original TEXT,registration_date_normalized TEXT,
 expiry_date_original TEXT,expiry_date_normalized TEXT,grain_status TEXT,extension_properties TEXT);
CREATE TABLE IF NOT EXISTS registration_uses(
 registration_use_id TEXT PRIMARY KEY,registration_id TEXT,product_id TEXT,jurisdiction_id TEXT,
 source_id TEXT,source_snapshot_id TEXT,evidence_id TEXT,source_record_id TEXT,
 pairing_status TEXT,crop_original TEXT,target_original TEXT,dose_original TEXT,
 method_original TEXT,timing_original TEXT,formulation_original TEXT,
 use_pattern_original TEXT,extension_properties TEXT);
CREATE TABLE IF NOT EXISTS evidence(
 evidence_id TEXT PRIMARY KEY,source_snapshot_id TEXT,source_id TEXT,source_file_sha256 TEXT,
 content_sha256 TEXT,source_record_id TEXT,source_row_number INTEGER,source_url TEXT,
 evidence_type TEXT);
CREATE TABLE IF NOT EXISTS relations(
 assertion_id TEXT PRIMARY KEY,subject_id TEXT,predicate TEXT,object_id TEXT,
 evidence_id TEXT,source_snapshot_id TEXT,source_record_id TEXT,
 assertion_status TEXT,confidence TEXT,derivation_rule_id TEXT,pipeline_version TEXT);
CREATE TABLE IF NOT EXISTS compositions(
 assertion_id TEXT PRIMARY KEY,product_id TEXT,source_id TEXT,source_snapshot_id TEXT,
 evidence_id TEXT,source_record_id TEXT,source_field TEXT,original_combination TEXT,
 parse_status TEXT,parsing_rule_id TEXT,pipeline_version TEXT,confidence TEXT,
 component_ids_json TEXT,identifier_link_status TEXT);
""")
db.commit()
regcols=['canonical_id','entity_type','entity_status','created_at','superseded_by','merged_into','decision_id','schema_version','registry_version','natural_key','source_file_sha256','source_snapshot_id']
with (REG/'ID_REGISTRY.csv').open(encoding='utf-8-sig',newline='') as f:
 for r in csv.DictReader(f):
  db.execute('INSERT OR IGNORE INTO registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',tuple(r[c] for c in regcols))
db.commit()
cached={}
def identity(typ,k,sha='',snapshot='',cache=True):
 ck=(typ,k)
 if cache and ck in cached:return cached[ck]
 row=db.execute('SELECT canonical_id FROM registry WHERE entity_type=? AND natural_key=?',ck).fetchone()
 if row:cid=row[0]
 else:
  prefix={'Jurisdiction':'JUR','Source':'SRC','SourceSnapshot':'SSNP','CountryOrTerritory':'CTRY','RegulatoryOrganization':'ORG','Registration':'REG','PesticideProduct':'PROD','LocalActiveIngredient':'LAI','RegistrationUse':'USE','CropTerm':'CROP','TargetTerm':'TARG','FormulationTerm':'FORM','Evidence':'EVD'}.get(typ,'ENT')
  cid=prefix+'_'+uuid.uuid4().hex
  db.execute('INSERT INTO registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(cid,typ,'active',NOW,'','','DEC-001' if typ=='LocalActiveIngredient' else '',SCHEMA,REGISTRY_VERSION,k,sha,snapshot))
 if cache and len(cached)<450000:cached[ck]=cid
 return cid
def entity(cid,typ,status,jid,sid,ssnp,rid,label,grain_status,ext,eid):
 db.execute('INSERT OR IGNORE INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?)',(cid,typ,status,jid,sid,ssnp,rid,label,grain_status,json.dumps(ext,ensure_ascii=False,separators=(',',':')),eid))
def name(cid,value,typ,sid,eid,rid,field,lang='und'):
 if not value:return
 nk=digest(key(cid,value,typ,field))
 db.execute('INSERT OR IGNORE INTO names VALUES (?,?,?,?,?,?,?,?,?,?)',(nk,cid,value,typ,lang,norm(value),sid,eid,rid,field))
def ident(cid,scheme,value,status,sid,eid,rid,field):
 if not value:return
 ik=digest(key(cid,scheme,value,eid))
 db.execute('INSERT OR IGNORE INTO identifiers VALUES (?,?,?,?,?,?,?,?,?)',(ik,cid,scheme,value,status,sid,eid,rid,field))
def relation(a,p,b,eid,ssnp,rid,status='source_asserted',rule=''):
 if not a or not b or a==b:raise RuntimeError('Invalid relation endpoint')
 aid='RA_'+digest(key(a,p,b,eid,status,rule))[:32]
 db.execute('INSERT OR IGNORE INTO relations VALUES (?,?,?,?,?,?,?,?,?,?,?)',(aid,a,p,b,eid,ssnp,rid,status,'SOURCE_DIRECT' if status=='source_asserted' else 'RULE_DERIVED',rule,PIPELINE))
meta={}
for r in db.execute("SELECT canonical_id,entity_type,natural_key FROM registry WHERE entity_type IN ('Jurisdiction','Source','SourceSnapshot')"):
 meta[(r[1],r[2])]=r[0]
for item in INV['primary_source_files']:
 s=item['source'];jur=item['jurisdiction'];sha=item['sha256']
 jid=meta[('Jurisdiction',jur)];sid=meta[('Source',s)];ssnp=meta[('SourceSnapshot',s+'|'+sha)]
 entity(jid,'Jurisdiction','active',jid,'','', '',jur,'REGULATORY_SCOPE',{'jurisdiction_code':jur},'')
 entity(sid,'Source','active',jid,sid,'','',s,'OFFICIAL_SOURCE',{'source_key':s,'public_distribution':'RESTRICTED_UNTIL_REVIEW'},'')
 entity(ssnp,'SourceSnapshot','active',jid,sid,ssnp,'',s+' snapshot','IMMUTABLE_PROJECT_SNAPSHOT',{'source_sha256':sha,'raw_snapshot_id':INV['snapshot_id']},'')
 evid=identity('Evidence',key(s,'MANIFEST',sha),sha,ssnp,False)
 db.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?,?)',(evid,ssnp,sid,sha,sha,'MANIFEST',0,'','SOURCE_MANIFEST'))
 relation(sid,'HAS_SNAPSHOT',ssnp,evid,ssnp,'MANIFEST')
 db.commit()

srcschema=pa.schema([
 ('source_record_id',pa.string()),('evidence_id',pa.string()),('source_snapshot_id',pa.string()),
 ('source_id',pa.string()),('jurisdiction_id',pa.string()),('source_file_sha256',pa.string()),
 ('source_row_number',pa.int64()),('raw_fields_json',pa.large_string()),('derived_fields_json',pa.large_string()),
 ('registration_id',pa.string()),('product_id',pa.string()),('registration_use_id',pa.string()),
 ('ingredient_parse_status',pa.string())])
srcwork=WORK/'source_records.incomplete.parquet'
writer=pq.ParquetWriter(srcwork,srcschema,compression='zstd',compression_level=5)
batch={n:[] for n in srcschema.names}
def flush():
 if batch['source_record_id']:
  writer.write_table(pa.Table.from_pydict(batch,schema=srcschema))
  for v in batch.values():v.clear()
stats=Counter();quarantine_path=WORK/'A10_COMPONENTIZATION_REVIEW.incomplete.csv'
qf=quarantine_path.open('w',encoding='utf-8-sig',newline='')
qw=csv.writer(qf);qw.writerow(['source_record_id','reason_code','source','stage','raw_reference','review_status'])
try:
 for item in A6['source_files']:
  s=source(item);jur=item['source_path'].split('/')[2] if False else Path(item['relative_output_path']).stem.split('_',1)[0]
  sha=item['source_sha256'];sid=meta[('Source',s)]
  ssnp=meta[('SourceSnapshot',s+'|'+sha)]
  jurisdiction=next(x['jurisdiction'] for x in INV['primary_source_files'] if x['source']==s)
  jid=meta[('Jurisdiction',jurisdiction)]
  for r in batch_rows(item):
   raw=json.loads(r['raw_fields_json']);rid=record_id(r);rh=rowhash(r)
   ekey=key(s,rh);eid=identity('Evidence',ekey,sha,ssnp,False)
   source_url,_=mapped(s,raw,'Source.record_url')
   db.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?,?)',(eid,ssnp,sid,sha,rh,rid,r['source_row_number'],source_url,'SOURCE_RECORD'))
   base,missing=regbase(s,raw,r)
   prodval,prodfield=mapped(s,raw,'PesticideProduct.original_name')
   regkey=key(s,base,prodval if (s,base) in conflicts else '')
   rgstatus='MISSING_KEY_CONTENT_SCOPED' if missing else ('KEY_COLLISION_PRODUCT_SCOPED' if (s,base) in conflicts else 'SOURCE_KEY')
   regid=identity('Registration',regkey,sha,ssnp)
   entity(regid,'Registration','active',jid,sid,ssnp,rid,base,rgstatus,{'source_registration_key':base,'product_label_scope':prodval if (s,base) in conflicts else ''},eid)
   productid=''
   if prodval:
    productid=identity('PesticideProduct',key(s,regkey,prodval),sha,ssnp)
    entity(productid,'PesticideProduct','active',jid,sid,ssnp,rid,prodval,'REGISTRATION_SCOPED_SOURCE_PRODUCT',{'source_field':prodfield,'source_registration_key':base},eid)
    name(productid,prodval,'original_name',sid,eid,rid,prodfield)
   status,_=mapped(s,raw,'Registration.original_status')
   rdate,rdatefield=mapped(s,raw,'Registration.first_registration_date_original')
   edate,edatefield=mapped(s,raw,'Registration.expiry_date_original')
   derived=json.loads(r['derived_fields_json'])
   def parsed(field):
    return derived.get(field,{}).get('parsed_date') or '' if field else ''
   db.execute('INSERT OR IGNORE INTO registrations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(regid,base,productid,jid,sid,ssnp,eid,status,rdate,parsed(rdatefield),edate,parsed(edatefield),rgstatus,json.dumps({'registration_key_field':mapped(s,raw,'Registration.source_registration_key')[1],'status_original':status},ensure_ascii=False)))
   relation(jid,'HAS_REGISTRATION',regid,eid,ssnp,rid)
   if productid:relation(regid,'REGISTERS_PRODUCT',productid,eid,ssnp,rid)
   usefields={target:[{'field':f,'value':raw[f]} for f in fields if useful(raw.get(f))] for target,fields in MAP[s].items() if target.startswith('RegistrationUse.')}
   usefields={k:v for k,v in usefields.items() if v}
   useid=''
   if usefields:
    useid=identity('RegistrationUse',key(s,regkey,rh),sha,ssnp,False)
    entity(useid,'RegistrationUse','active',jid,sid,ssnp,rid,base+' use','SOURCE_ROW_CONTEXT_NO_CARTESIAN_INFERENCE',{'source_record_id':rid},eid)
    u=lambda target:(usefields.get('RegistrationUse.'+target) or [{}])[0].get('value','')
    db.execute('INSERT OR IGNORE INTO registration_uses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(useid,regid,productid,jid,sid,ssnp,eid,rid,'SOURCE_ROW_CONTEXT_NO_CARTESIAN_INFERENCE',u('crop_original'),u('target_original'),u('dose_original'),u('application_method_original'),u('application_timing_original'),u('formulation_original'),u('use_pattern_original'),json.dumps(usefields,ensure_ascii=False,separators=(',',':'))))
    relation(regid,'HAS_USE',useid,eid,ssnp,rid)
    if productid:relation(useid,'USES_PRODUCT',productid,eid,ssnp,rid)
    for target,typ,pred in [('crop_original','CropTerm','FOR_CROP'),('target_original','TargetTerm','FOR_TARGET')]:
     val=u(target)
     if val:
      termid=identity(typ,key(s,val),sha,ssnp)
      field=(usefields.get('RegistrationUse.'+target) or [{}])[0].get('field','')
      entity(termid,typ,'active',jid,sid,ssnp,rid,val,'UNSPLIT_SOURCE_FIELD',{'source_field':field},eid)
      name(termid,val,'original_name',sid,eid,rid,field)
      relation(useid,pred,termid,eid,ssnp,rid)
    form=u('formulation_original')
    if form:
     formid=identity('FormulationTerm',key(s,form),sha,ssnp)
     field=(usefields.get('RegistrationUse.formulation_original') or [{}])[0].get('field','')
     entity(formid,'FormulationTerm','active',jid,sid,ssnp,rid,form,'UNSPLIT_SOURCE_FIELD_OWNER_UNVERIFIED',{'source_field':field},eid)
     name(formid,form,'original_name',sid,eid,rid,field)
   full,activefield=ingredient_source(s,raw)
   parse_status,parts,_=components(s,raw,full)
   compids=[];links=[]
   if full:
    stats['active_source_rows']+=1
    if parse_status.startswith('UNCERTAIN'):
     qw.writerow([rid,parse_status,s,'A10',sha+':'+str(r['source_row_number']),'OPEN'])
     stats['quarantine_component_rows']+=1
    for part in parts:
     n=part['name'];code=part['code'];cas=part['cas']
     namespace='STRUCTURED' if parse_status=='STRUCTURED_COMPONENTS_VERIFIED' else 'SOURCE_TERM'
     ikey=key(s,namespace,code,n)
     ingid=identity('LocalActiveIngredient',ikey,sha,ssnp)
     entity(ingid,'LocalActiveIngredient','active',jid,sid,ssnp,rid,n,parse_status,{'source_field':activefield,'source_code':code,'identity_status':'LOCAL_TERM_ONLY','componentization_rule':'DEC-001-v1.0.0'},eid)
     name(ingid,n,'original_name',sid,eid,rid,activefield)
     if code:
      scheme='EPA_PC_CODE' if s=='epa_ppls' else 'APVMA_CONSTITUENT_CODE'
      ident(ingid,scheme,code,'SOURCE_CODE_NOT_GLOBAL_ID',sid,eid,rid,'ActiveIngredientsJSON')
     if cas:
      cs='SOURCE_STRUCTURED_DIRECT_CHECKSUM_VALID' if cas_valid(cas) else 'SOURCE_STRUCTURED_DIRECT_INVALID_CAS'
      ident(ingid,'CAS_RN',cas,cs,sid,eid,rid,'ActiveIngredientsJSON.cas_number')
      links.append(cs)
     compids.append(ingid)
     if productid:relation(productid,'CONTAINS_ACTIVE_INGREDIENT',ingid,eid,ssnp,rid,'source_asserted','DEC-001-STRUCTURED' if namespace=='STRUCTURED' else 'SOURCE_ACTIVE_FIELD')
    if compids:stats['componentized_source_rows']+=1
    aid='CA_'+digest(key(rid,full))[:32]
    db.execute('INSERT OR IGNORE INTO compositions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(aid,productid,sid,ssnp,eid,rid,activefield,full,parse_status,'DEC-001-v1.0.0',PIPELINE,'SOURCE_STRUCTURED_NAME_SET' if parse_status=='STRUCTURED_COMPONENTS_VERIFIED' else ('SOURCE_SINGLE_FIELD' if parse_status=='SOURCE_SINGLE_TERM' else 'UNCERTAIN'),json.dumps(sorted(set(compids))), 'DIRECT_SOURCE_JSON' if links else 'UNRESOLVED_OR_NOT_PRESENT'))
   orgval,orgfield=mapped(s,raw,'RegulatoryOrganization.original_name')
   if orgval:
    orgid=identity('RegulatoryOrganization',key(s,orgval),sha,ssnp)
    entity(orgid,'RegulatoryOrganization','active',jid,sid,ssnp,rid,orgval,'SOURCE_NAMED_ORGANIZATION',{'source_field':orgfield},eid)
    name(orgid,orgval,'original_name',sid,eid,rid,orgfield)
    relation(orgid,'REGULATES',jid,eid,ssnp,rid)
   iso2,isofield=mapped(s,raw,'CountryOrTerritory.iso2_source')
   if iso2 and len(iso2)==2 and iso2.isalpha():
    countryid=identity('CountryOrTerritory',key(iso2.upper()),sha,ssnp)
    entity(countryid,'CountryOrTerritory','active','','','',rid,iso2.upper(),'SOURCE_ISO2',{'iso2':iso2.upper()},eid)
    relation(jid,'IN_TERRITORY',countryid,eid,ssnp,rid)
   values={'source_record_id':rid,'evidence_id':eid,'source_snapshot_id':ssnp,'source_id':sid,'jurisdiction_id':jid,'source_file_sha256':sha,'source_row_number':r['source_row_number'],'raw_fields_json':r['raw_fields_json'],'derived_fields_json':r['derived_fields_json'],'registration_id':regid,'product_id':productid,'registration_use_id':useid,'ingredient_parse_status':parse_status}
   for n,v in values.items():batch[n].append(v)
   stats['source_rows']+=1
   if stats['source_rows']%10000==0:
    flush();db.commit()
   if stats['source_rows']%50000==0:print('A10_A11_BUILD',stats['source_rows'],'registry',db.execute('SELECT COUNT(*) FROM registry').fetchone()[0],flush=True)
  print('A10_A11_SOURCE_DONE',s,item['row_count'],flush=True)
 flush();db.commit()
finally:
 writer.close();qf.close();db.commit()
if stats['source_rows']!=A6['row_count']:raise RuntimeError('Source row count mismatch')
os.replace(srcwork,OUT/'source_records.parquet')
os.replace(quarantine_path,B/'dataset/quarantine/A10_COMPONENTIZATION_REVIEW.csv')
def export(sql,cols,path,chunk=25000):
 cur=db.execute(sql);dest=WORK/(path.stem+'.incomplete.parquet')
 schema=pa.schema([(c,pa.string()) for c in cols])
 w=pq.ParquetWriter(dest,schema,compression='zstd',compression_level=5)
 total=0
 try:
  while True:
   rows=cur.fetchmany(chunk)
   if not rows:break
   values={c:[str(row[i]) if row[i] is not None else '' for row in rows] for i,c in enumerate(cols)}
   w.write_table(pa.Table.from_pydict(values,schema=schema));total+=len(rows)
 finally:w.close()
 os.replace(dest,path)
 return total
tables={
 'entities':['entity_id','entity_type','entity_status','jurisdiction_id','source_id','source_snapshot_id','source_record_id','display_label','grain_status','extension_properties','evidence_id'],
 'names':['name_key','entity_id','name','name_type','language','normalized_name','source_id','evidence_id','source_record_id','source_field'],
 'identifiers':['identifier_key','entity_id','identifier_type','identifier_value','status','source_id','evidence_id','source_record_id','source_field'],
 'registrations':['registration_id','source_registration_key','product_id','jurisdiction_id','source_id','source_snapshot_id','evidence_id','original_status','registration_date_original','registration_date_normalized','expiry_date_original','expiry_date_normalized','grain_status','extension_properties'],
 'registration_uses':['registration_use_id','registration_id','product_id','jurisdiction_id','source_id','source_snapshot_id','evidence_id','source_record_id','pairing_status','crop_original','target_original','dose_original','method_original','timing_original','formulation_original','use_pattern_original','extension_properties'],
 'evidence':['evidence_id','source_snapshot_id','source_id','source_file_sha256','content_sha256','source_record_id','source_row_number','source_url','evidence_type'],
 'relationship_assertions':['assertion_id','subject_id','predicate','object_id','evidence_id','source_snapshot_id','source_record_id','assertion_status','confidence','derivation_rule_id','pipeline_version'],
 'composition_assertions':['assertion_id','product_id','source_id','source_snapshot_id','evidence_id','source_record_id','source_field','original_combination','parse_status','parsing_rule_id','pipeline_version','confidence','component_ids_json','identifier_link_status']
}
dbnames={'relationship_assertions':'relations','composition_assertions':'compositions'}
manifest={'snapshot_id':INV['snapshot_id'],'schema_version':SCHEMA,'kg_schema_version':'PESTKG_KG_SCHEMA_v0.2','pipeline_version':PIPELINE,'canonical_registry_version':REGISTRY_VERSION,'decision_set':['DEC-RAW-001','DEC-001','DEC-002'],'source_rows':stats['source_rows'],'grain_audit':'dataset/_audit_workspace/quality/A10_GRAIN_AUDIT.json','quarantine_component_rows':stats['quarantine_component_rows'],'tables':{},'completed_at':datetime.now(timezone.utc).isoformat()}
for name,cols in tables.items():
 path=OUT/(name+'.parquet');sql='SELECT '+','.join(cols)+' FROM '+dbnames.get(name,name)+' ORDER BY '+cols[0]
 n=export(sql,cols,path)
 manifest['tables'][name]={'path':str(path.relative_to(B)).replace('\\','/'),'rows':n,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 print('A11_EXPORT',name,n,flush=True)
p=REG/'ID_REGISTRY.csv'
regwork=WORK/'ID_REGISTRY.incomplete.csv'
with regwork.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(regcols)
 for row in db.execute('SELECT '+','.join(regcols)+' FROM registry ORDER BY entity_type,natural_key'):w.writerow(row)
os.replace(regwork,p)
regmeta={'registry_version':REGISTRY_VERSION,'schema_version':SCHEMA,'snapshot_id':INV['snapshot_id'],'row_count':db.execute('SELECT COUNT(*) FROM registry').fetchone()[0],'entities_by_type':dict(db.execute('SELECT entity_type,COUNT(*) FROM registry GROUP BY entity_type').fetchall()),'registry_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'updated_at':datetime.now(timezone.utc).isoformat(),'decision_set':['DEC-001','DEC-002'],'scope':'Complete source-local canonical ID registry; UUID4 assigned and persisted, source-scoped keys prevent unsupported chemical merge.'}
(REG/'REGISTRY_METADATA.json').write_text(json.dumps(regmeta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest['registry_sha256']=regmeta['registry_sha256']
manifest['registry_rows']=regmeta['row_count']
manifest['tables']['source_records']={'path':'dataset/canonical/v1_0/source_records.parquet','rows':stats['source_rows'],'bytes':(OUT/'source_records.parquet').stat().st_size,'sha256':hashlib.sha256((OUT/'source_records.parquet').read_bytes()).hexdigest()}
(OUT/'A11_CANONICAL_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A10_A11_DONE',json.dumps({'source_rows':stats['source_rows'],'registry_rows':regmeta['row_count'],'componentized_rows':stats['componentized_source_rows'],'quarantine_component_rows':stats['quarantine_component_rows']},ensure_ascii=True),flush=True)
db.close()

