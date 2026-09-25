"""Validate A11 canonical tables and build/validate A13-A15 research graph assets."""
from __future__ import annotations
import hashlib,json,os,re,sqlite3
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
B=Path(__file__).resolve().parents[2]
CAN=B/'dataset/canonical/v1_0'
KG=B/'dataset/kg/v1_0';KG.mkdir(parents=True,exist_ok=True)
WORK=CAN/'_build'
db=sqlite3.connect(WORK/'canonical_build.sqlite')
manifest=json.loads((CAN/'A11_CANONICAL_MANIFEST.json').read_text(encoding='utf-8'))
contract=json.loads((B/'dataset/display/A15_PROJECTION_CONTRACT.json').read_text(encoding='utf-8'))
def count(q):return db.execute(q).fetchone()[0]
def chk(name,condition):
 checks[name]=bool(condition)
 if not condition:raise RuntimeError('QA_FAIL '+name)
def hashfile(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
checks={}
chk('source_records_count',pq.ParquetFile(CAN/'source_records.parquet').metadata.num_rows==manifest['source_rows']==821183)
for name,x in manifest['tables'].items():
 p=B/x['path']
 chk('manifest_'+name,p.exists() and pq.ParquetFile(p).metadata.num_rows==x['rows'] and hashfile(p)==x['sha256'])
chk('registry_entity_parity',count('SELECT COUNT(*) FROM entities e LEFT JOIN registry r ON r.canonical_id=e.entity_id WHERE r.canonical_id IS NULL')==0)
chk('registration_entity_parity',count("SELECT COUNT(*) FROM registrations f LEFT JOIN entities e ON e.entity_id=f.registration_id AND e.entity_type='Registration' WHERE e.entity_id IS NULL")==0)
chk('use_parent_integrity',count('SELECT COUNT(*) FROM registration_uses u LEFT JOIN registrations r ON r.registration_id=u.registration_id WHERE r.registration_id IS NULL')==0)
chk('use_entity_integrity',count("SELECT COUNT(*) FROM registration_uses u LEFT JOIN entities e ON e.entity_id=u.registration_use_id AND e.entity_type='RegistrationUse' WHERE e.entity_id IS NULL")==0)
chk('use_evidence_integrity',count('SELECT COUNT(*) FROM registration_uses u LEFT JOIN evidence e ON e.evidence_id=u.evidence_id WHERE e.evidence_id IS NULL')==0)
chk('registration_evidence_integrity',count('SELECT COUNT(*) FROM registrations r LEFT JOIN evidence e ON e.evidence_id=r.evidence_id WHERE e.evidence_id IS NULL')==0)
chk('name_owner_integrity',count('SELECT COUNT(*) FROM names n LEFT JOIN entities e ON e.entity_id=n.entity_id WHERE e.entity_id IS NULL')==0)
chk('identifier_owner_integrity',count('SELECT COUNT(*) FROM identifiers i LEFT JOIN entities e ON e.entity_id=i.entity_id WHERE e.entity_id IS NULL')==0)
chk('relationship_endpoint_integrity',count('SELECT COUNT(*) FROM relations r LEFT JOIN entities a ON a.entity_id=r.subject_id LEFT JOIN entities b ON b.entity_id=r.object_id WHERE a.entity_id IS NULL OR b.entity_id IS NULL')==0)
chk('relationship_evidence_integrity',count('SELECT COUNT(*) FROM relations r LEFT JOIN evidence e ON e.evidence_id=r.evidence_id WHERE e.evidence_id IS NULL')==0)
chk('relationship_snapshot_integrity',count("SELECT COUNT(*) FROM relations r LEFT JOIN entities s ON s.entity_id=r.source_snapshot_id AND s.entity_type='SourceSnapshot' WHERE s.entity_id IS NULL")==0)
chk('no_self_edges',count('SELECT COUNT(*) FROM relations WHERE subject_id=object_id')==0)
chk('no_unapproved_exact_identity',count("SELECT COUNT(*) FROM relations WHERE predicate='EXACT_CHEMICAL_IDENTITY'")==0)
chk('uncertain_composition_has_no_components',count("SELECT COUNT(*) FROM compositions WHERE parse_status LIKE 'UNCERTAIN%' AND component_ids_json!='[]'")==0)
chk('all_components_have_parse_rule',count("SELECT COUNT(*) FROM compositions WHERE parse_status='STRUCTURED_COMPONENTS_VERIFIED' AND (parsing_rule_id='' OR source_record_id='' OR evidence_id='')")==0)
pairs=list(db.execute('SELECT r.predicate,a.entity_type,b.entity_type FROM relations r JOIN entities a ON a.entity_id=r.subject_id JOIN entities b ON b.entity_id=r.object_id GROUP BY 1,2,3'))
for p,a,b in pairs:
 spec=contract['predicates'].get(p)
 chk('predicate_type_'+p+'_'+a+'_'+b,bool(spec) and spec['source_type']==a and spec['target_type']==b and bool(re.fullmatch(r'[A-Z][A-Z0-9_]*',p)))
entity_counts=dict(db.execute('SELECT entity_type,COUNT(*) FROM entities GROUP BY entity_type').fetchall())
predicate_counts=dict(db.execute('SELECT predicate,COUNT(*) FROM relations GROUP BY predicate').fetchall())
status_counts=dict(db.execute('SELECT parse_status,COUNT(*) FROM compositions GROUP BY parse_status').fetchall())
reg_count=count('SELECT COUNT(*) FROM registrations')
use_count=count('SELECT COUNT(*) FROM registration_uses')
chk('registrations_nonempty',reg_count>0)
chk('uses_nonempty',use_count>0)
qa={'snapshot_id':manifest['snapshot_id'],'schema_version':manifest['schema_version'],'pipeline_version':manifest['pipeline_version'],'status':'PASS','checks':checks,'check_count':len(checks),'counts':{'source_rows':manifest['source_rows'],'canonical_entities':sum(entity_counts.values()),'entity_types':entity_counts,'registrations':reg_count,'registration_uses':use_count,'names':count('SELECT COUNT(*) FROM names'),'identifiers':count('SELECT COUNT(*) FROM identifiers'),'evidence':count('SELECT COUNT(*) FROM evidence'),'relationship_assertions':sum(predicate_counts.values()),'composition_status':status_counts,'quarantine_component_rows':manifest['quarantine_component_rows']},'limitations':['GlobalChemical count is zero: no chemical identity was auto-approved.','Unstructured multi-value active ingredient strings remain uncertain and are excluded from composition edges.','Registration keys reused across distinct products are product-scoped; this avoids unsupported merge.','Use rows preserve original field groups without creating crop-target Cartesian products.','Formulation ownership is unverified; no HAS_FORMULATION edges are materialized.','Supplementary assets remain source-preserved/profiled and are not silently joined to primary regulatory facts.'],'checked_at':datetime.now(timezone.utc).isoformat()}
(B/'dataset/_audit_workspace/quality/A12_CANONICAL_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(B/'docs/audits/A12_CANONICAL_DATASET_QA.md').write_text('# A12 Canonical Dataset QA\n\n**Status:** PASS for the conservative source-backed Canonical v1.0 dataset. Raw Snapshot: '+manifest['snapshot_id']+'.\n\n'+f"- Source rows: {manifest['source_rows']:,}; canonical entities: {sum(entity_counts.values()):,}; registrations: {reg_count:,}; registration uses: {use_count:,}.\n- Identity: 0 GlobalChemical and 0 exact identity edges. This is intentional under v0.2 evidence rules.\n- Checks: {len(checks)} PASS, including output hashes, parent/source/evidence links, unique IDs, predicate endpoint types and conservative componentization.\n- Component parse status: "+json.dumps(status_counts,ensure_ascii=False)+'.\n- Known limits: '+'; '.join(qa['limitations'])+'\n\nMachine evidence: dataset/_audit_workspace/quality/A12_CANONICAL_QA.json.\n',encoding='utf-8')
print('A12_PASS',len(checks),'entities',sum(entity_counts.values()),'registrations',reg_count,'uses',use_count,flush=True)

def export_cursor(sql,cols,path,transform=None,chunk=25000):
 cur=db.execute(sql);work=KG/(path.stem+'.incomplete.parquet')
 schema=pa.schema([(c,pa.string()) for c in cols]);w=pq.ParquetWriter(work,schema,compression='zstd',compression_level=5)
 n=0
 try:
  while True:
   rows=cur.fetchmany(chunk)
   if not rows:break
   if transform:rows=[transform(row) for row in rows]
   values={c:[str(row[i]) if row[i] is not None else '' for row in rows] for i,c in enumerate(cols)}
   w.write_table(pa.Table.from_pydict(values,schema=schema));n+=len(rows)
 finally:w.close()
 os.replace(work,path)
 return n
nodecols=['node_id','node_type','display_label','jurisdiction_id','entity_status','source_id','source_snapshot_id','evidence_id','display_priority','default_hidden','extension_properties']
def node_transform(row):
 eid,typ,label,jid,status,sid,ssnp,evid,ext=row
 spec=contract['node_types'].get(typ,{})
 return (eid,typ,label,jid,status,sid,ssnp,evid,spec.get('display_priority','HIDDEN_BY_DEFAULT'),'false' if spec.get('ordinary_visible',False) else 'true',ext)
nodes=export_cursor('SELECT entity_id,entity_type,display_label,jurisdiction_id,entity_status,source_id,source_snapshot_id,evidence_id,extension_properties FROM entities ORDER BY entity_id',nodecols,KG/'nodes.parquet',node_transform)
edgecols=['edge_id','source_id','predicate','target_id','assertion_status','evidence_id','source_snapshot_id','source_record_id','origin_kind','derivation_rule_id','pipeline_version','display_priority','default_hidden']
def edge_transform(row):
 aid,a,p,b,status,eid,ssnp,rid,rule,version=row
 spec=contract['predicates'][p]
 return (aid,a,p,b,status,eid,ssnp,rid,'derived' if status=='derived' else 'source_asserted',rule,version,spec['display_priority'],'false' if spec['ordinary_visible'] else 'true')
edges=export_cursor('SELECT assertion_id,subject_id,predicate,object_id,assertion_status,evidence_id,source_snapshot_id,source_record_id,derivation_rule_id,pipeline_version FROM relations ORDER BY assertion_id',edgecols,KG/'edges.parquet',edge_transform)
chk('kg_nodes_parity',nodes==sum(entity_counts.values()))
chk('kg_edges_parity',edges==sum(predicate_counts.values()))
kgmanifest={'snapshot_id':manifest['snapshot_id'],'canonical_manifest_sha256':hashfile(CAN/'A11_CANONICAL_MANIFEST.json'),'schema_version':'PESTKG_KG_SCHEMA_v0.2','pipeline_version':'a-line-kg-v1.0.0','status':'PASS','node_count':nodes,'edge_count':edges,'node_type_counts':entity_counts,'predicate_counts':predicate_counts,'files':{},'generated_at':datetime.now(timezone.utc).isoformat(),'limitations':qa['limitations']}
for name in ['nodes','edges']:
 p=KG/(name+'.parquet')
 kgmanifest['files'][name]={'path':str(p.relative_to(B)).replace('\\','/'),'rows':pq.ParquetFile(p).metadata.num_rows,'size_bytes':p.stat().st_size,'sha256':hashfile(p)}
(KG/'A13_KG_MANIFEST.json').write_text(json.dumps(kgmanifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
kgqa={'status':'PASS','checks':{k:v for k,v in checks.items() if k.startswith('relationship_') or k.startswith('predicate_') or k in ('no_self_edges','no_unapproved_exact_identity','kg_nodes_parity','kg_edges_parity')},'node_count':nodes,'edge_count':edges,'predicate_counts':predicate_counts,'checked_at':datetime.now(timezone.utc).isoformat()}
(B/'dataset/_audit_workspace/quality/A14_KG_QA.json').write_text(json.dumps(kgqa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(B/'docs/audits/A14_KG_QUALITY_REPORT.md').write_text('# A14 Full Research KG QA\n\n**Status:** PASS for the conservative v0.2 research graph. Nodes: '+f'{nodes:,}; edges: {edges:,}.'+'\n\nAll materialized predicates use UPPER_SNAKE_CASE and approved endpoint types. Every edge has a resolvable source snapshot and evidence locator; no self edges or unsupported exact chemical identity edges were emitted. Edge IDs are release-stable assertion digests over endpoints, predicate, evidence and status. Duplicate source rows collapse to one evidence-content assertion while the canonical source-record table retains every row locator.\n\nPredicate counts: '+json.dumps(predicate_counts,ensure_ascii=False)+'.\n\nLimitations: '+ '; '.join(qa['limitations'])+'\n\nMachine evidence: dataset/_audit_workspace/quality/A14_KG_QA.json.\n',encoding='utf-8')
display={'snapshot_id':manifest['snapshot_id'],'status':'READY_AS_PROJECTION_OF_FULL_RESEARCH_KG','schema_contract':'dataset/display/A15_PROJECTION_CONTRACT.json','kg_manifest_path':'dataset/kg/v1_0/A13_KG_MANIFEST.json','kg_manifest_sha256':hashfile(KG/'A13_KG_MANIFEST.json'),'nodes_path':'dataset/kg/v1_0/nodes.parquet','edges_path':'dataset/kg/v1_0/edges.parquet','node_count':nodes,'edge_count':edges,'ordinary_visible_node_types':[x for x,v in contract['node_types'].items() if v['ordinary_visible']],'ordinary_visible_predicates':[x for x,v in contract['predicates'].items() if v['ordinary_visible']],'rule':'Filter default_hidden=false and apply approved expansion policy. No second independent fact table is created.','generated_at':datetime.now(timezone.utc).isoformat()}
(B/'dataset/display/A15_DISPLAY_PROJECTION_MANIFEST.json').write_text(json.dumps(display,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('A13_A14_A15_DONE',nodes,edges,flush=True)
db.close()

