"""A15 schema-only display projection contract from approved KG Schema v0.2."""
import json,re
from pathlib import Path
from datetime import datetime,timezone
B=Path(__file__).resolve().parents[2]
doc=(B/'docs/design/PESTKG_KG_SCHEMA_v0.2.md').read_text(encoding='utf-8')
def table(section,next_section):
 block=doc.split(section,1)[1].split(next_section,1)[0]
 return [[x.strip() for x in line.strip('|').split('|')] for line in block.splitlines() if line.startswith('| `')]
nodes={}
for parts in table('## 7. Core Node Types','## 8. Provenance Nodes'):
 if len(parts)>=3:
  node=parts[0].strip('`');priority=parts[-1].strip('` *')
  nodes[node]={'display_priority':priority,'ordinary_visible':priority!='HIDDEN_BY_DEFAULT'}
preds={}
for parts in table('## 10. Directed Edge Contract','## 11. Product Composition vs Use Context'):
 if len(parts)<6:continue
 name=parts[0].strip('`');pair=re.search(r'([A-Za-z]+)\s*->\s*([A-Za-z]+)',parts[1].replace('`',''))
 if not pair:raise RuntimeError('No directed pair '+name)
 priority=parts[-1].strip('` *')
 preds[name]={'source_type':pair.group(1),'target_type':pair.group(2),'display_priority':priority,'ordinary_visible':priority!='HIDDEN_BY_DEFAULT','provenance_required':True}
assert len(nodes)==11 and len(preds)==15,(len(nodes),len(preds))
contract={'schema_version':'PESTKG_KG_SCHEMA_v0.2','status':'SCHEMA_ONLY_NO_GRAPH_DATA','generated_at':datetime.now(timezone.utc).isoformat(),'source_contract':'docs/design/PESTKG_KG_SCHEMA_v0.2.md','canonical_input_required':True,'full_research_kg_input_required':True,'never_independent_fact_source':True,'node_types':nodes,'predicates':preds,'hidden_node_types':['Source','SourceSnapshot','Evidence','IdentityDecision'],'side_table_concepts_not_required_as_nodes':['Name','ExternalIdentifier','RelationshipAssertion'],'node_display_fields':['node_id','node_type','display_label','display_label_zh','display_label_en','jurisdiction_id','entity_status','short_summary','display_priority'],'edge_display_fields':['edge_id','predicate','assertion_status','origin','provenance_detail_ref'],'progressive_expansion':{'deterministic_cursor_required':True,'has_more_required':True,'numeric_node_edge_depth_limits':'PROVISIONAL_UNTIL_REAL_DEGREE_PROFILE'},'identity_visibility_rule':'Only evidence-approved EXACT_CHEMICAL_IDENTITY eligible for ordinary display; candidate and lexical links research-only.'}
out=B/'dataset/display';out.mkdir(parents=True,exist_ok=True)
(out/'A15_PROJECTION_CONTRACT.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(B/'docs/audits/A15_DISPLAY_PROJECTION_STATUS.md').write_text(f'''# A15 Display Graph Projection Assets — Schema Contract Only\n\n**KG Schema:** v0.2. **Status:** PARTIAL_SCHEMA_ONLY; no Display Graph data built because A13 Full Research KG is not available.\n\n`dataset/display/A15_PROJECTION_CONTRACT.json` records **{len(nodes)}** business node types and **{len(preds)}** directed predicates with their approved priority and endpoint types. Internal provenance/governance nodes and candidate/lexical identity edges are hidden by default. The contract requires canonical and Full Research KG inputs and cannot invent facts. Numerical expansion limits remain provisional pending real graph degree profiling.\n\nNo frontend code or second fact store was created.\n''',encoding='utf-8')
print('A15_SCHEMA_CONTRACT_DONE',len(nodes),len(preds))
