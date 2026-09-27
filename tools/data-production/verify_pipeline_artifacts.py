"""Cross-stage QA of completed A-Line artifacts; never rehash the raw tree."""
import csv,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import pyarrow.parquet as pq
B=Path(__file__).resolve().parents[2]
read=lambda p:json.loads((B/p).read_text(encoding='utf-8'))
hashfile=lambda p:hashlib.file_digest((B/p).open('rb'),'sha256').hexdigest()
checks={};warnings=[]
def check(name,condition):
 checks[name]=bool(condition)
 if not condition:raise RuntimeError('QA failed: '+name)
raw=read('dataset/raw_manifest/RAW_INPUT_MANIFEST.json')
check('A1_snapshot_and_count',raw['snapshot_id']=='PESTKG_RAW_SNAPSHOT_2026-09-23' and raw['file_count']==72761)
check('A1_sha_list_digest',hashfile('dataset/raw_manifest/RAW_INPUT_SHA256.csv')==raw['sha256_manifest_sha256'])
inv=read('dataset/raw_manifest/RAW_INPUT_INVENTORY.json');check('A1_12_primary_sources',len(inv['primary_source_files'])==12)
profile=read('dataset/_audit_workspace/profiles/A3_JSON_COLLECTION_PROFILE.json');check('A3_JSON_parsed',profile['file_count']==71855 and profile['error_count']==0)
with (B/'dataset/mappings/source_field_mapping.csv').open(encoding='utf-8-sig') as f:m=list(csv.DictReader(f))
with (B/'dataset/mappings/DATA_FIELD_CLASSIFICATION.csv').open(encoding='utf-8-sig') as f:c=list(csv.DictReader(f))
check('A4_A5_field_parity',len(m)==len(c)==1827 and sum(x['classification']=='CORE' for x in c)==223)
a6=read('dataset/normalized/A6_NORMALIZED_MANIFEST.json');check('A6_count',len(a6['source_files'])==12 and a6['row_count']==821183)
for x in a6['source_files']:
 p=x['relative_output_path']
 check('A6_'+Path(p).stem,pq.ParquetFile(B/p).metadata.num_rows==x['row_count'] and hashfile(p)==x['output_sha256'])
a7=read('dataset/names/A7_NAME_ASSERTIONS_MANIFEST.json');check('A7_assertions',pq.ParquetFile(B/a7['output_path']).metadata.num_rows==a7['assertion_count']==6472303 and hashfile(a7['output_path'])==a7['output_sha256'])
a8=read('dataset/identifiers/A8_IDENTIFIER_MANIFEST.json');check('A8_assertions',pq.ParquetFile(B/a8['output_path']).metadata.num_rows==a8['assertion_count']==568506 and hashfile(a8['output_path'])==a8['output_sha256'])
a9=read('dataset/candidates/A9_CLUSTER_SUMMARY.json');check('A9_clusters',a9['candidate_clusters']==8853 and a9['cross_jurisdiction_clusters']==1135)
registry=read('dataset/canonical_registry/REGISTRY_METADATA.json');check('A10_registry_ids',registry['row_count']>=36 and all(registry['entities_by_type'].get(t,0)>=12 for t in ('Jurisdiction','Source','SourceSnapshot')) and hashfile('dataset/canonical_registry/ID_REGISTRY.csv')==registry['registry_sha256'])
a11=read('dataset/canonical/partial_metadata/A11_PARTIAL_METADATA_MANIFEST.json')
for name,x in a11['tables'].items():check('A11_'+name,hashfile('dataset/canonical/partial_metadata/'+name)==x['sha256'] and x['rows']==12)
a15=read('dataset/display/A15_PROJECTION_CONTRACT.json');check('A15_schema_only',a15['status']=='SCHEMA_ONLY_NO_GRAPH_DATA' and len(a15['node_types'])==11 and len(a15['predicates'])==15)
with (B/'dataset/license/A17_SOURCE_LICENSE_MATRIX.csv').open(encoding='utf-8-sig') as f:license=list(csv.DictReader(f))
check('A17_restricted_unknown',len(license)==18 and all(x['release_disposition']=='RESTRICTED_UNTIL_REVIEW' for x in license))
q=(B/'docs/audits/A_LINE_DECISION_QUEUE.md').read_text(encoding='utf-8');check('semantic_decisions_recorded','## DEC-001' in q and '## DEC-002' in q)
if list((B/'dataset/names').glob('*.incomplete.parquet')):warnings.append('Preserved interrupted A7 attempt: dataset/names/SOURCE_NAME_ASSERTIONS.20260924T015553Z.incomplete.parquet; final A7 output is separately verified.')
warnings+=['ChEBI official structures.tsv.gz is truncated/quarantined.','Legacy upstream manifest does not prove upstream completeness; DEC-RAW-001 establishes this project snapshot.','Current completeness is determined by A_LINE_TASK_STATE.md and final A12/A14/A16/A18/A20 gates; do not infer full release completion from this completed-artifact checker.']
res={'snapshot_id':raw['snapshot_id'],'quality_status':'COMPLETED_ARTIFACTS_QA_PASS_FULL_RELEASE_NOT_READY','checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'check_count':len(checks),'warnings':warnings,'raw_tree_rehashed':False}
out=B/'dataset/_audit_workspace/quality';out.mkdir(parents=True,exist_ok=True)
(out/'A_LINE_PARTIAL_QA.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A_LINE_PARTIAL_QA_PASS',len(checks),'checks',len(warnings),'warnings')
