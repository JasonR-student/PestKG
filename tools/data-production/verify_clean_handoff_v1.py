"""Verify the completed clean handoff without rebuilding or modifying it."""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow.compute as pc
B=Path(__file__).resolve().parents[2]
D=B/'delivery/PestKG_A_Data_Release_v1.0'
assert D.is_dir()
M=json.loads((D/'metadata/manifest.json').read_text(encoding='utf-8'))
KG=json.loads((B/'dataset/kg/v1_0/A13_KG_MANIFEST.json').read_text(encoding='utf-8'))
QA=json.loads((B/'dataset/_audit_workspace/quality/A14_KG_QA.json').read_text(encoding='utf-8'))
def h(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
paths={x['path'] for x in M['files']}|{'metadata/manifest.json','metadata/SHA256SUMS.txt'}
actual={p.relative_to(D).as_posix() for p in D.rglob('*') if p.is_file()}
assert paths==actual and len(paths)==13
for x in M['files']:
 p=D/x['path']
 assert p.stat().st_size==x['size_bytes'] and h(p)==x['sha256']
 if 'row_count' in x:
  pf=pq.ParquetFile(p);assert pf.metadata.num_rows==x['row_count']
  if x['row_count']:next(pf.iter_batches(batch_size=1))
for line in (D/'metadata/SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
 sha,path=line.split('  ',1);assert h(D/path)==sha
assert h(D/'kg/nodes.parquet')==KG['files']['nodes']['sha256']
assert h(D/'kg/edges.parquet')==KG['files']['edges']['sha256'] and QA['status']=='PASS'
text=(D/'README.md').read_text(encoding='utf-8')
assert M['release_type']=='INTERNAL_RESEARCH_RELEASE' and 'BLOCKED_BY_RIGHTS_REVIEW' in text
for metric in ('canonical_entities','registrations','registration_uses','kg_nodes','kg_edges'):
 assert f"{M['row_counts'][metric]:,}" in text
for p in D.rglob('*'):
 if p.is_file() and p.suffix in ('.md','.json','.txt'):
  t=p.read_text(encoding='utf-8')
  assert not re.search(r'(?i)[FC]:\\(?:05_project|Users)\\',t),p
  assert not re.search(r'(?i)(?:api[_-]?key|token|password)\s*[:=]\s*[A-Za-z0-9_-]{12,}',t),p
for parquet in D.rglob('*.parquet'):
 for batch in pq.ParquetFile(parquet).iter_batches(batch_size=65536):
  for arr in batch.columns:
   for marker in (r'F:\05_project',r'C:\Users'):
    assert not pc.any(pc.match_substring(arr,marker)).as_py(),(parquet,marker)
   assert not pc.any(pc.match_substring_regex(arr,r'(?i)(?:api[_-]?key|token|password)\s*[:=]\s*[A-Za-z0-9_-]{12,}')).as_py(),parquet
assert len(list(D.rglob('*.parquet')))==7
assert not any(p.suffix in ('.rar','.csv','.log','.py') or 'incomplete' in p.name.lower() for p in D.rglob('*') if p.is_file())
out={'status':'PASS','release_name':M['release_name'],'release_type':M['release_type'],'delivery_path':str(D),'file_count':len(actual),'parquet_count':7,'checks':['manifest_file_set','sha256_all','parquet_metadata_and_first_row','row_count_manifest','kg_endpoint_qa_and_file_identity','readme_counts','no_absolute_machine_paths_in_text_and_parquet','no_secret_patterns_in_text_and_parquet','no_raw_or_temporary_files'],'checked_at':datetime.now(timezone.utc).isoformat()}
(B/'dataset/_audit_workspace/quality/A20_CLEAN_HANDOFF_QA.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A20_CLEAN_HANDOFF_PASS',len(actual),flush=True)

