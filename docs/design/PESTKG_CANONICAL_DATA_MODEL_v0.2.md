# PestKG Canonical Data Model v0.2

## 1. Status

**Human-reviewed design baseline / 经人工审核的设计基线。** 本文落实本阶段已批准的模型决策，供后续数据审计、Schema 和实现方案使用。它尚未成为生产 Schema，也不表示全量数据已经符合此模型。当前原始 RAR 的完整性测试在 `CN-TW/aphia_pesticide/edges.csv.gz` 报 CRC error；因此 **Full RAR validation pending because current archive failed CRC**。完整文件、字段和标识符覆盖率均未在本轮独立复算。[v0.1](PESTKG_CANONICAL_DATA_MODEL_v0.1.md) 完整保留；本文件不修改数据、代码或其他提案。

本文使用两种明确标记：**APPROVED DESIGN DECISION** 表示已由人工确定的模型方向；**PROVISIONAL / REQUIRES FULL DATA VALIDATION** 表示需在可信全量档案恢复后核实的具体字段、映射、基数或实施约束。正式技术主线是 React/TypeScript → FastAPI/Python → DuckDB/Neo4j；Java 21/Spring Boot/Vaadin 保留为冻结的实验/参考实现。

## 2. Design Goals

**APPROVED DESIGN DECISION**：同时表达全球审核化学身份和各司法辖区的原始监管事实；为每个长期引用对象分配稳定、可追溯的 PestKG 内部 ID；永久保留来源原值；把名称、外部标识、对齐结论和证据分别建模；使数据重建后仍能回答“同一化学实体的判断依据是什么”和“这个具体事实来自哪里”。模型应简单、可查询、可解释，并支持不可变发布。

## 3. Non-Goals

v0.2 不是最终 OWL Ontology、完整数据清洗实现、API Contract、DuckDB/Neo4j 物理 Schema 或迁移计划。本文不宣布任何实际 CAS/PubChem/ChEBI 覆盖率，不自动合并实体，不规定尚未验证的各国字段必填率，也不批准原始数据再分发。Crop/Target 的全球 canonical 层本版不纳入核心模型；未来可另行提出 `GlobalCrop`、`GlobalTarget`。本文不改变现有发布包。

## 4. CURRENT vs v0.2

| Concern | CURRENT：仓库可见状态 | v0.2 设计基线 | 验证边界 |
| --- | --- | --- | --- |
| 化学身份 | `ActiveIngredientLocal`、发布元数据中的 `exactMatch`/`lexicalAlignment` | **APPROVED**：`GlobalChemical` 与 `LocalActiveIngredient` 并存 | 现有对齐的证据和粒度待全量审计 |
| ID | 辖区前缀 node ID，比较样本中有 `CHEBI:` 等共享 ID | **APPROVED**：PestKG 分配不含业务语义的稳定内部 ID；外部 ID 单独记录 | 旧 ID 的稳定性和迁移映射待核实 |
| 名称 | `label_original`、`label_en`，局部样本有多语言及单位混入名称 | **APPROVED**：区分原名、译名、推荐展示名、全球规范名、同义名、商品名和搜索键 | 各来源语言与名称类型覆盖待核实 |
| 登记用途 | `RegistrationUse` 已是节点，带 pairing/source 信息 | **APPROVED**：继续作为事实型实体 | 具体粒度和多对多配对规则待全量核实 |
| 来源 | 节点/边有 `source_record_id`、`source_url` | **APPROVED**：记录级和关系级必备，关键字段字段级 | 全量覆盖与实际来源定位精度待核实 |
| 辖区 | `CountryJurisdiction` 和字符串代码；GB/GB-NI 共用 ISO3 `GBR` | **APPROVED**：`Jurisdiction` 与 `CountryOrTerritory` 分离 | 各来源到代码的映射待验证 |
| 扩展属性 | `properties_json` 承载异构字段 | **APPROVED**：稳定高价值字段进入 Core，长尾保留 Extension | 具体字段必填性仍为暂定 |

CURRENT 依据：[发布 Schema](../../data/releases/2026.08.3_federated/schema.json)、[辖区元数据](../../data/releases/2026.08.3_federated/countries.json)、[Phase 1 审计](../audits/PESTKG_DATASET_DEEP_AUDIT_2026-09-23.md)。这些资料不是本次 RAR 的完整性证明。

## 5. Entity Scope Model

**APPROVED DESIGN DECISION**：全球层解决经审核的跨来源化学身份和共享参照；本地层保留来源及监管语境。全球层的存在不导致不同司法辖区的登记、产品或使用记录直接合并。

| Scope | 模型成员 | 边界 |
| --- | --- | --- |
| GLOBAL / CROSS-JURISDICTION | `GlobalChemical`、`Jurisdiction`、`CountryOrTerritory`、`RegulatoryOrganization`、`Source`、`SourceSnapshot`、`Evidence`、`IdentityDecision` | 共享身份或审计对象；仍需明确其适用辖区和来源 |
| LOCAL / SOURCE-SPECIFIC | `LocalActiveIngredient`、`PesticideProduct`、`Registration`、`RegistrationUse`、`CropTerm`、`TargetTerm`、`FormulationTerm` | 每条记录保留 jurisdiction、source 和 source snapshot context |
| ASSERTION LAYER | `Name`、`ExternalIdentifier`，以及字段/关系断言 | 随所属实体具有 global 或 local scope；首版可置于关系表/侧表，**不强制成为 Neo4j 节点** |

`Source`、`Evidence` 和 `IdentityDecision` 属于跨层追踪对象，不表示其陈述对所有司法辖区成立。`GlobalCrop`、`GlobalTarget` 仅为未来预留术语，不是 v0.2 核心实体。

## 6. Entity Types

下表的“核心属性”是概念字段候选；除已批准的 ID、原值和来源保留原则外，**具体字段是否对所有来源 mandatory 属于 PROVISIONAL / REQUIRES FULL DATA VALIDATION**。每个稳定 ID 均由 PestKG 管理，源站自然键和外部 ID 另存。

| Entity | Definition / Grain | Scope / Stable ID | Core attributes（概念） | Provenance |
| --- | --- | --- | --- | --- |
| `GlobalChemical` | 一个经审核、粒度明确的全球化学实体身份；盐、混合物、异构体和形态不可默认为同一粒度 | Global；PestKG `CHEM_…` 不透明 ID | `identity_granularity`、`canonical_name`、`entity_status`、身份审核状态 | 关联批准的 `IdentityDecision` 和字段级名称/标识证据 |
| `LocalActiveIngredient` | 一个来源/监管语境中的有效成分记录或术语 | Local；不透明本地 ID，保留旧 `nodeId` | `jurisdiction_id`、`source_id`、`source_record_id`、`original_name`、`entity_status` | 来源快照、记录和与 GlobalChemical 的对齐证据 |
| `PesticideProduct` | 一个来源声明的产品身份或版本 | Local；不透明产品 ID | 原始产品名、来源产品键、辖区、状态（若有） | 记录级及关键状态字段级 |
| `Registration` | 一个监管登记/授权记录及其有效期语境 | Local；不透明登记 ID | 来源登记号、辖区、原始状态和日期文本 | 记录级；状态与有效期字段级 |
| `RegistrationUse` | 一个来源断言的具体登记使用事实，含官方配对语义 | Local；不透明 use ID | registration/source context、`pairing_status`、原始使用条件 | 记录级与关键参与关系级 |
| `CropTerm` | 来源使用的作物术语，而非全局作物身份 | Local；不透明术语 ID | 原始名称、语言、辖区/来源 | 记录/字段来源 |
| `TargetTerm` | 来源使用的防治对象术语 | Local；不透明术语 ID | 原始名称、语言、辖区/来源 | 记录/字段来源 |
| `FormulationTerm` | 来源使用的剂型术语 | Local；不透明术语 ID | 原始名称、语言、辖区/来源 | 记录/字段来源 |
| `Jurisdiction` | 作出或适用监管决定的范围 | Global registry；稳定 PestKG 辖区 ID 与独立代码 | regulatory code、名称、有效时间 | 代码来源和边界证据 |
| `CountryOrTerritory` | 地理/ISO 参照对象 | Global registry；稳定内部 ID | 地理名称、ISO2/ISO3（适用时） | ISO/地理参照来源 |
| `RegulatoryOrganization` | 监管组织身份及其随时间变化的职责 | Cross-jurisdiction；稳定内部 ID | 原名、角色、适用辖区和有效时间 | 机构来源与角色断言证据 |
| `Source` | 官方站点、数据库、出版物或其他来源 | Global registry；稳定 `source_id` | 来源名、类型、组织、URL、权利状态 | 来源登记与条款位置 |
| `SourceSnapshot` | 一次不可变的获取/交付版本 | Cross-jurisdiction；稳定 `snapshot_id` | `source_id`、内容哈希、原路径/URI、获取时间或 UNKNOWN、版本 | 快照哈希与获取记录 |
| `Evidence` | 支持具体断言的记录、字段或文献定位 | Cross-jurisdiction；稳定 `evidence_id` | snapshot/record locator、`evidence_type`、DOI/citation（如适用） | 指向不可变快照，保留审阅信息 |
| `IdentityDecision` | 一次对两个实体是否同一身份的可审计判断 | Cross-jurisdiction；稳定 `decision_id` | 两端 ID、决策、方法、规则版本、证据、审核时间 | 证据引用、规则和人工审核者 |

`Name` 与 `ExternalIdentifier` 是结构化 assertion，不在上表中暗示必需的图节点。其粒度和字段分别在第 8、9 节定义。

## 7. Canonical Identifier Policy

**APPROVED DESIGN DECISION**：PestKG 自行分配 opaque、non-semantic、稳定且不可回收的内部 ID；CAS、PubChem CID、ChEBI、InChIKey 等永不充当 PestKG 主键。前缀可表达实体类型（如 `CHEM_`），后缀不编码国家、名称、排序或化学性质。任何 row order、label hash、来源 URL、文件路径变化都不能决定永久 ID。构建重跑必须使用同一 ID Registry 和审核映射。

`Canonical ID Registry` 至少记录 `canonical_id`、`entity_type`、`entity_status`、`created_at`、`superseded_by`、`merged_into`、`decision_id`、`schema_version`。旧 ID 永不重新分配给另一实体。合并时保留旧 ID，并记录 `merged_into` 和依据；拆分时将旧 ID 标为 `superseded`，新实体获取新 ID。现有 local `nodeId`、来源记录键和外部 ID 保留为可查询别名/历史映射，不被悄悄改写。实体撤销或纠错使用 lineage，不删除已有引用。

**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：现有 node ID 在不同 release 中的稳定率、同源自然键可靠性、具体前缀和 Registry 物理存储方式。它们须经可信全量数据和迁移设计验证。

## 8. Name Model

**APPROVED DESIGN DECISION**：

| Name type | 含义与约束 |
| --- | --- |
| `original_name` | 来源原文，保留原 Unicode、大小写、标点和语言语境，绝不覆盖 |
| `translated_name` | 翻译名称，必须记录译名来源或翻译过程证据 |
| `preferred_name` | 特定语言和使用情境下推荐的展示名称，可随版本和语境改变 |
| `canonical_name` | 仅在 `GlobalChemical` 层经审核选定的规范名称，须有字段级证据和决策记录 |
| `synonym` | 同义名称；同名不足以证明身份相同 |
| `trade_name` | 商品/商标名称；产品名不能自动变成化学身份 |
| `search_normalized` | 派生的检索/匹配索引键，不是正式展示值或证据原值 |

首版优先设计关系侧表 `entity_names(entity_id, name_value, language, script, name_type, source_id, evidence_id, is_preferred, normalized_key, assertion_status, valid_from, valid_to)`。字段组合、语言标记标准和 preferred 的唯一性范围在实施时验证；名称原值与规范化键同时保存。规范化可生成候选，但不能覆盖原名，也不能单独触发 `exactMatch`。

## 9. External Identifier Model

**APPROVED DESIGN DECISION**：CAS、PubChem CID、ChEBI、InChI、InChIKey、SMILES、AGROVOC 及其他来源标识均存为外部 identifier/structure assertion。建议侧表 `external_identifiers(entity_id, scheme, value, source_id, evidence_id, status, original_value, normalized_value, granularity, checked_at)`；最低语义要求是 `scheme`、`value`、`source`、`evidence`、`status`。一个实体可以有多个 scheme/value 断言；冲突断言保留并标记，不能以最后写入值覆盖。InChI/SMILES 可能是结构描述符而非唯一业务 ID，也须记录 scheme、粒度和适用范围，不隐式当作主键。

**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：各 identifier 实际存在位置、覆盖率、冲突率与标准化规则。Q1 比较样本出现 ChEBI ID 不能证明全库 ChEBI 覆盖。CAS 校验和其他格式校验仅是语法检查。

## 10. Chemical Identity Model

**APPROVED DESIGN DECISION**：`GlobalChemical` 表示经过审核的全球化学身份，只回答多个来源/司法辖区的记录是否指向同一化学实体。`LocalActiveIngredient` 继续承载本地监管名称、登记、剂型和来源语境。建立 `GlobalChemical` 不把不同国家的产品、登记或使用事实合并。

Identity Resolution Policy：先保留原始字符串，再生成 Unicode NFKC、大小写、空格/标点处理后的候选键；名称一致只产生候选。CAS RN 先检查格式与 checksum，checksum 合法只表示 **syntactically valid**，不能证明 **chemical identity**。PubChem、ChEBI、InChIKey 等应连同来源、版本及对应化学粒度审查。对 salt、mixture、isomer、form 及母体/衍生物明确身份边界；标识符指向不同粒度时不做自动等价。不同来源 ID 冲突、同 ID 对应不同结构或多 CAS 等情形**阻断自动 `exactMatch`**，进入人工审核。人工判断保存在 `IdentityDecision`，而非改写原始节点。当前样本中 AU、GB、GB-NI 的 `glyphosate` 名称候选簇仅说明候选发现能力，不构成三条 local record 的身份结论。

**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：哪些 local 记录实际满足相同化学粒度、GlobalChemical 覆盖率、冲突规模、各来源可信度次序和具体自动规则白名单。

## 11. Alignment States

**APPROVED DESIGN DECISION**：

| State | 含义 | 是否允许自动 merge / identity 使用 |
| --- | --- | --- |
| `lexicalAlignment` | 名称相似、翻译或规范化匹配，供发现候选 | **永远不允许**自动合并或作为确证身份 |
| `candidateMatch` | 已有较强标识符/结构/来源证据，但尚不足以确证同一化学身份 | 不允许自动合并；等待进一步规则或人工审核 |
| `exactMatch` | 规则验证或人工审核通过，证据可追溯，且 chemical granularity 一致 | 可支持经审核的 GlobalChemical 身份映射；仍保留全部 local records |

状态升级应生成新的 `IdentityDecision` 或审计事件，不覆盖过去的候选或 `NO_MATCH` 记录。`exactMatch` 必须有 evidence；若后续证据冲突，应暂停该映射并记录新决策和 lineage。

## 12. IdentityDecision Model

**APPROVED DESIGN DECISION**：新增可独立审计的 `IdentityDecision`，记录候选、确认、排除及不确定判断。最小结构：

| Field | 含义 |
| --- | --- |
| `decision_id` | 稳定、不可回收的决定 ID |
| `entity_a`, `entity_b` | 被比较的实体 ID，保留原始顺序及对象版本 |
| `decision` | 枚举 `MATCH`、`NO_MATCH`、`UNCERTAIN` |
| `evidence_ids` | 支持或反驳决定的证据引用集合 |
| `method`, `rule_version` | 人工、规则或辅助方法及其可复现版本 |
| `confidence` | 方法给出的置信信息；不代替证据或人工批准 |
| `reviewer`, `reviewed_at` | 审核者与审核时间；纯规则决定也应指明规则责任及状态 |
| `created_at` | 候选/决定创建时间 |

后续可增加 `supersedes_decision_id`、理由、决策有效时间和冲突状态，但 v0.2 的 `decision` 枚举先保持三值。`MATCH` 只有在第 10、11 节条件满足时才支持 `exactMatch`；`UNCERTAIN` 与 `NO_MATCH` 保留，避免重新运行候选生成时丢失“为什么不同/未定”的解释。证据缺失的旧 `exactMatch` 不能被默认为已审核。

## 13. Registration / RegistrationUse Model

**APPROVED DESIGN DECISION**：`RegistrationUse` 保留为 entity，是一个来源断言的具体使用事实（statement-like entity），不是普通 Product→Crop edge。示意：

```text
Registration
    └─ hasUse → RegistrationUse
                     ├─ crop → CropTerm
                     ├─ target → TargetTerm
                     ├─ formulation → FormulationTerm
                     ├─ dose / method / timing → 原值与派生断言
                     └─ evidence → Evidence
```

每条 use 保留 jurisdiction、source snapshot、source record、官方配对状态及时间语境。不能因为一条来源记录同时提及作物和靶标，就自动产生所有笛卡尔积配对。剂量、作物、靶标、施用方法和时间条件属于这个 use 的共同语境；将它们塞进单条普通 edge 会丢失复合事实的粒度、版本和各自证据。**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：不同来源中“一个 use”的自然键、同一登记下的重复 use、缺少明确 Registration 时可接受的 equivalent source context，以及每种 participant 关系的基数。

## 14. Jurisdiction Model

**APPROVED DESIGN DECISION**：`Jurisdiction` 是监管决策范围；`CountryOrTerritory` 是地理/ISO 参考对象，二者分离。`GB` 与 `GB-NI` 在现有元数据中均对应 ISO3 `GBR`，未来 EU 或 subnational regulation 也不等同于单个国家。保留 PestKG jurisdiction code，并以带来源和有效时间的映射联系 ISO2/ISO3；不能仅凭 ISO3 推断 jurisdiction。Local entities 必须携带 jurisdiction/source context。**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：12 个辖区及未来区域组织的精确边界、历史更名和代码映射。

## 15. Measurement / Unit Model

**APPROVED DESIGN DECISION**：原始值永久保存；规范化值仅作为可追溯派生结果。测量断言至少考虑 `original_value`、`original_unit`、`normalized_value`、`canonical_unit`、`conversion_rule_id`、`confidence`、`evidence_id`，并关联 measurement type 和适用的 RegistrationUse。转换失败或单位不明时保留原值，派生值为空并标记状态；不静默猜测。**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：真实剂量/浓度/施用率单位清单、适用转换规则和单位字段覆盖率。

## 16. Date / Time Model

**APPROVED DESIGN DECISION**：每个日期断言保留 `original_text`、`source_locale`、`parsed_date`、`precision`、`timezone`、`parse_status`。注册、到期、来源获取和记录更新时间的语义须分别标记，不能用一个无语义日期字段代替。样本同时有 ISO、`02/27/2020` 和 `22/08/2025` 形态；歧义格式不自动按某一辖区解释。**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：各来源真实 locale、日期语义、时区与解析率。

## 17. Provenance Integration

**APPROVED DESIGN DECISION**：采用三层科研方案：Level 1 **record-level 必须实现**；Level 2 **relationship-level 必须实现**；Level 3 对关键字段**field-level 必须实现**，首版优先 CAS、PubChem CID、ChEBI、`canonical_name`、`regulatory_status`、registration validity 和 `exactMatch`。其他字段逐步升级。完整细节仍以 [Provenance Model v0.1](PESTKG_PROVENANCE_MODEL_v0.1.md) 为参考；本文不替代它。

```text
Source（来源）
  ↓
SourceSnapshot（不可变获取快照）
  ↓
Evidence（具体记录/字段/文献定位）
  └─ supports → Entity assertion / Name assertion /
                ExternalIdentifier assertion / Relationship /
                IdentityDecision
```

`Evidence` 不等于 `Source`：前者是支持某一断言的可定位证据，后者是资料来源；`SourceSnapshot` 固定来源的某个字节版本。每条关键关系独立关联证据；同一事实的不同来源可并存，不用一个 URL 覆盖其他来源。**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：全量记录级、关系级和关键字段级证据能否达标、实际来源 URL 是否指向记录、历史 DOI/获取日期是否可恢复。

## 18. Core vs Extension Properties

**APPROVED DESIGN DECISION**：Core 只收语义清晰、跨来源稳定、支持主要查询和追溯的高价值字段；来源特有、长尾、实验性或暂不能统一解释的字段保存在 `extension_properties` 及其来源字段映射中。不能为兼容所有国家无限扩张 Core，也不能把核心 ID、辖区、来源、名称、关键状态及证据全部埋进 JSON。

Core 概念至少包括内部 ID、类型、生命周期状态、jurisdiction/source context、原始名称或原始值引用、关键实体间关系、RegistrationUse 配对状态、关键来源和证据引用。`GlobalChemical` 的审核粒度与规范名称、`Registration` 的原始监管状态/有效期，以及 Identifier/Name assertion 的 scheme/type、值和证据也属于核心语义。具体列级 mandatory/nullable 规则、各国映射和 extension 字段清单均 **PROVISIONAL / REQUIRES FULL DATA VALIDATION**。

## 19. Versioning

**APPROVED DESIGN DECISION**：分别记录 `Data Version`（数据内容）、`Schema Version`（本模型/结构）、`Pipeline Version`（转换逻辑）、`Source Snapshot Version`（每个来源字节版本）、`Canonical Registry Version`（ID 与审核映射状态）、`Release Version`（对外不可变组合及校验清单）。发布记录应绑定这些版本及输入/输出哈希。Schema 升级不自动改变 canonical ID；Pipeline 重跑也不能改变已审核的 canonical identity。任何身份修订须生成新决定与 lineage，并保留旧 release 的可解释性。

## 20. Entity Lifecycle

**APPROVED DESIGN DECISION**：Canonical Entity 统一支持 `entity_status ∈ {active, deprecated, superseded, merged}`。`active` 可用于当前身份；`deprecated` 保留但不推荐新引用；`superseded` 表示已由新身份/拆分结果替代，记录 `superseded_by`；`merged` 表示已审核合并到另一个 ID，记录 `merged_into` 与 `decision_id`。旧 ID 始终可查询到历史及映射，不删除、不回收。拆分时旧 ID `superseded`，每个新实体获新 ID；合并时旧 ID `merged`，不能把旧 ID 分配给另一实体。生命周期事件应包含时间、原因、审核者和适用 release。

## 21. Model Invariants

**APPROVED DESIGN DECISION**：

1. Canonical ID never reused；任何旧 ID 都不分配给其他实体。
2. Original source values never overwritten；原始 Unicode、大小写、日期与单位文本永久保留。
3. `lexicalAlignment` never causes automatic merge。
4. `exactMatch` must have evidence，并与 chemical granularity 一致。
5. Every canonical identity decision is auditable，包括 MATCH、NO_MATCH、UNCERTAIN。
6. Every `RegistrationUse` belongs to a `Registration` or documented equivalent source context。
7. Every local entity retains jurisdiction and source context。
8. External identifiers never become implicit PestKG primary keys。
9. Normalized values are derived and carry transformation status/rule。
10. Published releases are immutable；修订产生新版本与 lineage，不回写已发布事实。

## 22. Open Questions

以下是真正尚未由本次人工决策或可信全量数据解决的事项，不重新讨论已批准的 GlobalChemical、本地层、RegistrationUse 实体和三层 provenance 原则：

1. 各化学来源对 salt、mixture、isomer、form 的标识粒度如何对应；哪些经验证的规则可免人工逐条批准？
2. 已有 local `nodeId` 跨 release 的稳定率如何，迁移时哪些旧 ID 应成为公开长期别名？
3. 各来源 RegistrationUse 的真实事实粒度和“equivalent source context”边界是什么？
4. 哪些 Core 字段可在所有来源强制非空，哪些必须允许明确的 UNKNOWN/不适用？
5. 来源权利和记录级定位能否支持计划中的证据展示与对外 release；具体发布范围需独立审核。
6. IdentityDecision 的规则批准角色、冲突复审流程与 Registry 物理承载方式如何确定？

## 23. Validation Required After RAR Recovery

**PROVISIONAL / REQUIRES FULL DATA VALIDATION**：先用可复核 RAR5 工具通过 archive CRC，并核对档案 SHA、成员 manifest 与解压后哈希；若仍失败，停止全量审计，不从局部文件推断全库。可信档案到位后，按 source/jurisdiction 分块检查真实字段、类型、缺失、日期/单位形态、CAS 格式与 checksum、PubChem/ChEBI/InChIKey 覆盖和冲突、同名/同 ID 候选、化学粒度、现有 `exactMatch`/`lexicalAlignment` 的证据、RegistrationUse 粒度、关系端点/重复、各层 provenance、辖区映射与来源 license。然后评估本模型的 Core 字段必填性、GlobalChemical 可审核覆盖率及转换成本。所有量化结论须注明分母、数据版本和来源；验证结果可能细化字段和映射，但不得在未重新人工审核的情况下推翻本文已批准的设计原则或直接进入数据清洗与实现。
