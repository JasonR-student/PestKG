"""Map every profiled primary-source field without dropping original values."""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]
PROFILE=BASE/'dataset/_audit_workspace/profiles'
INVENTORY=json.loads((BASE/'dataset/raw_manifest/RAW_INPUT_INVENTORY.json').read_text(encoding='utf-8'))
OUT=BASE/'dataset/mappings'
OUT.mkdir(parents=True,exist_ok=True)

# Exact observed header semantics only. Unlisted headers remain source-specific assertions.
RULES={
 'LocalActiveIngredient.original_name': 'ActiveIngredient|有効成分|유효성분|주성분|有效成分|Werkzame stof(fen)|Ingredient|Active(s)|common_name',
 'LocalActiveIngredient.translated_name': 'ActiveIngredientEnglish|Active Ingredients English|有効成分英文名|有效成分英文名',
 'LocalActiveIngredient.name_evidence': 'ActiveIngredientEnglishSource|EnglishNameSource|English name source|英文名来源|英文名来源|English name source|EnglishNameSourceURL|ActiveIngredientEnglishStatus',
 'PesticideProduct.original_name': 'PesticideProduct|Product_Name|Product Name|Product_Name|農薬の名称|농약명|품목명|Middelnaam|Trade Name|brand_name|农药名称',
 'PesticideProduct.trade_name': '상표명|AlternateBrandNames',
 'Registration.source_registration_key': 'RegistrationNumber|RegistrationCode|Registration No|登録番号|등록번호|登记证号|Toelatingsnummer|MAPP_No|Product MAPP No|EPARegistrationNumber|APVMAProductNumber|permit_number',
 'Registration.original_status': 'RegistrationStatus|OfficialRegistrationStatus|OfficialRegulatoryStatus|OfficialStatus|StatusGroup|등록취소일자|등록취소목록조회|登记证状态',
 'Registration.first_registration_date_original': 'RegistrationDate|DateFirstRegistered|FirstAuthorisationDate|Date of registration|登録年月日|등록일|批准日期|approval_date|ApprovalDate',
 'Registration.expiry_date_original': 'RegistrationExpiryDate|RegistrationExpirationDate|Product Expiry Date|Expiratiedatum|valid_until|등록유효기한|登録有効期限|最新批准日期',
 'RegistrationUse.crop_original': 'Crop|crop_name|작물명|作物/场所|Crop(s) (may have different Expiry Dates)|Crop / Site / Animal|Crop / Site / UseArea|Toepassingsgebied',
 'RegistrationUse.target_original': 'Pest / Pathogen / Weed|target_name|防治对象|적용병해충|Toepassingsorganismen',
 'RegistrationUse.formulation_original': 'FormulationType|FormulationType|formulation|剂型|剤型名|제형',
 'RegistrationUse.use_pattern_original': 'UsePattern|use_pattern|UsePurpose|用途|용도|使用技术要求|Gebruik per toepassing',
 'RegistrationUse.dose_original': 'DilutionOrDosage|dosage_per_hectare|Maximum middeldosis|Maximum middeldosis per gewasseizoen|用药量（制剂量/亩）|사용량|희석배수',
 'RegistrationUse.application_method_original': 'ApplicationMethod|application_method|施用方法|사용방법|Toepassingsmethoden',
 'RegistrationUse.application_timing_original': 'ApplicationTiming|application_timing|使用적기|사용적기|Toepassingstijdstip',
 'ExternalIdentifier.CAS_original_value': 'ActiveIngredientCASNumber',
 'Source.record_url': 'SourceURL|SourceDatasetURL|SourcePortalURL|OfficialSourceURL|OfficialDetailSourceURL|SourceDatasetURL|RecordViewURL|record_url|pesticide_url|source_page|OfficialNoticeURL',
 'Jurisdiction.source_label': 'Country / Jurisdiction|SovereignCountry',
 'Jurisdiction.source_code': 'JurisdictionCode',
 'CountryOrTerritory.iso2_source': 'CountryISO2|SovereignCountryISO2',
 'CountryOrTerritory.iso3_source': 'CountryISO3',
 'RegulatoryOrganization.original_name': 'RegulatoryAgency',
}
# These source-specific aliases are mapped where identical concepts are explicit.
ALIASES={
 'ActiveIngredient':'LocalActiveIngredient.original_name',
 'ActiveIngredientEnglish':'LocalActiveIngredient.translated_name',
 'Active Ingredients English':'LocalActiveIngredient.translated_name',
 'Active(s)':'LocalActiveIngredient.original_name',
 'Ingredient':'LocalActiveIngredient.original_name',
 'PesticideProduct':'PesticideProduct.original_name',
 'Product_Name':'PesticideProduct.original_name',
 'RegistrationNumber':'Registration.source_registration_key',
 'RegistrationStatus':'Registration.original_status',
 'RegistrationDate':'Registration.first_registration_date_original',
 'RegistrationExpiryDate':'Registration.expiry_date_original',
 'FormulationType':'RegistrationUse.formulation_original',
 'Crop':'RegistrationUse.crop_original',
 'Pest / Pathogen / Weed':'RegistrationUse.target_original',
 'UsePattern':'RegistrationUse.use_pattern_original',
 'SourceURL':'Source.record_url',
}
# Explicitly avoid false semantic equivalence for broad source words.
EXCLUDE={'common_name','最新批准日期','registration_type','UsePattern','用途','용도'}
lookup={}
for target, pipe in RULES.items():
 for name in pipe.split('|'):
  if name and name not in EXCLUDE and name not in lookup: lookup[name]=target
lookup.update(ALIASES)
# Source-specific true aliases, each inspected in the observed profile headers.
lookup.update({
 '农药名称':'PesticideProduct.original_name','農薬の名称':'PesticideProduct.original_name','품목명':'PesticideProduct.original_name','Middelnaam':'PesticideProduct.original_name','Trade Name':'PesticideProduct.original_name','brand_name':'PesticideProduct.original_name',
 '登记证号':'Registration.source_registration_key','登録番号':'Registration.source_registration_key','등록번호':'Registration.source_registration_key','Toelatingsnummer':'Registration.source_registration_key','Registration No':'Registration.source_registration_key','EPARegistrationNumber':'Registration.source_registration_key','APVMAProductNumber':'Registration.source_registration_key','permit_number':'Registration.source_registration_key',
 '有効成分':'LocalActiveIngredient.original_name','有效成分':'LocalActiveIngredient.original_name','주성분':'LocalActiveIngredient.original_name','Werkzame stof(fen)':'LocalActiveIngredient.original_name',
 '有効成分英文名':'LocalActiveIngredient.translated_name','有效成分英文名':'LocalActiveIngredient.translated_name',
 '作物/场所':'RegistrationUse.crop_original','작물명':'RegistrationUse.crop_original','Crop(s) (may have different Expiry Dates)':'RegistrationUse.crop_original','Toepassingsgebied':'RegistrationUse.crop_original','crop_name':'RegistrationUse.crop_original',
 '防治对象':'RegistrationUse.target_original','적용병해충':'RegistrationUse.target_original','Toepassingsorganismen':'RegistrationUse.target_original','target_name':'RegistrationUse.target_original',
 '剂型':'RegistrationUse.formulation_original','剤型名':'RegistrationUse.formulation_original','제형':'RegistrationUse.formulation_original','formulation':'RegistrationUse.formulation_original',
 '注册日期':'Registration.first_registration_date_original','登録年月日':'Registration.first_registration_date_original','등록일':'Registration.first_registration_date_original','Date of registration':'Registration.first_registration_date_original','批准日期':'Registration.first_registration_date_original','approval_date':'Registration.first_registration_date_original',
 '登録有効期限':'Registration.expiry_date_original','등록유효기한':'Registration.expiry_date_original','Expiratiedatum':'Registration.expiry_date_original','valid_until':'Registration.expiry_date_original','Product Expiry Date':'Registration.expiry_date_original',
 'ActiveIngredientCASNumber':'ExternalIdentifier.CAS_original_value',
})
rows=[]
for item in INVENTORY['primary_source_files']:
 p=json.loads((PROFILE/f"{item['jurisdiction']}_{item['source']}.json").read_text(encoding='utf-8'))
 for c in p['columns']:
  field=c['field']
  target=lookup.get(field)
  if target:
   entity,canonical=target.split('.',1)
   classification='CORE'
   confidence='HIGH'
   rule='PRESERVE_ORIGINAL_TEXT; DERIVE_VALIDATED_VALUE_ONLY'
   notes='Source field semantics explicit; nullability is source-specific, not globally required.'
  else:
   entity='SourceFieldAssertion'
   canonical='extension_properties.'+field
   classification='EXTENSION'
   confidence='SOURCE_SPECIFIC'
   rule='PRESERVE_ORIGINAL_TEXT_AND_SOURCE_FIELD_NAME'
   notes='Source-specific or ambiguous field; retained without cross-source semantic assertion.'
  rows.append({'source':item['source'],'jurisdiction':item['jurisdiction'],'source_table':item['relative_path'],'source_field':field,'canonical_entity':entity,'canonical_field':canonical,'transform_rule':rule,'required':'NO_GLOBAL_REQUIREMENT','confidence':confidence,'notes':notes,'classification':classification,'nonempty_count':c['nonempty_count'],'row_count':p['row_count']})
if len(rows)!=sum(json.loads((PROFILE/f"{x['jurisdiction']}_{x['source']}.json").read_text(encoding='utf-8'))['column_count'] for x in INVENTORY['primary_source_files']):
 raise RuntimeError('Field count mismatch')
map_cols=['source','jurisdiction','source_table','source_field','canonical_entity','canonical_field','transform_rule','required','confidence','notes']
with (OUT/'source_field_mapping.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=map_cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
class_cols=['snapshot_id','source','jurisdiction','source_table','source_field','classification','canonical_entity','canonical_field','reason','nonempty_count','row_count']
with (OUT/'DATA_FIELD_CLASSIFICATION.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=class_cols);w.writeheader()
 for r in rows:
  w.writerow({'snapshot_id':INVENTORY['snapshot_id'],**{k:r[k] for k in ['source','jurisdiction','source_table','source_field','classification','canonical_entity','canonical_field','nonempty_count','row_count']},'reason':'Approved v0.2 concept and explicit source header' if r['classification']=='CORE' else 'Preserve source-specific/ambiguous original value without lossy semantic inference'})
counts=Counter(r['classification'] for r in rows)
report=f'''# A4 Source Field Mapping and A5 Classification

**Baseline:** {INVENTORY['snapshot_id']}. **Scope:** all observed columns of 12 primary official CSVs. **Status:** A4 and A5 DONE for these primary sources. Supplementary assets retain separate A3 profiles and require field-level integration when their grain is established.

- Source fields: {len(rows)}; CORE {counts['CORE']}; EXTENSION {counts['EXTENSION']}; RAW_ONLY 0; IGNORED_WITH_REASON 0.
- Every field is retained. CORE means a direct v0.2 concept mapping from an explicit header. EXTENSION stores the original field name and original value in a source-specific assertion; it does not imply a cross-source interpretation.
- `required=NO_GLOBAL_REQUIREMENT` reflects observed missingness and the v0.2 model's provisional cardinality. No source cell is rewritten. Dates, measurements and identifiers require separate validated derived assertions in A6/A8.
- Field map: `dataset/mappings/source_field_mapping.csv`. Classification: `dataset/mappings/DATA_FIELD_CLASSIFICATION.csv`.
- Known ambiguity: product/registration/use grain differs by source; field mapping does not create entity identity or join keys. AU historical registry path mismatch is resolved by frozen file hash and country graph manifest, as documented in A2.

**Next:** Human Gate 1 schema review and A6 normalization on the frozen files. Supplementary use-detail grain remains to be established before creating RegistrationUse facts.
'''
(BASE/'docs/audits/A4_A5_FIELD_MAPPING_REVIEW.md').write_text(report,encoding='utf-8')
print(f"A4_A5_DONE fields={len(rows)} core={counts['CORE']} extension={counts['EXTENSION']}")
