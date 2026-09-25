"""Extend A4/A5 field ledger to all profiled supplementary structured assets."""
import csv,json
from pathlib import Path
from collections import Counter
B=Path(__file__).resolve().parents[2]
P=B/'dataset/_audit_workspace/profiles/supplementary'
M=B/'dataset/mappings'
I=list(csv.DictReader((P/'SUPPLEMENTARY_PROFILE_INDEX.csv').open(encoding='utf-8-sig',newline='')))
country={'澳大利亚':'AU','中国':'CN','英国与北爱尔兰':'GB_OR_GB_NI','匈牙利':'HU','爱尔兰':'IE','日本':'JP','韩国':'KR','荷兰':'NL','新西兰':'NZ','台湾':'TW','中国台湾':'TW','美国':'US'}
def jurisdiction(path):
 parts=path.split('/')
 for part in parts:
  if part in country:return country[part]
 return 'CROSS_JURISDICTION_OR_UNKNOWN'
map_path=M/'source_field_mapping.csv';class_path=M/'DATA_FIELD_CLASSIFICATION.csv'
with map_path.open(encoding='utf-8-sig',newline='') as f: mapped=list(csv.DictReader(f))
with class_path.open(encoding='utf-8-sig',newline='') as f: classified=list(csv.DictReader(f))
base_m=[r for r in mapped if not r['source'].startswith('supplementary::')]
base_c=[r for r in classified if not r['source'].startswith('supplementary::')]
supp_m=[];supp_c=[];status=Counter()
for item in I:
 status[item['status']]+=1
 d=json.loads((P/item['profile']).read_text(encoding='utf-8'))
 header=d.get('header') or []
 if item['status']!='DONE' or not header:continue
 for index,field in enumerate(header):
  # A supplementary header is kept as a source-specific assertion until its actual record grain is joined to the primary source.
  sf=field if field else f'__UNNAMED_COLUMN_{index+1}'
  source='supplementary::'+item['relative_path']
  row={'source':source,'jurisdiction':jurisdiction(item['relative_path']),'source_table':item['relative_path'],'source_field':sf,'canonical_entity':'SourceFieldAssertion','canonical_field':'extension_properties.'+sf,'transform_rule':'PRESERVE_ORIGINAL_TEXT_AND_SOURCE_FIELD_NAME','required':'NO_GLOBAL_REQUIREMENT','confidence':'SOURCE_SPECIFIC','notes':'Supplementary file header retained; record grain and linkage require source-specific validation before promotion.'}
  supp_m.append(row)
  supp_c.append({'snapshot_id':'PESTKG_RAW_SNAPSHOT_2026-09-23','source':source,'jurisdiction':row['jurisdiction'],'source_table':row['source_table'],'source_field':sf,'classification':'EXTENSION','canonical_entity':row['canonical_entity'],'canonical_field':row['canonical_field'],'reason':'Supplementary field retained with source path; no unsupported cross-source semantic inference','nonempty_count':str(int(d['row_count'])-int(d['blank_counts'][index])) if len(d.get('blank_counts',[]))>index else '', 'row_count':str(d['row_count'])})
cols=['source','jurisdiction','source_table','source_field','canonical_entity','canonical_field','transform_rule','required','confidence','notes']
with map_path.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(base_m+supp_m)
cols=['snapshot_id','source','jurisdiction','source_table','source_field','classification','canonical_entity','canonical_field','reason','nonempty_count','row_count']
with class_path.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(base_c+supp_c)
report=B/'docs/audits/A4_A5_FIELD_MAPPING_REVIEW.md'
s=report.read_text(encoding='utf-8')
s=s.replace('**Scope:** all observed columns of 12 primary official CSVs. **Status:** A4 and A5 DONE for these primary sources. Supplementary assets retain separate A3 profiles and require field-level integration when their grain is established.',f'**Scope:** all observed columns of 12 primary official CSVs and 99 readable supplementary structured assets. **Status:** A4 and A5 DONE for observable fields; one truncated GZIP, one legacy XLS without a reader, and one empty file have no validated field schema.')
s=s.replace('- Source fields: 517; CORE 223; EXTENSION 294; RAW_ONLY 0; IGNORED_WITH_REASON 0.',f'- Source fields: {len(base_m)+len(supp_m)}; CORE 223; EXTENSION {len(base_m)+len(supp_m)-223}; RAW_ONLY 0; IGNORED_WITH_REASON 0. The {len(supp_m)} supplementary fields are held as source-specific extension assertions pending grain/linkage validation.')
s=s.replace('**Next:** Human Gate 1 schema review and A6 normalization on the frozen files. Supplementary use-detail grain remains to be established before creating RegistrationUse facts.',f'**Supplementary profiling status:** {dict(status)}. The truncated ChEBI GZIP is quarantined; the legacy JP XLS remains an explicitly deferred technical gap; the AU empty file is recorded without invented columns. Supplementary use-detail grain remains to be established before creating RegistrationUse facts.\n\n**Next:** Human Gate 1 schema review and A6 normalization on the frozen files.')
report.write_text(s,encoding='utf-8')
print(f'A4_A5_EXTENDED primary={len(base_m)} supplementary={len(supp_m)} total={len(base_m)+len(supp_m)} status={dict(status)}')
