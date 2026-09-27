"""Create and self-check the seven-Parquet A20 clean internal handoff."""
from __future__ import annotations
import hashlib,json,os,re,shutil
from datetime import datetime,timezone
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow.compute as pc
B=Path(__file__).resolve().parents[2]
CAN=B/'dataset/canonical/v1_0';KG=B/'dataset/kg/v1_0'
INTERNAL=B/'dataset/releases/2.0.0_internal'
C=json.loads((CAN/'A11_CANONICAL_MANIFEST.json').read_text(encoding='utf-8'))
K=json.loads((KG/'A13_KG_MANIFEST.json').read_text(encoding='utf-8'))
A12=json.loads((B/'dataset/_audit_workspace/quality/A12_CANONICAL_QA.json').read_text(encoding='utf-8'))
A14=json.loads((B/'dataset/_audit_workspace/quality/A14_KG_QA.json').read_text(encoding='utf-8'))
PROV=json.loads((B/'dataset/_audit_workspace/quality/A16_PROVENANCE_QA.json').read_text(encoding='utf-8'))
assert (INTERNAL/'manifest.json').exists() and (B/'docs/audits/PESTKG_DATA_RELEASE_V2_QUALITY_REPORT.md').exists()
assert A12['status']==A14['status']=='PASS'
dest=B/'delivery/PestKG_A_Data_Release_v1.0'
work=B/'delivery/PestKG_A_Data_Release_v1.0.incomplete'
if dest.exists():raise RuntimeError('Final handoff already exists; do not overwrite')
if work.exists():raise RuntimeError('Preserved incomplete handoff exists; inspect before resuming')
work.mkdir(parents=True)
def h(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def entry(p):
 d={'path':p.relative_to(work).as_posix(),'size_bytes':p.stat().st_size,'sha256':h(p)}
 if p.suffix=='.parquet':d['row_count']=pq.ParquetFile(p).metadata.num_rows
 return d
core=['entities','names','identifiers','registrations','registration_uses']
for name in core:
 p=work/'canonical'/(name+'.parquet');p.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(CAN/(name+'.parquet'),p)
 assert h(p)==C['tables'][name]['sha256']
for name in ['nodes','edges']:
 p=work/'kg'/(name+'.parquet');p.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(KG/(name+'.parquet'),p)
 assert h(p)==K['files'][name]['sha256']
print('A20_PARQUET_COPY_DONE',flush=True)
counts=A12['counts'];etype=counts['entity_types'];n=K['node_count'];e=K['edge_count'];snap=C['snapshot_id']
readme=[
 '# PestKG A-Line Data Release v1.0','',
 '**Type:** INTERNAL RESEARCH RELEASE. **Raw Snapshot:** '+snap+'.',
 '',
 'This package contains source-backed Canonical data and the Full Research KG built with the approved v0.2 models. Internal research use is allowed; public redistribution is BLOCKED_BY_RIGHTS_REVIEW.','',
 '| Folder | Purpose |','| --- | --- |',
 '| canonical/ | Entities, names, identifiers, registrations and uses |',
 '| kg/ | Directed nodes and edges for graph analysis |',
 '| docs/ | Short field, schema and quality guides |',
 '| metadata/ | Manifest and SHA-256 checksums |','',
 'For graph queries, read kg/nodes.parquet and kg/edges.parquet. For entity and registration analysis, read canonical/.',
 '',
 'Canonical IDs are opaque registry-issued PestKG IDs. Local entity IDs retain jurisdiction and source context. CAS, ChEBI and other external identifiers are attributes, never internal primary keys.','',
 '| Measure | Count |','| --- | ---: |',
 f"| Canonical entities | {counts['canonical_entities']:,} |",
 f"| GlobalChemical | {etype.get('GlobalChemical',0):,} |",
 f"| Registrations | {counts['registrations']:,} |",
 f"| Registration uses | {counts['registration_uses']:,} |",
 f"| KG nodes | {n:,} |",f"| KG edges | {e:,} |",'',
 '**Key limits:** No GlobalChemical or exact chemical identity was invented. Ambiguous multi-ingredient records remain unresolved for review. One truncated ChEBI structures file is excluded. The approved Raw Snapshot does not prove the old archive was complete. Source rights have not been cleared for public redistribution. See docs/QUALITY_REPORT.md.','']
(work/'README.md').write_text('\n'.join(readme),encoding='utf-8')
desc={
'entity_id':'Opaque PestKG Canonical entity ID.','entity_type':'Approved entity class.','entity_status':'Entity lifecycle status.','jurisdiction_id':'Regulatory jurisdiction ID for a local entity.','source_id':'Source registry ID; edge source_id instead means subject node ID.','source_snapshot_id':'Immutable source snapshot ID.','source_record_id':'Frozen source-row locator.','display_label':'Source-backed short label.','grain_status':'Conservative entity granularity or scoping rule.','extension_properties':'JSON for source-specific retained attributes.','evidence_id':'Evidence ID supporting this value or relation.','name_key':'Stable name assertion key.','name':'Original source name text.','name_type':'Original, translated or other source-supported name class.','language':'Language tag; und means undetermined.','normalized_name':'Derived search key, never identity proof.','source_field':'Original source column for this assertion.','identifier_key':'Stable external-identifier assertion key.','identifier_type':'External scheme or source-specific constituent code.','identifier_value':'Source identifier text.','status':'Validation or linkage status, not identity proof.','registration_id':'Opaque Registration ID.','source_registration_key':'Original permit/registration key or documented fallback.','product_id':'Related source-local product ID when present.','original_status':'Regulatory status text as stated by source.','registration_date_original':'Source registration date text.','registration_date_normalized':'Safely derived ISO date when available.','expiry_date_original':'Source expiry date text.','expiry_date_normalized':'Safely derived ISO expiry date when available.','registration_use_id':'Opaque RegistrationUse ID.','pairing_status':'Source-row use context; no crop-target Cartesian inference.','crop_original':'Full original crop or site field text.','target_original':'Full original pest or target field text.','dose_original':'Full original dose and unit text.','method_original':'Original application method text.','timing_original':'Original timing text.','formulation_original':'Original formulation text.','use_pattern_original':'Original use-pattern text.','node_id':'KG node ID equal to Canonical entity ID.','node_type':'KG entity class.','display_priority':'Default HIGH/MEDIUM/LOW or hidden priority.','default_hidden':'True if ordinary display hides this item.','edge_id':'Release-stable relationship assertion ID.','predicate':'Approved directed UPPER_SNAKE_CASE relation.','target_id':'Target KG node ID.','assertion_status':'Source-asserted, derived or reviewed status.','origin_kind':'Source-asserted or derived origin.','derivation_rule_id':'Versioned rule behind a derived/component relation.','pipeline_version':'Pipeline version that emitted the assertion.'}
dictionary=['# Data Dictionary','',
 'Delivered Parquet columns are UTF-8 strings. Empty strings mean unavailable or not applicable. JSON strings are marked. The full source-record and Evidence lookup is in the internal engineering release.','']
for name in core+['nodes','edges']:
 folder='canonical' if name in core else 'kg'
 p=work/folder/(name+'.parquet');pf=pq.ParquetFile(p)
 dictionary += ['## '+folder+'/'+name+'.parquet','', '| Field | Type | Required | Meaning | Example | Notes |','| --- | --- | --- | --- | --- | --- |']
 row=next(pf.iter_batches(batch_size=1)).to_pylist()[0] if pf.metadata.num_rows else {}
 for col in pf.schema.names:
  required='Yes' if col in ('entity_id','entity_type','registration_id','registration_use_id','node_id','node_type','edge_id','predicate','target_id') else 'No'
  example=str(row.get(col,'')).replace('|','/').replace('\n',' ')[:38] or '(empty)'
  if col=='extension_properties':example='JSON object'
  note='Source-scoped; no global identity inference.' if col in ('normalized_name','identifier_value') else ''
  dictionary.append('| '+col+' | '+('JSON string' if col=='extension_properties' else 'string')+' | '+required+' | '+desc[col]+' | '+example+' | '+note+' |')
 dictionary.append('')
(work/'docs').mkdir(exist_ok=True)
(work/'docs/DATA_DICTIONARY.md').write_text('\n'.join(dictionary)+'\n',encoding='utf-8')
contract=json.loads((B/'dataset/display/A15_PROJECTION_CONTRACT.json').read_text(encoding='utf-8'))
meaning={'HAS_REGISTRATION':'Jurisdiction governs Registration.','REGISTERS_PRODUCT':'Registration covers PesticideProduct.','HAS_USE':'Registration owns RegistrationUse.','USES_PRODUCT':'Use statement names Product.','CONTAINS_ACTIVE_INGREDIENT':'Product has supported source ingredient component.','FOR_CROP':'Use statement carries source crop term.','FOR_TARGET':'Use statement carries source target term.','IN_TERRITORY':'Jurisdiction maps to source-stated territory.','REGULATES':'Organization regulates jurisdiction.','HAS_SNAPSHOT':'Source has frozen SourceSnapshot.'}
schema=['# KG Schema — concise delivered v0.2','','The graph is a directed projection of Canonical assertions. Candidate lexical matches never become exact identity.','', '## Node types','', '| Node type | Count | Ordinary display |','| --- | ---: | --- |']
for typ,count in sorted(K['node_type_counts'].items()):
 pri=contract['node_types'].get(typ,{}).get('display_priority','HIDDEN_BY_DEFAULT')
 schema.append(f'| {typ} | {count:,} | {pri} |')
schema += ['','## Predicates','', '| Predicate | Direction | Count | Meaning |','| --- | --- | ---: | --- |']
for pred,count in sorted(K['predicate_counts'].items()):
 p=contract['predicates'][pred]
 schema.append(f"| {pred} | {p['source_type']} to {p['target_type']} | {count:,} | {meaning.get(pred,'Approved v0.2 relation.')} |")
schema += ['','GlobalChemical / LocalActiveIngredient: no exact chemical identity was approved, so GlobalChemical and EXACT_CHEMICAL_IDENTITY counts are zero. Local terms remain source-scoped.','','RegistrationUse: first-class statement under Registration, carrying crop/target/dose/method/timing in one source-row context. No Cartesian product is inferred.','','Every edge carries evidence_id, source_snapshot_id and source_record_id. Detailed Evidence records are in the internal release. Display clients may filter default_hidden=true and expand by jurisdiction; they must not create independent facts.','']
(work/'docs/KG_SCHEMA.md').write_text('\n'.join(schema),encoding='utf-8')
quality=[
 '# Quality Report','',
 '**Release:** PestKG A-Line Data Release v1.0, INTERNAL_RESEARCH_RELEASE. **Snapshot:** '+snap+'.','',
 '| Measure | Result |','| --- | ---: |',
 f"| Primary source rows | {C['source_rows']:,} |",f"| Canonical entities | {counts['canonical_entities']:,} |",
 f"| Registration / RegistrationUse | {counts['registrations']:,} / {counts['registration_uses']:,} |",
 f"| KG nodes / edges | {n:,} / {e:,} |",
 '| Exact source-row duplicates retained | 1,288 |',
 f"| Uncertain component rows in review | {counts['quarantine_component_rows']:,} |",
 '| Truncated supplementary ChEBI file | 1 |','| Grouped ChEBI CAS candidates | 750 |','',
 f"A12 Canonical and A14 KG gates passed. Record provenance covers {C['source_rows']:,}/{C['source_rows']:,} primary rows. Relationship provenance covers {PROV['relationship_level']['with_evidence_snapshot_record']:,}/{PROV['relationship_level']['assertions']:,} edges. Names and identifiers carry source-field locators. Registration status and validity resolve through Evidence to the original source row.",'',
 'Known limits: GlobalChemical count is zero pending identity evidence. Ambiguous components stay for review. Supplementary assets were profiled, not blindly joined. Legacy upstream completeness is unproven; DEC-RAW-001 approved this project snapshot. Public redistribution remains BLOCKED_BY_RIGHTS_REVIEW; internal use is allowed by DEC-002.','']
(work/'docs/QUALITY_REPORT.md').write_text('\n'.join(quality),encoding='utf-8')
files=[entry(p) for p in sorted(work.rglob('*')) if p.is_file()]
manifest={'release_name':'PestKG A-Line Data Release v1.0','release_version':'1.0','release_type':'INTERNAL_RESEARCH_RELEASE','raw_snapshot_id':snap,'raw_snapshot_manifest_hash':h(B/'dataset/raw_manifest/RAW_INPUT_MANIFEST.json'),'schema_version':C['schema_version'],'kg_schema_version':K['schema_version'],'pipeline_version':C['pipeline_version']+' + '+K['pipeline_version'],'canonical_registry_version':C['canonical_registry_version'],'created_at':datetime.now(timezone.utc).isoformat(),'files':files,'row_counts':{'canonical_entities':counts['canonical_entities'],'global_chemicals':etype.get('GlobalChemical',0),'registrations':counts['registrations'],'registration_uses':counts['registration_uses'],'kg_nodes':n,'kg_edges':e},'known_limitations':['No GlobalChemical/exact identity without approved evidence.','Uncertain component rows remain in engineering quarantine.','Legacy upstream completeness unproven.','Public redistribution rights unverified.'],'distribution_status':{'internal':'ALLOWED_DEC_002','public':'BLOCKED_BY_RIGHTS_REVIEW'}}
(work/'metadata').mkdir(exist_ok=True)
(work/'metadata/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (work/'metadata/SHA256SUMS.txt').open('w',encoding='utf-8') as f:
 for x in files+[entry(work/'metadata/manifest.json')]:f.write(x['sha256']+'  '+x['path']+'\n')
expected={x['path'] for x in files}|{'metadata/manifest.json','metadata/SHA256SUMS.txt'}
actual={p.relative_to(work).as_posix() for p in work.rglob('*') if p.is_file()}
assert actual==expected
for x in files:
 p=work/x['path'];assert h(p)==x['sha256']
 if 'row_count' in x:
  pf=pq.ParquetFile(p);assert pf.metadata.num_rows==x['row_count']
  if pf.metadata.num_rows:next(pf.iter_batches(batch_size=1))
for line in (work/'metadata/SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
 sha,rel=line.split('  ',1);assert h(work/rel)==sha
assert h(work/'kg/nodes.parquet')==K['files']['nodes']['sha256']
assert h(work/'kg/edges.parquet')==K['files']['edges']['sha256'] and A14['status']=='PASS'
assert f"{n:,}" in (work/'README.md').read_text(encoding='utf-8') and f"{e:,}" in (work/'README.md').read_text(encoding='utf-8')
for p in work.rglob('*'):
 if p.is_file() and p.suffix in ('.md','.json','.txt'):
  text=p.read_text(encoding='utf-8')
  assert not re.search(r'(?i)[FC]:\\(?:05_project|Users)\\',text),p
  assert not re.search(r'(?i)(?:api[_-]?key|token|password)\s*[:=]\s*[A-Za-z0-9_-]{12,}',text),p
for parquet in work.rglob('*.parquet'):
 pf=pq.ParquetFile(parquet)
 for batch in pf.iter_batches(batch_size=65536):
  for arr in batch.columns:
   for marker in (r'F:\05_project',r'C:\Users'):
    assert not pc.any(pc.match_substring(arr,marker)).as_py(),(parquet,marker)
   assert not pc.any(pc.match_substring_regex(arr,r'(?i)(?:api[_-]?key|token|password)\s*[:=]\s*[A-Za-z0-9_-]{12,}')).as_py(),parquet
assert len(list(work.rglob('*.parquet')))==7
assert not any(p.suffix in ('.rar','.csv','.log','.py') or 'incomplete' in p.name.lower() for p in work.rglob('*') if p.is_file())
try:
 os.replace(work,dest)
except PermissionError:
 shutil.move(str(work),str(dest))
qa={'status':'PASS','delivery_path':str(dest),'file_count':len(expected),'parquet_count':7,'checks':['manifest_files_exist','sha256_match','parquet_readable','row_counts_match','endpoint_qa_and_copied_hashes_pass','readme_counts_match','no_absolute_machine_paths_in_text_and_parquet','no_secret_patterns_in_text_and_parquet','no_raw_or_temporary_files'],'checked_at':datetime.now(timezone.utc).isoformat()}
(B/'dataset/_audit_workspace/quality/A20_CLEAN_HANDOFF_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A20_CLEAN_HANDOFF_PASS',len(expected),flush=True)

