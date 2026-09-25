# Data Dictionary

Delivered Parquet columns are UTF-8 strings. Empty strings mean unavailable or not applicable. JSON strings are marked. The full source-record and Evidence lookup is in the internal engineering release.

## canonical/entities.parquet

| Field | Type | Required | Meaning | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| entity_id | string | Yes | Opaque PestKG Canonical entity ID. | CROP_0003b17efb904bb0b42df1a282c056ca |  |
| entity_type | string | Yes | Approved entity class. | CropTerm |  |
| entity_status | string | No | Entity lifecycle status. | active |  |
| jurisdiction_id | string | No | Regulatory jurisdiction ID for a local entity. | JUR_8b603e79ffcd4b11a44cd528f1da39ff |  |
| source_id | string | No | Source registry ID; edge source_id instead means subject node ID. | SRC_ee3afb1c9c46468f9a74b2219ff0be96 |  |
| source_snapshot_id | string | No | Immutable source snapshot ID. | SSNP_aa9dd2c4a0d549c09dfe5f75b4e642f0 |  |
| source_record_id | string | No | Frozen source-row locator. | REC_0a65640cdd1004997a4fadc0be07eea0 |  |
| display_label | string | No | Source-backed short label. | PLASTICS (PVC) / WOOD PRODUCTS |  |
| grain_status | string | No | Conservative entity granularity or scoping rule. | UNSPLIT_SOURCE_FIELD |  |
| extension_properties | JSON string | No | JSON for source-specific retained attributes. | JSON object |  |
| evidence_id | string | No | Evidence ID supporting this value or relation. | EVD_185d2ccd71a5458d93014d002c11c216 |  |

## canonical/names.parquet

| Field | Type | Required | Meaning | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| name_key | string | No | Stable name assertion key. | 0000bc7adf9a853ec3b443296e993391d7997b |  |
| entity_id | string | Yes | Opaque PestKG Canonical entity ID. | PROD_bf225eddde134d9cbb1176f121c1ef84 |  |
| name | string | No | Original source name text. | 噻虫胺 |  |
| name_type | string | No | Original, translated or other source-supported name class. | original_name |  |
| language | string | No | Language tag; und means undetermined. | und |  |
| normalized_name | string | No | Derived search key, never identity proof. | 噻虫胺 | Source-scoped; no global identity inference. |
| source_id | string | No | Source registry ID; edge source_id instead means subject node ID. | SRC_2457dd69c4e444c6b8e8e878ff641a60 |  |
| evidence_id | string | No | Evidence ID supporting this value or relation. | EVD_4ffe9ae1661e4ee78ea2cf43bbdf504d |  |
| source_record_id | string | No | Frozen source-row locator. | REC_de38c5a1863eaaa32a254a24d545df41 |  |
| source_field | string | No | Original source column for this assertion. | 农药名称 |  |

## canonical/identifiers.parquet

| Field | Type | Required | Meaning | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| identifier_key | string | No | Stable external-identifier assertion key. | 000020ee3e9b4540693a68d88077c97b080e24 |  |
| entity_id | string | Yes | Opaque PestKG Canonical entity ID. | LAI_cca9d2b62dcd4503b78a10405b5e5670 |  |
| identifier_type | string | No | External scheme or source-specific constituent code. | EPA_PC_CODE |  |
| identifier_value | string | No | Source identifier text. | 001501 | Source-scoped; no global identity inference. |
| status | string | No | Validation or linkage status, not identity proof. | SOURCE_CODE_NOT_GLOBAL_ID |  |
| source_id | string | No | Source registry ID; edge source_id instead means subject node ID. | SRC_ee3afb1c9c46468f9a74b2219ff0be96 |  |
| evidence_id | string | No | Evidence ID supporting this value or relation. | EVD_7864f319e0dc41a9bde5ea548eb4f808 |  |
| source_record_id | string | No | Frozen source-row locator. | REC_56384c52d384cb32901d5d5849d7adeb |  |
| source_field | string | No | Original source column for this assertion. | ActiveIngredientsJSON |  |

## canonical/registrations.parquet

| Field | Type | Required | Meaning | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| registration_id | string | Yes | Opaque Registration ID. | REG_000066c1dc0d43a09810913300fcd224 |  |
| source_registration_key | string | No | Original permit/registration key or documented fallback. | 農藥製 06127 |  |
| product_id | string | No | Related source-local product ID when present. | PROD_d3f4dea2156247f99c9792a0f96da21f |  |
| jurisdiction_id | string | No | Regulatory jurisdiction ID for a local entity. | JUR_e5eaf05cf9d946789a6f81772434f0a1 |  |
| source_id | string | No | Source registry ID; edge source_id instead means subject node ID. | SRC_c75f84fdf1a148b29ae050354e2fb593 |  |
| source_snapshot_id | string | No | Immutable source snapshot ID. | SSNP_c6365033ae3e40e894c7687b92736e89 |  |
| evidence_id | string | No | Evidence ID supporting this value or relation. | EVD_875f4632c6b94a4b9ef00972ee3cd05a |  |
| original_status | string | No | Regulatory status text as stated by source. | Current official common-name table |  |
| registration_date_original | string | No | Source registration date text. | (empty) |  |
| registration_date_normalized | string | No | Safely derived ISO date when available. | (empty) |  |
| expiry_date_original | string | No | Source expiry date text. | 115-12-04 |  |
| expiry_date_normalized | string | No | Safely derived ISO expiry date when available. | 2026-12-04 |  |
| grain_status | string | No | Conservative entity granularity or scoping rule. | SOURCE_KEY |  |
| extension_properties | JSON string | No | JSON for source-specific retained attributes. | JSON object |  |

## canonical/registration_uses.parquet

| Field | Type | Required | Meaning | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| registration_use_id | string | Yes | Opaque RegistrationUse ID. | USE_000012add5ec4e8597f19b85c079a5db |  |
| registration_id | string | Yes | Opaque Registration ID. | REG_79aad2fe528e446c8d0660b19254bb55 |  |
| product_id | string | No | Related source-local product ID when present. | PROD_fc63820abc0243948a97cedfbee6d58f |  |
| jurisdiction_id | string | No | Regulatory jurisdiction ID for a local entity. | JUR_e5eaf05cf9d946789a6f81772434f0a1 |  |
| source_id | string | No | Source registry ID; edge source_id instead means subject node ID. | SRC_c75f84fdf1a148b29ae050354e2fb593 |  |
| source_snapshot_id | string | No | Immutable source snapshot ID. | SSNP_c6365033ae3e40e894c7687b92736e89 |  |
| evidence_id | string | No | Evidence ID supporting this value or relation. | EVD_2fc9a9c46066487fb935fd07a32d52cd |  |
| source_record_id | string | No | Frozen source-row locator. | REC_edc42f56d608292ea2a7c4918be3e672 |  |
| pairing_status | string | No | Source-row use context; no crop-target Cartesian inference. | SOURCE_ROW_CONTEXT_NO_CARTESIAN_INFERE |  |
| crop_original | string | No | Full original crop or site field text. | 梨 |  |
| target_original | string | No | Full original pest or target field text. | 二點葉蟎 |  |
| dose_original | string | No | Full original dose and unit text. | 1.3公升 |  |
| method_original | string | No | Original application method text. | (empty) |  |
| timing_original | string | No | Original timing text. | 害蟎發生時開始施藥 |  |
| formulation_original | string | No | Original formulation text. | EC 乳劑 |  |
| use_pattern_original | string | No | Original use-pattern text. | Dosage:1.3公升 / Dilution:1000 / Timing: |  |
| extension_properties | JSON string | No | JSON for source-specific retained attributes. | JSON object |  |

## kg/nodes.parquet

| Field | Type | Required | Meaning | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| node_id | string | Yes | KG node ID equal to Canonical entity ID. | CROP_0003b17efb904bb0b42df1a282c056ca |  |
| node_type | string | Yes | KG entity class. | CropTerm |  |
| display_label | string | No | Source-backed short label. | PLASTICS (PVC) / WOOD PRODUCTS |  |
| jurisdiction_id | string | No | Regulatory jurisdiction ID for a local entity. | JUR_8b603e79ffcd4b11a44cd528f1da39ff |  |
| entity_status | string | No | Entity lifecycle status. | active |  |
| source_id | string | No | Source registry ID; edge source_id instead means subject node ID. | SRC_ee3afb1c9c46468f9a74b2219ff0be96 |  |
| source_snapshot_id | string | No | Immutable source snapshot ID. | SSNP_aa9dd2c4a0d549c09dfe5f75b4e642f0 |  |
| evidence_id | string | No | Evidence ID supporting this value or relation. | EVD_185d2ccd71a5458d93014d002c11c216 |  |
| display_priority | string | No | Default HIGH/MEDIUM/LOW or hidden priority. | MEDIUM |  |
| default_hidden | string | No | True if ordinary display hides this item. | false |  |
| extension_properties | JSON string | No | JSON for source-specific retained attributes. | JSON object |  |

## kg/edges.parquet

| Field | Type | Required | Meaning | Example | Notes |
| --- | --- | --- | --- | --- | --- |
| edge_id | string | Yes | Release-stable relationship assertion ID. | RA_000000d1cd2f229b0bfee7586665407b |  |
| source_id | string | No | Source registry ID; edge source_id instead means subject node ID. | JUR_e5eaf05cf9d946789a6f81772434f0a1 |  |
| predicate | string | Yes | Approved directed UPPER_SNAKE_CASE relation. | IN_TERRITORY |  |
| target_id | string | Yes | Target KG node ID. | CTRY_63bce6e4188146e4a2335844ea5c51ba |  |
| assertion_status | string | No | Source-asserted, derived or reviewed status. | source_asserted |  |
| evidence_id | string | No | Evidence ID supporting this value or relation. | EVD_db7445f2739245f39c8feb3e6cc3f15b |  |
| source_snapshot_id | string | No | Immutable source snapshot ID. | SSNP_c6365033ae3e40e894c7687b92736e89 |  |
| source_record_id | string | No | Frozen source-row locator. | REC_e8493ea9d5103a38b3fdfc9ca1b360c4 |  |
| origin_kind | string | No | Source-asserted or derived origin. | source_asserted |  |
| derivation_rule_id | string | No | Versioned rule behind a derived/component relation. | (empty) |  |
| pipeline_version | string | No | Pipeline version that emitted the assertion. | a-line-canonical-v1.0.0 |  |
| display_priority | string | No | Default HIGH/MEDIUM/LOW or hidden priority. | LOW |  |
| default_hidden | string | No | True if ordinary display hides this item. | false |  |

