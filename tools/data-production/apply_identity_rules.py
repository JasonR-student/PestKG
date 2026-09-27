"""Apply approved lexicalAlignment-only rule to provisional A9 source terms."""
import csv,json
from pathlib import Path
from datetime import datetime,timezone
B=Path(__file__).resolve().parents[2];src=B/'dataset/candidates/A9_LOCAL_INGREDIENT_CANDIDATE_MEMBERS.csv';dest=B/'dataset/candidates/A9B_ALIGNMENT_ASSERTIONS.csv'
n=0
with src.open(encoding='utf-8-sig',newline='') as f,dest.open('w',encoding='utf-8-sig',newline='') as o:
 r=csv.DictReader(f);w=csv.writer(o)
 w.writerow(['snapshot_id','candidate_cluster_id','provisional_term_id','alignment_state','rule_id','evidence_source_sha256','evidence_source_row','evidence_source_field','identity_decision','canonical_id_status'])
 for x in r:
  w.writerow([x['snapshot_id'],x['candidate_cluster_id'],x['entity_id'],'lexicalAlignment','PESTKG_V0_2_LEXICAL_NAME_ONLY',x['source_file_sha256'],x['source_row_example'],x['source_field'],'NONE','NOT_ASSIGNED']);n+=1
summary={'snapshot_id':'PESTKG_RAW_SNAPSHOT_2026-09-23','rule_version':'PESTKG_V0_2_LEXICAL_NAME_ONLY','lexical_alignment_members':n,'candidate_match':0,'exact_match':0,'auto_merge':0,'identity_decision_match':0,'generated_at':datetime.now(timezone.utc).isoformat(),'policy':'Normalized lexical equality supports discovery only; no approved automatic exact identity rule was applied.'}
(B/'dataset/candidates/A9B_RULE_ENGINE_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert n==23545
print('A9B_DONE',summary)
