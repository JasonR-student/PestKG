# PestKG 论文制图模块

该模块从冻结发布版 `2026.08.3_federated` 生成可复现的论文图。图形使用真实发布统计、APVMA 样例子图以及 Q1 跨国比较结果，不从参考图片复制版式或数据。

## 产物

- `figure_01_dataset_landscape`：12 个司法辖区的数据量、图规模和字段完整度。
- `figure_02_single_site_apvma`：APVMA 单一官方网站到登记知识图谱的局部链路。
- `figure_03_federated_chebi_agrovoc`：国家本地实体经语义对齐连接 ChEBI 与 AGROVOC。
- `figure_04_pestkg_storyboard`：适合论文主文的三联综合图。
- `figure_05_apvma_entity_relationship`：APVMA 单网站实体-关系-属性模型。
- `figure_06_bipartite_and_projections`：司法辖区-共享实体二部网络、国家投影和实体投影。
- `figure_07_multisite_external_chain`：中国大陆、中国台湾、日本、韩国官方网站经 PestKG 连接 ChEBI/AGROVOC。
- `figure_08_complete_main_figure`：约 183 mm 双栏宽的完整论文主 Figure。
- `CAPTIONS_EN.md`、`CAPTIONS_ZH.md`：中英文图注。
- `FIGURE_MANIFEST.json`：输入数据与全部图片的 SHA-256、格式、大小和运行模式。
- `LOCAL_RUN_2026-09-02.md`：本机验证结果和未完成的容器运行条件。
- `delivery/pestkg_figure_delivery_2026-09-02.zip`：完整 Figure 交付包。

每张图同时输出：

- SVG：首选编辑格式，文字和线条保持矢量。
- PDF：投稿与排版格式。
- PNG：600 dpi 审阅格式。

## 本机直接生成

```powershell
.\.venv\Scripts\python.exe -m pip install -r research\figures\requirements.txt
.\.venv\Scripts\python.exe research\figures\generate_figures.py
.\.venv\Scripts\python.exe research\figures\generate_extended_figures.py
.\.venv\Scripts\python.exe research\figures\build_delivery_package.py
```

此方式从发布 CSV 读取数据，适合 Docker Desktop 未运行时快速成图。

## 通过 Neo4j 生成

启动 Docker Desktop 后执行：

```powershell
docker compose -f research\figures\docker-compose.yml up --build --abort-on-container-exit renderer
```

流程会：

1. 启动隔离的 Neo4j 实例，浏览器地址为 `http://localhost:7475`。
2. 将 203 个样例节点和 235 条样例关系装载为 `PaperSample` 子图，并将 200 条 Q1 结果装载为独立的 `PaperProjection` 派生层。
3. 通过 Cypher 抽取 Fortin Herbicide 三跳邻域和 Q1 投影数据。
4. 在 `artifacts/research/figures/output` 生成图 1-8，并构建最终 ZIP 交付包。

Neo4j Browser 登录信息：用户名 `neo4j`，密码 `pestkg-paper`。该实例使用独立数据卷，不修改生产 PestKG 数据卷。

## 完整数据库查询

`neo4j/queries.cypher` 包含两个查询契约：

- 单站点三跳子图，最多返回 400 条路径。
- 完整发布版的 `exactMatch|lexicalAlignment` 联邦关系查询。

本仓库的浏览样例有意省略完整联邦边，因此联合图从 Q1 结果读取真实共享 ID。Q1 不保留逐行对齐谓词，图中统一写作 `semantic alignment`，不会猜测具体谓词。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s research\figures\tests -v
```

测试锁定发布规模、APVMA 登记链的来源追溯、48 条作物关系，以及 ChEBI/AGROVOC 标识符真实性。
