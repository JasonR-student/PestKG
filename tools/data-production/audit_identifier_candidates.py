"""A8 conflict-candidate and AGROVOC cache audit, preserving source evidence."""
import csv,json,re
from pathlib import Path
from collections import defaultdict,Counter
import pyarrow.parquet as pq
B=Path(__file__).resolve().parents[2]
OUT=B/'dataset/identifiers';P=OUT/'SOURCE_EXTERNAL_IDENTIFIERS.parquet'
subject_cas=defaultdict(set);cas_subject=defaultdict(set);evidence=defaultdict(list)
for chunk in pq.ParquetFile(P).iter_batches(columns=['source_path','source_row_number','subject_scope','source_subject_key','scheme','normalized_value','validation_status'],batch_size=20000):
 for src,row,scope,sub,scheme,value,status in zip(*[chunk.column(i).to_pylist() for i in range(7)]):
  if scope!='REFERENCE_CHEBI_COMPOUND' or scheme!='CAS_RN' or status!='CHECKSUM_VALID' or not value:continue
  subject_cas[sub].add(value);cas_subject[value].add(sub)
  key=(sub,value)
  if len(evidence[key])<3:evidence[key].append(f'{src}#row={row}')
rows=[]
for sub,values in subject_cas.items():
 if len(values)>1:rows.append({'candidate_type':'ONE_CHEBI_MULTIPLE_CAS','subject_or_value':sub,'distinct_counterparts':len(values),'counterparts':' | '.join(sorted(values)),'evidence':' | '.join(evidence[(sub,v)][0] for v in sorted(values)[:5]),'resolution_status':'CANDIDATE_REVIEW_NO_AUTO_IDENTITY'})
for value,subjects in cas_subject.items():
 if len(subjects)>1:rows.append({'candidate_type':'ONE_CAS_MULTIPLE_CHEBI','subject_or_value':value,'distinct_counterparts':len(subjects),'counterparts':' | '.join(sorted(subjects)),'evidence':' | '.join(evidence[(sub,value)][0] for sub in sorted(subjects)[:5]),'resolution_status':'CANDIDATE_REVIEW_NO_AUTO_IDENTITY'})
rows.sort(key=lambda x:(x['candidate_type'],x['subject_or_value']))
with (OUT/'A8_IDENTIFIER_CONFLICT_CANDIDATES.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['candidate_type','subject_or_value','distinct_counterparts','counterparts','evidence','resolution_status']);w.writeheader();w.writerows(rows)
cache=Path('data/01_raw_sources/外部参考数据/Crop_Target_English_Enrichment/agrovoc_search_cache')
root=Path(json.loads((B/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))['root_path'])
outrows=[];bad=0
for f in sorted((root/cache).glob('*.json')):
 d=json.loads(f.read_text(encoding='utf-8'))
 for i,item in enumerate(d.get('results') or [],1):
  uri=item.get('uri') or ''
  if not re.fullmatch(r'https?://aims\.fao\.org/aos/agrovoc/c_[0-9a-f]+',uri):bad+=1
  outrows.append({'source_path':(cache/f.name).as_posix(),'result_ordinal':i,'agrovoc_uri':uri,'label':item.get('prefLabel') or '', 'language':item.get('lang') or 'und','status':'SEARCH_CANDIDATE_ONLY'})
with (OUT/'A8_AGROVOC_SEARCH_CANDIDATES.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['source_path','result_ordinal','agrovoc_uri','label','language','status']);w.writeheader();w.writerows(outrows)
summary={'ChEBI_compounds_with_multiple_valid_CAS':sum(len(x)>1 for x in subject_cas.values()),'valid_CAS_linked_to_multiple_ChEBI_compounds':sum(len(x)>1 for x in cas_subject.values()),'conflict_candidate_rows':len(rows),'AGROVOC_search_result_rows':len(outrows),'AGROVOC_URI_not_matching_expected_pattern':bad}
(OUT/'A8_CONFLICT_AND_AGROVOC_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A8_TRIAGE_DONE',summary)
