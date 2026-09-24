# PestKG API 接口文档

> **版本**: v1.1  
> **Base URL**: `http://127.0.0.1:8000`（开发环境）  
> **协议**: HTTP/1.1, REST  
> **数据格式**: JSON (UTF-8)  
> **只读接口**: 所有端点均为 GET 或 POST 查询，不修改数据

---

## 目录

- [1. 通用约定](#1-通用约定)
  - [1.1 响应信封](#11-响应信封)
  - [1.2 错误响应](#12-错误响应)
  - [1.3 Release 选择](#13-release-选择)
  - [1.4 通用请求头](#14-通用请求头)
  - [1.5 通用响应头](#15-通用响应头)
- [2. 健康检查](#2-健康检查)
- [3. 统计与元数据](#3-统计与元数据)
- [4. 搜索](#4-搜索)
- [5. 实体与图谱](#5-实体与图谱)
- [6. 登记用途](#6-登记用途)
- [7. 能力问题对比](#7-能力问题对比)
- [8. Release 管理](#8-release-管理)
- [9. 文件下载](#9-文件下载)
- [10. 数据模型定义](#10-数据模型定义)
- [11. 枚举值参考](#11-枚举值参考)

---

## 1. 通用约定

### 1.1 响应信封

所有 `/api/v1` 下的成功响应都使用统一的信封结构：

```json
{
  "api_version": "1.1",
  "release_id": "2026.08.3_federated",
  "schema_version": "1.0",
  "data": { /* 端点特定数据 */ },
  "meta": {
    "generated_at": "2026-09-24T10:00:00+00:00"
    /* 端点特定的元数据 */
  },
  "links": {
    "release": "/api/v1/releases/2026.08.3_federated"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `api_version` | string | API 版本，当前 `"1.1"` |
| `release_id` | string | 本次请求所绑定的不可变数据发布 ID |
| `schema_version` | string | 数据 schema 版本 |
| `data` | object/array | 端点特定数据载荷 |
| `meta` | object | 元数据（时间戳、分页游标、计数等） |
| `links` | object | 相关链接 |

### 1.2 错误响应

所有错误使用统一结构，HTTP 状态码同时反映在状态行和响应体中：

```json
{
  "detail": {
    "code": "entity_not_found",
    "message": "Entity not found"
  },
  "error": {
    "code": "entity_not_found",
    "message": "Entity not found",
    "details": {},
    "request_id": "a1b2c3d4e5f6"
  }
}
```

| 状态码 | 含义 | 典型 `code` |
|--------|------|-------------|
| 400 | 请求参数冲突或游标无效 | `release_selector_conflict`, `cursor_release_mismatch`, `Invalid cursor` |
| 404 | 实体/Release/资源不存在 | `entity_not_found`, `release_not_found` |
| 409 | Release 生命周期冲突 | — |
| 422 | 校验失败或结果超限 | `request_validation_failed`, `export_too_large` |
| 503 | 没有可用的已验证 Release | `no_release_available`, `active_release_unavailable` |

### 1.3 Release 选择

每个 release 感知的端点都支持通过以下两种方式指定数据发布版本（任选其一，不可冲突）：

| 方式 | 示例 |
|------|------|
| 查询参数 | `?release=2026.08.3_federated` |
| 请求头 | `X-PestKG-Release: 2026.08.3_federated` |

- 两者同时存在时必须一致，否则返回 `400 release_selector_conflict`。
- 两者均未提供时，服务端自动解析当前活跃 Release。
- 一次请求期间 Release 固定不变。

### 1.4 通用请求头

| 头部 | 必填 | 说明 |
|------|------|------|
| `X-PestKG-Release` | 否 | 指定 Release ID |
| `X-Request-ID` | 否 | 请求追踪 ID（未提供时自动生成） |

### 1.5 通用响应头

| 头部 | 说明 |
|------|------|
| `X-Request-ID` | 请求追踪 ID（始终返回） |
| `X-PestKG-Release` | 实际使用的 Release ID |
| `Vary` | `/api/` 路径下始终包含 `X-PestKG-Release` |

---

## 2. 健康检查

### 2.1 GET /health

综合健康检查。

**响应** (200):

```json
{
  "status": "ok",
  "api_version": "1.1",
  "release_id": "2026.08.3_federated",
  "schema_version": "1.0",
  "available_releases": 1,
  "data_mode": "sample",
  "neo4j_configured": false,
  "neo4j_reachable": false,
  "neo4j_release_id": null
}
```

| 字段 | 说明 |
|------|------|
| `data_mode` | `"sample"` 或 `"full"` |
| `neo4j_configured` | 是否配置了 Neo4j |
| `neo4j_reachable` | Neo4j 是否可达 |

### 2.2 GET /health/live

存活探针（无依赖检查）。

**响应** (200):

```json
{ "status": "ok", "request_id": "..." }
```

### 2.3 GET /health/ready

就绪探针（检查 Release 和 Neo4j）。

**响应** (200 就绪 / 503 未就绪):

```json
{
  "status": "ready",
  "release_id": "2026.08.3_federated",
  "schema_version": "1.0",
  "data_mode": "sample",
  "neo4j_configured": false,
  "neo4j_reachable": false
}
```

---

## 3. 统计与元数据

### 3.1 GET /api/v1/stats/overview

获取知识图谱全局概览统计。

**响应** `data` 字段:

```json
{
  "title": "Federated multicountry pesticide registration knowledge graphs",
  "version": "2026.08.3_federated",
  "published_at": "2026-08-24",
  "cutoff": "2026-08-20",
  "status": "release_ready",
  "distribution_status": "blocked_pending_manifest_rebuild",
  "known_limitations": ["..."],
  "mode": "sample",
  "jurisdictions": 12,
  "source_records": 821183,
  "country_nodes": 1204973,
  "country_edges": 9739818,
  "shared_nodes": 44645,
  "alignment_edges": 48721,
  "node_types": { "PesticideProduct": 163297, "...": "..." },
  "relation_types": { "hasRegistrationUse": 820231, "...": "..." },
  "coverage": [ /* CoverageRecord, 见 §10.4 */ ]
}
```

### 3.2 GET /api/v1/stats/countries

获取各国/管辖区详细信息列表。

**响应** `data`: `CountryData[]`，见 [§10.2](#102-countrydata)。

### 3.3 GET /api/v1/schema

获取数据 schema 定义。

**响应** `data` 字段:

```json
{
  "schema_version": "1.0",
  "node_fields": ["id", "type", "label_original", "label_en", "jurisdiction", "source_record_id", "source_url", "properties_json"],
  "edge_fields": ["id", "start_id", "predicate", "end_id", "jurisdiction", "source_record_id", "source_url", "properties_json"],
  "node_types": { "PesticideProduct": 163297, "...": "..." },
  "relation_types": { "hasRegistrationUse": 820231, "...": "..." },
  "federation_predicates": { "lexicalAlignment": 44672, "exactMatch": 4049 },
  "rules": {
    "country_local_identity": "Local regulatory entities are never merged across jurisdictions.",
    "cross_country_alignment": "Cross-country traversal uses exactMatch or lexicalAlignment.",
    "formal_crop_target_pair": "Formal comparison defaults to official_pair_asserted."
  }
}
```

---

## 4. 搜索

### 4.1 GET /api/v1/search

全文搜索知识图谱节点。支持多语言（中文、英文、日文等）。

**查询参数**:

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 |
|------|------|------|------|------|------|
| `q` | string | 否 | `""` | 最长 200 | 搜索关键词，对 `label_original`、`label_en`、`id` 做 ILIKE 模糊匹配 |
| `entity_type` | string | 否 | — | 最长 100 | 按节点类型精确过滤 |
| `jurisdiction` | string | 否 | — | 最长 10 | 按管辖区过滤（自动转大写） |
| `limit` | int | 否 | 50 | 1–100 | 返回条数上限 |
| `release` | string | 否 | — | 最长 128 | Release 选择 |

**排序规则**: 当提供 `q` 时，`label_en` 完全匹配的记录排最前，其余按 `label_en`（回退到 `label_original`）字母序排列。

**响应** `data`: `EntityData[]`，见 [§10.5](#105-entitydata)。

**示例**:

```
GET /api/v1/search?q=GLYPHOSATE&limit=10
```

```json
{
  "api_version": "1.1",
  "release_id": "2026.08.3_federated",
  "schema_version": "1.0",
  "data": [
    {
      "id": "AU:AI:d22fdad88d35b630b33716b8",
      "type": "ActiveIngredientLocal",
      "label_original": "GLYPHOSATE",
      "label_en": "GLYPHOSATE",
      "jurisdiction": "AU",
      "source_record_id": "RAW:5f2ef3eb26004f52cc81b83f",
      "source_url": "https://portal.apvma.gov.au/pubcris",
      "properties": { "english_status": "official_english_field" }
    }
  ],
  "meta": { "generated_at": "...", "count": 1 },
  "links": { "release": "/api/v1/releases/2026.08.3_federated" }
}
```

---

## 5. 实体与图谱

### 5.1 GET /api/v1/entities/{node_id}

获取单个节点的完整信息。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | string (path) | 节点 ID，支持 `/` 字符 |

**响应** `data`: `EntityData`，见 [§10.5](#105-entitydata)。

**错误**: 404 `Entity not found` — 节点不存在。

### 5.2 GET /api/v1/graph/neighborhood

获取某节点的邻域子图（BFS 展开）。

**查询参数**:

| 参数 | 类型 | 默认 | 约束 | 说明 |
|------|------|------|------|------|
| `node_id` | string | — | 必填 | 中心节点 ID |
| `depth` | int | 1 | 1–2 | BFS 展开深度 |
| `release` | string | — | — | Release 选择 |

**服务端限制** (由配置决定):

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `graph_node_limit` | 1000 | 最多返回节点数 |
| `graph_edge_limit` | 2000 | 最多返回边数 |

**查询引擎**: 优先使用 Neo4j（如已配置且 Release 匹配），回退到 DuckDB。`meta.query_engine` 标识实际使用的引擎（`"neo4j"` 或 `"duckdb"`）。

**响应** `data`: `GraphData`，见 [§10.7](#107-graphdata)。

**错误**: 404 `Entity or neighborhood not found`。

### 5.3 GET /api/v1/graph/path

查找两个节点之间的最短路径。

**查询参数**:

| 参数 | 类型 | 默认 | 约束 | 说明 |
|------|------|------|------|------|
| `start_id` | string | — | 必填 | 起点节点 ID |
| `end_id` | string | — | 必填 | 终点节点 ID |
| `max_depth` | int | 3 | 1–3 | 最大搜索深度（跳数） |
| `release` | string | — | — | Release 选择 |

**响应** `data`: `GraphData`，见 [§10.7](#107-graphdata)。

- 若 `start_id == end_id`，返回仅含该节点的单节点图。
- 若不存在路径，返回 `{ "nodes": [], "edges": [] }`。
- `meta.query_engine` 标识引擎（`"neo4j"` 或 `"duckdb"`）。

---

## 6. 登记用途

### 6.1 POST /api/v1/registration-uses/query

分页查询农药登记用途记录。支持多维度过滤和游标分页。

**请求体**:

```json
{
  "filters": {
    "jurisdictions": ["AU", "CN"],
    "query": "GLYPHOSATE",
    "product": "Roundup",
    "active_ingredient": "glyphosate",
    "crop": "wheat",
    "target": "weed",
    "formulation": "SL",
    "registration_status": "approved",
    "pairing_status": "paired",
    "valid_on": "2026-01-01"
  },
  "cursor": null,
  "page_size": 50
}
```

**filters 字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `jurisdictions` | string[] | 最多 12 个 | 管辖区代码列表（自动去重、去空白、转大写） |
| `query` | string\|null | 最长 200 | 全文模糊搜索（同时匹配产品、有效成分、作物、靶标、剂型） |
| `product` | string\|null | 最长 200 | 产品名称模糊匹配 |
| `active_ingredient` | string\|null | 最长 200 | 有效成分模糊匹配 |
| `crop` | string\|null | 最长 200 | 作物模糊匹配 |
| `target` | string\|null | 最长 200 | 靶标模糊匹配 |
| `formulation` | string\|null | 最长 200 | 剂型模糊匹配 |
| `registration_status` | string\|null | 最长 100 | 登记状态模糊匹配 |
| `pairing_status` | string\|null | 最长 100 | 配对状态模糊匹配 |
| `valid_on` | date\|null | ISO 8601 | 有效日期过滤（`registration_date ≤ valid_on ≤ expiry_date`，支持多种日期格式） |

**其他字段**:

| 字段 | 类型 | 默认 | 约束 | 说明 |
|------|------|------|------|------|
| `cursor` | string\|null | null | — | 上一页返回的游标 |
| `page_size` | int | 50 | 1–200 | 每页行数 |

**响应**:

```json
{
  "data": [ /* RegistrationUseData[], 见 §10.8 */ ],
  "meta": {
    "generated_at": "...",
    "total": 15234,
    "page_size": 50,
    "next_cursor": "eyJvZmZzZXQiOjUwfQ"
  }
}
```

| meta 字段 | 说明 |
|-----------|------|
| `total` | 满足过滤条件的总记录数 |
| `next_cursor` | 下一页游标（已到末页时为 `null`） |

**游标规则**: 游标与 `release_id` 和 filters 指纹绑定。跨 Release 或跨 filters 复用游标会返回 `400 cursor_release_mismatch` 或 `400 cursor_filter_mismatch`。

### 6.2 POST /api/v1/exports/registration-uses

导出登记用途记录为 CSV 流。

**请求体**:

```json
{
  "filters": { /* 同 §6.1 的 filters */ }
}
```

**响应** (200):

- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename="registration-uses-2026.08.3_federated.csv"`
- CSV 首行为 UTF-8 BOM + 列头

**错误** (422): 导出量超过同步行限制。

```json
{
  "detail": {
    "code": "export_too_large",
    "message": "Export exceeds the synchronous row limit",
    "details": { "total": 200000, "limit": 100000 },
    "total": 200000,
    "limit": 100000,
    "download_url": "/downloads/2026.08.3_federated/"
  }
}
```

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `export_limit` | 100000 | 同步导出最大行数 |

---

## 7. 能力问题对比

### 7.1 GET /api/v1/compare/{question}

查询预计算的 competency question 结果。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `question` | string | 能力问题 ID：`q1`–`q5` |

**能力问题定义**:

| ID | 主题 | 可搜索列 |
|----|------|---------|
| `q1` | 跨国作物-有效成分 | `crop_label_en`, `active_ingredient_label_en` |
| `q2` | 跨国同靶标产品 | `target_label_en`, `product_name` |
| `q3` | 共享作物-靶标组合 | `crop_label_en`, `target_label_en`, `countries` |
| `q4` | 有效成分-剂型 | `active_ingredient_label_en`, `formulation_label_en` |
| `q5` | 有效成分-国家用途画像 | `active_ingredient_label_en`, `crop_examples`, `target_examples`, `formulation_examples` |

**查询参数**:

| 参数 | 类型 | 默认 | 约束 | 说明 |
|------|------|------|------|------|
| `q` | string\|null | — | 最长 200 | 对该问题的可搜索列做 ILIKE 模糊匹配 |
| `jurisdiction` | string\|null | — | 最长 10 | 管辖区过滤（`q3` 用 `countries ILIKE`，其余用 `jurisdiction =`） |
| `limit` | int | 100 | 1–500 | 返回条数上限 |
| `release` | string | — | — | Release 选择 |

**响应** `data`: `ComparisonRow[]`，每行为一个动态键值对对象（列因问题而异）。

**错误**: 404 `Unknown competency question` — `question` 不在 q1–q5 范围内。

---

## 8. Release 管理

### 8.1 GET /api/v1/releases

列出所有可用 Release。活跃 Release 排首位，其余按发布时间倒序。

**响应** `data`: `ReleaseData[]`，见 [§10.9](#109-releasedata)。

### 8.2 GET /api/v1/releases/active

获取当前活跃 Release 的详细信息。

**响应** `data`: `ReleaseData`。

### 8.3 GET /api/v1/releases/{release_id}

获取指定 Release 的详细信息。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `release_id` | string | Release ID |

**响应** `data`: `ReleaseData`。

---

## 9. 文件下载

> 这些端点不在 OpenAPI schema 中（`include_in_schema=False`），但前端可通过构建 URL 直接访问。

### 9.1 GET /downloads/{release_id}/

获取某 Release 的下载目录索引。

**响应**: `index.json` 文件内容，包含 `release_id`、`license`、`artifacts[]`。

### 9.2 GET /downloads/{release_id}/{relative_path}

下载指定文件。响应带 `Cache-Control: public, max-age=31536000, immutable`。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `release_id` | string | Release ID |
| `relative_path` | string (path) | 相对于下载目录的文件路径 |

**错误**: 404 — 文件不存在；400 — 路径越界。

---

## 10. 数据模型定义

### 10.1 EntityRef

节点引用（轻量）。

```json
{
  "id": "AU:AI:d22fdad88d35b630b33716b8",
  "label_original": "GLYPHOSATE",
  "label_en": "GLYPHOSATE"
}
```

### 10.2 CountryData

```json
{
  "jurisdiction": "AU",
  "jurisdiction_name": "Australia",
  "sovereign_country": "Australia",
  "site_id": "apvma_pubcris",
  "official_url": "https://portal.apvma.gov.au/pubcris",
  "source_file": "...",
  "source_sha256": "58970d...",
  "source_snapshot_eligible": true,
  "source_rows": 18555,
  "skipped_rows": 0,
  "nodes": 67763,
  "edges": 532220,
  "broken_edges": 0,
  "graph_scope": "one jurisdiction + one official website",
  "language": "en",
  "iso3": "AUS",
  "map_id": "036",
  "coverage": { /* CoverageRecord, 见 §10.4 */ }
}
```

### 10.3 EdgeData

```json
{
  "id": "AU:EDGE:...",
  "start_id": "AU:PROD:...",
  "predicate": "containsActiveIngredient",
  "end_id": "AU:AI:...",
  "jurisdiction": "AU",
  "source_record_id": "RAW:...",
  "source_url": "https://portal.apvma.gov.au/pubcris",
  "properties": {}
}
```

### 10.4 CoverageRecord

```json
{
  "jurisdiction": "AU",
  "source_language": "en",
  "records": "18555",
  "crop_source": "0.676044",
  "target_source": "0.676044",
  "active_source": "0.999784",
  "formulation_source": "1.0",
  "crop_english": "0.676044",
  "target_english": "0.676044",
  "active_english": "0.999784",
  "formulation_english": "1.0",
  "crop_english_given_source": "1.0",
  "target_english_given_source": "1.0",
  "active_english_given_source": "1.0",
  "formulation_english_given_source": "1.0"
}
```

### 10.5 EntityData

继承 `EntityRef` 并扩展：

```json
{
  "id": "AU:AI:d22fdad88d35b630b33716b8",
  "label_original": "GLYPHOSATE",
  "label_en": "GLYPHOSATE",
  "type": "ActiveIngredientLocal",
  "jurisdiction": "AU",
  "source_record_id": "RAW:5f2ef3eb26004f52cc81b83f",
  "source_url": "https://portal.apvma.gov.au/pubcris",
  "properties": { "english_status": "official_english_field" }
}
```

### 10.6 GraphData

```json
{
  "nodes": [ /* EntityData[] */ ],
  "edges": [ /* EdgeData[] */ ]
}
```

### 10.7 RegistrationUseData

```json
{
  "use_id": "AU:USE:...",
  "jurisdiction": "AU",
  "product_id": "AU:PROD:...",
  "product_label_original": "Roundup",
  "product_label_en": "Roundup",
  "active_ingredients": [ /* EntityRef[] */ ],
  "crops": [ /* EntityRef[] */ ],
  "targets": [ /* EntityRef[] */ ],
  "formulations": [ /* EntityRef[] */ ],
  "registration_status": "approved",
  "registration_date": "2020-01-15",
  "expiry_date": "2025-01-15",
  "pairing_status": "paired",
  "source_record_id": "RAW:...",
  "source_url": "https://portal.apvma.gov.au/pubcris"
}
```

### 10.8 ReleaseData

```json
{
  "release_id": "2026.08.3_federated",
  "schema_version": "1.0",
  "title": "Federated multicountry pesticide registration knowledge graphs",
  "published_at": "2026-08-24",
  "cutoff": "2026-08-20",
  "status": "release_ready",
  "distribution_status": "blocked_pending_manifest_rebuild",
  "known_limitations": ["..."],
  "license": "CC BY 4.0 for project-derived data",
  "inventory": {
    "jurisdictions": 12,
    "source_records": 821183,
    "country_nodes": 1204973,
    "country_edges": 9739818,
    "shared_nodes": 44645,
    "alignment_edges": 48721
  },
  "integrity": {
    "passed": true,
    "checks": { "twelve_country_site_graphs": true, "...": "..." }
  },
  "artifacts": [ /* ReleaseArtifact[] */ ],
  "is_active": true,
  "registry_status": "discovered",
  "registered_at": null
}
```

### 10.9 ReleaseArtifact

```json
{
  "path": "metadata/countries.json",
  "url": "/downloads/2026.08.3_federated/metadata/countries.json",
  "category": "metadata",
  "format": "json",
  "media_type": "application/json",
  "bytes": 16446,
  "sha256": "37b006d3..."
}
```

### 10.10 ComparisonRow

动态键值对对象，列因 `question` 而异。示例（`q1`）：

```json
{
  "crop_label_en": "Wheat",
  "active_ingredient_label_en": "Glyphosate",
  "countries": "AU,CN,US",
  "jurisdiction": "AU"
}
```

---

## 11. 枚举值参考

### 11.1 节点类型 (`entity_type`)

| 类型 | 说明 | 数量 |
|------|------|------|
| `ActiveIngredientLocal` | 有效成分（本地） | 10,380 |
| `CountryJurisdiction` | 国家管辖区 | 12 |
| `CropLocal` | 作物（本地） | 29,878 |
| `FormulationLocal` | 剂型（本地） | 568 |
| `PesticideProduct` | 农药产品 | 163,297 |
| `Registration` | 登记 | 163,208 |
| `RegistrationUse` | 登记用途 | 820,231 |
| `RegulatoryAgency` | 监管机构 | 12 |
| `TargetLocal` | 靶标（本地） | 17,387 |

### 11.2 关系类型 (`predicate`)

| 关系 | 说明 | 数量 |
|------|------|------|
| `containsActiveIngredient` | 包含有效成分 | 842,180 |
| `hasActiveIngredient` | 有有效成分 | 842,180 |
| `hasFormulation` | 有剂型 | 760,753 |
| `hasProduct` | 有产品 | 820,231 |
| `hasRegistration` | 有登记 | 820,231 |
| `hasRegistrationUse` | 有登记用途 | 820,231 |
| `registeredForCrop` | 登记用于作物 | 2,268,251 |
| `registeredForTarget` | 登记用于靶标 | 1,745,518 |
| `regulatesIn` | 监管于 | 12 |
| `usesProduct` | 使用产品 | 820,231 |

### 11.3 管辖区代码 (`jurisdiction`)

| 代码 | 名称 | 语言 | 记录数 |
|------|------|------|--------|
| `AU` | Australia | en | 18,555 |
| `CN` | China | zh | 86,978 |
| `TW` | Taiwan | zh | 291,185 |
| `JP` | Japan | ja | 142,010 |
| `KR` | Korea | ko | 144,050 |
| `US` | United States | en | 57,782 |
| `HU` | Hungary | hu | 878 |
| `IE` | Ireland | en | 1,279 |
| `GB` | United Kingdom | en | 909 |
| `GB-NI` | Northern Ireland | en | 731 |
| `NZ` | New Zealand | en | 59,695 |
| `NL` | Netherlands | nl | 17,131 |

### 11.4 联邦对齐谓词

| 谓词 | 说明 | 数量 |
|------|------|------|
| `lexicalAlignment` | 词法对齐 | 44,672 |
| `exactMatch` | 精确匹配 | 4,049 |
