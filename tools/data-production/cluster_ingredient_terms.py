"""A9 lexical candidate grouping of source-local ingredient terms; never merge."""
import csv,hashlib,json
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
import pyarrow.parquet as pq
B=Path(__file__).resolve().parents[2]
P=B/'dataset/names/SOURCE_NAME_ASSERTIONS.parquet';OUT=B/'dataset/candidates';OUT.mkdir(parents=True,exist_ok=True)
terms={};tot=0
for chunk in pq.ParquetFile(P).iter_batches(columns=['source_file_sha256','source_row_number','jurisdiction','source','source_field','entity_concept','name_type','original_value','search_normalized'],batch_size=30000):
 for sha,row,jur,source,field,concept,typ,original,key in zip(*[chunk.column(i).to_pylist() for i in range(9)]):
  if concept!='LocalActiveIngredient' or not key:continue
  tot+=1
  tkey=(sha,field,original)
  if tkey not in terms:terms[tkey]={'sha':sha,'first_row':row,'jurisdiction':jur,'source':source,'field':field,'name_type':typ,'original':original,'normalized':key,'occurrences':0}
  terms[tkey]['occurrences']+=1
clusters=defaultdict(list)
for t in terms.values():clusters[t['normalized']].append(t)
qual={k:v for k,v in clusters.items() if len(v)>=2}
mc=OUT/'A9_LOCAL_INGREDIENT_CANDIDATE_MEMBERS.csv';cc=OUT/'A9_CANDIDATE_CLUSTERS.csv'
with mc.open('w',encoding='utf-8-sig',newline='') as fm,cc.open('w',encoding='utf-8-sig',newline='') as fc:
 mw=csv.writer(fm);cw=csv.writer(fc)
 mw.writerow(['snapshot_id','candidate_cluster_id','entity_id','id_kind','jurisdiction','source','source_file_sha256','source_field','source_row_example','original_name','name_type','normalized_name','source_occurrence_count','candidate_reason','supporting_identifiers','conflicts','confidence_features'])
 cw.writerow(['snapshot_id','candidate_cluster_id','normalized_name','member_term_count','jurisdiction_count','jurisdictions','source_count','source_occurrences','candidate_reason','identity_status'])
 for key,ts in sorted(qual.items()):
  cid='CAND_'+hashlib.sha256(key.encode('utf-8')).hexdigest()[:24];jurs=sorted({x['jurisdiction'] for x in ts});sources={x['source'] for x in ts}
  reason='CROSS_JURISDICTION_LEXICAL' if len(jurs)>1 else 'WITHIN_JURISDICTION_LEXICAL'
  cw.writerow(['PESTKG_RAW_SNAPSHOT_2026-09-23',cid,key,len(ts),len(jurs),' | '.join(jurs),len(sources),sum(x['occurrences'] for x in ts),reason,'CANDIDATE_ONLY'])
  for t in sorted(ts,key=lambda x:(x['jurisdiction'],x['source'],x['field'],x['original'])):
   member='LTERM_'+hashlib.sha256((t['sha']+'\0'+t['field']+'\0'+t['original']).encode('utf-8')).hexdigest()[:24]
   features=json.dumps({'lexical_key_equal':True,'jurisdiction_count':len(jurs),'source_occurrences':t['occurrences']},separators=(',',':'))
   mw.writerow(['PESTKG_RAW_SNAPSHOT_2026-09-23',cid,member,'PROVISIONAL_SOURCE_TERM_KEY',t['jurisdiction'],t['source'],t['sha'],t['field'],t['first_row'],t['original'],t['name_type'],key,t['occurrences'],reason,'NOT_LINKED_TO_LOCAL_TERM','NOT_EVALUATED',features])
summary={'snapshot_id':'PESTKG_RAW_SNAPSHOT_2026-09-23','pipeline_version':'a-line-candidate-clustering-v1.0.0','input_name_assertions':tot,'unique_source_local_terms':len(terms),'candidate_clusters':len(qual),'candidate_member_terms':sum(map(len,qual.values())),'cross_jurisdiction_clusters':sum(len({x['jurisdiction'] for x in ts})>1 for ts in qual.values()),'max_member_terms_per_cluster':max((len(x) for x in qual.values()),default=0),'singleton_terms':sum(len(x)==1 for x in clusters.values()),'completed_at':datetime.now(timezone.utc).isoformat(),'policy':'Provisional staging IDs only; lexical normalized name yields candidates and never exact chemical identity or canonical IDs.'}
(OUT/'A9_CLUSTER_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A9_DONE',summary,flush=True)
