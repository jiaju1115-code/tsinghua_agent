# 清华校园智能问答 / Tsinghua Agent

> **Submission Candidate V1 (2026-08-17).** The candidate runtime combines Frozen RAG Runtime V1, Evidence Sufficiency V1, Citation Support V1, and Natural Uncertainty Runtime Adapter V1. Frozen text artifacts are verified with canonical LF hashing for cross-platform checkout compatibility. Pilot V1 is a validated research candidate and is not part of the submission runtime. Formal held-out E2E and beta/user testing have not been completed.

截至 2026-08-26 的完整进度、已知限制与下一步见 [`docs/current_progress_20260826.md`](docs/current_progress_20260826.md)。

## 独立候选：可信校园事务智能体 V2

src/trusted_campus_agent_v2/ 是 2026-08-30 新建的本地候选链路，增加场景化 Coverage Matrix、校园术语改写、复杂问题拆解、Fast/Full 路由、Dense+BM25、metadata/时效/权威 rerank、四态 Evidence Gate、办事行动清单，以及 DOCX/XLSX/PPTX/PDF 的生成、回读、修改和可选 LLM Tool Calling。它只读冻结 KB V1，public staging 先进入自动复核候选池，不修改或替换 Submission Candidate V1，也没有发布。边界和运行方式见 docs/trusted_campus_agent_v2.md。

### 本地交互体验

从项目根目录执行：

```powershell
python scripts/chat_submission_candidate_v1.py
```

这是 Submission Candidate V1 的本地开发者交互入口，支持 `/help`、`/debug on`、`/debug off`、`/clear` 和 `/exit`。

本项目面向清华校园场景的智能问答，重点解决“回答看起来合理但无法核验”的问题。项目以公开、可追溯的校园资料为基础，建立从数据采集、质量审计、知识库构建、检索、证据充分性判断、引用支持整理到答案生成的分层流水线。

项目的核心原则是：先确认资料和证据是否足够，再决定能否回答；证据不足时必须降级为部分回答或拒答，不能通过模型自由发挥补齐事实。

## 当前状态（截至 2026-08-15）

### 已完成

1. 完成项目目录重构，旧的 `data_first/`、`data_second/` 路径已迁移到当前 `data/`、`evaluation/`、`experiments/` 等目录，详细映射见 [`docs/project_file_map.md`](docs/project_file_map.md)。
2. 完成公开基线与公开扩展数据整理，保留历史运行、审计结果和冻结清单。
3. 完成 Knowledge Base V1 / RAG Retrieval V1 的正式冻结包：语料、标准化文本、分块、索引、来源与 chunk 映射、provenance、配置和校验清单均位于 `data/03_knowledge_base/v1/`。
4. 完成 Evidence Sufficiency Runtime V1：只消费 Retriever V1 的 Top-5 结果，处理 `SUFFICIENT`、`PARTIAL`、`INSUFFICIENT`，并对空证据、冲突证据、无关证据、版本不一致等情况 fail-closed。
5. 完成 Citation Support V1：把通过证据门控的 provenance 整理为可供答案生成使用的 citation support package，并校验 source、chunk、span 和版本关系。
6. 完成 Answer Generation Runtime V1：只消费 Citation Support V1，按 `READY / PARTIAL / BLOCKED` 生成完整回答、部分回答或拒答，并阻止无支持事实、伪造 support ID 和 prompt injection 绕过。
7. 完成 Unified E2E Orchestrator V1：严格按 `RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> ANSWER_GENERATION_V1` 顺序调用一次，不包含 fallback、retry、re-retrieval 或隐式修复。
8. 完成 Router V0.2 与多轮 retrieval、evidence sufficiency、citation、answer generation 实验，保留为候选或历史实验，不混入已冻结的 Retrieval V1 runtime bundle。
9. V1 单元测试已通过：Evidence Sufficiency 10/10、Citation Support 16/16、Answer Generation 23/23、E2E Orchestrator 37/37。

### 尚未完成 / 当前限制

1. `evaluation/e2e_heldout/v1/` 的 held-out E2E 评估集、审查协议和 one-shot runner 已准备，但尚未正式运行；因此当前不能宣称 held-out E2E 通过。
2. `data/06_human_annotation/` 中仍有需要人工复核或 adjudication 的内容，不能视为全部完成的人审闭环。
3. Router V0.2 仍是候选版本；其独立 Shadow Set 结果为变更前的 provisional regression result，后续语义优先级修复尚未在 Shadow Set 上重跑验证。
4. Restricted-stage 数据仍处于研究与准入边界管理阶段，不是当前公开 Knowledge Base V1 的默认运行语料。
5. Knowledge Base V1 / Retrieval V1 所需的冻结 encoder 权重、索引、配置和词表已随仓库发布；但其他实验所需的本地模型、浏览器认证、人工标注、外部数据访问或可再生缓存不保证随仓库提供。凭据、浏览器状态和缓存不会进入 Git。
6. Knowledge Base V1 不应原地修改。若变更语料、chunking、embedding、索引、retriever 配置或来源准入规则，应建立 Knowledge Base V2 / RAG Retrieval V2。

## 当前正式运行链路

```text
公开数据采集
  -> 安全门（来源、凭据、访问边界）
  -> 质量门（字段、文本、重复、结构）
  -> Prompt / 数据审计
  -> Knowledge Base V1
  -> RAG Retrieval V1 Top-5
  -> Evidence Sufficiency V1
  -> Citation Support V1
  -> Answer Generation V1
  -> E2E Orchestrator V1
```

正式链路的运行时入口和冻结工件必须使用 `data/03_knowledge_base/v1/`。`data/04_public_staging/`、历史 RAG 评估和 `experiments/` 中的候选实现只用于审计、回归或研究，不是正式 runtime 的隐式输入。

## 先读什么：不同读者的入口

| 你要做的事 | 建议先读 | 然后查看 | 不要直接把它当成 |
| --- | --- | --- | --- |
| 了解当前项目是否已具备可运行能力 | 本 README 的“当前状态”和“系统契约” | `reports/*_v1_report.md` | 已完成的独立 held-out 效果证明 |
| 复现正式检索与四层运行时 | `data/03_knowledge_base/v1/README.md` | `src/*_v1/`、`scripts/run_*_v1_*.py` | 任意历史 RAG/实验目录 |
| 审计来源、准入和版本完整性 | `reports/knowledge_base_v1_freeze_report.md` | `data/03_knowledge_base/v1/audit/`、`manifests/`、`provenance/` | 仅凭 README 结论 |
| 开展下一轮数据/检索实验 | `docs/project_file_map.md` | `data/04_kb_expansion_candidate/`、`experiments/` | 对 KB V1 的原地编辑 |
| 执行 E2E 评估 | `reports/e2e_evaluation_v1_readiness_report.md` | `evaluation/e2e_heldout/v1/`、`evaluation/e2e/v1/` | 已通过的正式 benchmark |
| 处理人工复核 | `data/06_human_annotation/` 中的状态与工作簿 | 对应 `audit/`、`human_check/` 文件 | 可自动升级为 gold truth 的标签 |

## 正式冻结包：可验证的技术事实

当前正式运行基础是 `KNOWLEDGE_BASE_V1` 和 `RAG_RETRIEVAL_V1`，两者都在 `data/03_knowledge_base/v1/`。下面的数值来自知识库冻结报告，用于识别当前版本，不应被解读为端到端效果指标。

| 项目 | 当前冻结值 | 含义 |
| --- | ---: | --- |
| 纳入 runtime 的来源 | 122 | 119 条公开来源 + 3 条 restricted 来源；review/reject/unresolved 不进入 runtime |
| runtime 外排除来源 | 47 | 包括质量、时效、安全或审查状态不满足要求的候选 |
| 文本 chunk 数 | 488 | 每个 chunk 都映射到稳定 source ID、字符边界和正文 hash |
| 检索索引 | 488 行 dense embedding | 每行与一个 chunk 一一对应，由 `row_mapping.jsonl` 固定顺序 |
| embedding 模型 | `BAAI/bge-small-zh-v1.5` | 固定 revision；模型权重 `index/model/model.safetensors`、配置、词表、索引与 manifest 都有 hash 审计 |
| 检索策略 | Dense cosine，Top-K=5 | 按分数降序、chunk ID 升序打破平分；不启用 bilingual expansion |
| 历史 RAG V0/V1 | 238 sources / 717 chunks | 仅作历史比较与 provenance，不是 V1 runtime 的依赖 |

### Knowledge Base V1 内部结构与追溯关系

```text
原始/已审核来源
  -> 准入决定（audit/eligibility_decisions.jsonl）
  -> canonical source（sources/）
  -> 标准化文本与 provenance（provenance/）
  -> chunk（chunks/chunks.jsonl）
  -> source/chunk manifest（manifests/）
  -> embedding + row mapping（index/）
  -> KB/Retriever freeze manifest（audit/）
```

- 每个 runtime source 使用稳定的 `canonical_source_id`：公开来源以 `KBV1-PUB-*` 命名，restricted 来源以 `KBV1-RES-*` 命名。
- 每个 chunk 使用稳定 chunk ID，记录所属 source、顺序、字符范围和文本 hash；`source_to_chunk_mapping.jsonl` 连接 source 与 chunk。
- `provenance/source_provenance.jsonl` 记录标题、URL/domain、来源类型、公开/受限属性、准入原因、审核/质量/安全工件路径与 hash，支持从回答证据回溯到来源。
- `audit/knowledge_base_v1_freeze.json`、`audit/rag_retrieval_v1_freeze.json` 以及对应 `.sha256` 文件是版本锁定点；运行前应由 adapter 校验，而不是只依赖路径名称。
- `index/model/model.safetensors` 是当前 RAG Retrieval V1 使用的冻结 encoder 权重（95,827,648 bytes，SHA256 以 freeze report/manifest 为准），已作为唯一允许提交的模型权重例外纳入仓库；其他权重仍由 `.gitignore` 排除。

### 已发布的 Markdown 数据口径

“正式运行语料”与“仓库中保留的数据资产”不是同一个集合。KB V1 只有 122 份经过准入的 Markdown 来源；这是一项有意的 fail-closed 选择，并不表示项目只采集了 122 份文档。

| 路径 | 受 Git 跟踪的 Markdown 数 | 用途 |
| --- | ---: | --- |
| `data/01_public_baseline/` | 6 | 初始公开/门户基线 |
| `data/02_public_expansion/` | 405 | 公开扩展 V1/V2、审计与候选资料 |
| `data/03_knowledge_base/v1/` | 123 | 122 份正式 runtime source + 知识库 README |
| `data/04_public_staging/` | 235 | 已冻结的准入前公开候选语料 |
| `data/05_restricted_expansion/` | 20 | restricted 阶段研究与准入资料 |
| `data/06_human_annotation/` | 2 | 人工审核说明性 Markdown；其余多为工作簿/结构化状态文件 |
| **`data/` 合计** | **792** | 全部受 Git 追踪的数据 Markdown |

仓库全部路径（包含 `docs/`、`reports/`、`experiments/`、`evaluation/` 等）的受 Git 追踪 Markdown 合计为 1,049 份。正式 Retriever 只读取 `data/03_knowledge_base/v1/`，不能因为其它 Markdown 已上传就把它们自动当成运行时知识。

## 系统契约与各层责任

项目将“检索到文本”“证据足以回答”“引用可追溯”“答案可发布”拆成独立层。任何层不能替另一层越权补全。

| 层 | 代码/配置位置 | 接收什么 | 产出什么 | 明确不做什么 |
| --- | --- | --- | --- | --- |
| Retrieval V1 | `src/retrieval_v1/adapter.py` 与 `data/03_knowledge_base/v1/` | `query`、`case_id` | 有序 Top-5 chunks、source/chunk IDs、scores、版本与错误字段 | 不读 staging、不在线搜索、不判定证据充分性、不生成答案 |
| Evidence Sufficiency V1 | `src/evidence_sufficiency_v1/` | query + 严格 Top-5 retrieval result | `SUFFICIENT/PARTIAL/INSUFFICIENT`、required points、缺失属性、support spans、reason codes | 不检索、不调用网络/模型、不生成答案、不对最终 citation 作正确性背书 |
| Citation Support V1 | `src/citation_support_v1/` | Retriever V1 与 Evidence V1 的完成对象 | 分组后的 support units、provenance、source/chunk/span 校验结果 | 不生成自然语言答案、不把弱支持伪装为强支持 |
| Answer Generation V1 | `src/answer_generation_v1/` | Citation Support package | `FULL_ANSWER/PARTIAL_ANSWER/REFUSAL` 与结构化结果 | 不绕过 support package，不补写无支持事实 |
| E2E Orchestrator V1 | `src/e2e_orchestrator_v1/` | 请求及四层配置/对象 | 一次有序的完整运行与跨层校验记录 | 不 fallback、不 repair、不 retry、不 re-retrieve、不运行 held-out case |

### Evidence Sufficiency V1 的决策语义

Evidence V1 是一个确定性、fail-closed 的词法/结构化支持代理，不是语义蕴含模型，也没有伪造的校准置信度。

| 决策 | 对应策略 | 触发条件 |
| --- | --- | --- |
| `SUFFICIENT` | `ALLOW_FULL_ANSWER` | 所有最小核心点有支持、请求属性完整、没有未解决冲突 |
| `PARTIAL` | `ALLOW_PARTIAL_ANSWER` | 至少一个核心点可安全支持，但其他核心点或请求属性不完整 |
| `INSUFFICIENT` | `REQUIRE_REFUSAL` | 没有任何核心点可安全支持，或证据冲突、输入无效、版本不匹配、检索失败 |

它的 10 项单元测试覆盖三种决策、缺失属性、可选信息、空/无关/冲突证据、畸形输入、版本不匹配和确定性。历史兼容性回归不是 held-out 评估，且存在明显过度拒答风险；因此 README 不将其分数写作生产准确率。

### Citation Support 与 Answer Generation V1 的边界

Citation Support V1 只整理已通过 Evidence 门控的来源、chunk 与 span，保证来源关系可追溯；它不是“引用越多越好”的格式化工具。Answer Generation V1 将上游状态映射为：

- `READY`：输出 `FULL_ANSWER`；
- `PARTIAL`：输出受支持范围内的 `PARTIAL_ANSWER`，并保留缺失信息；
- `BLOCKED`：输出 `REFUSAL`，且不调用模型绕过上游结论。

Answer Generation V1 的测试覆盖未支持事实、伪造 support ID、版本错误、模型无效 JSON、prompt injection、受限元数据泄露、超时/异常与可重复性。这里的“通过”表示契约与保护逻辑被测试覆盖，不表示已经完成独立人工质量评估。

## 数据生命周期、状态与准入规则

```text
采集/候选资料
  -> 安全与质量检查
  -> 人工或规则审查
  -> staging / candidate（可继续研究）
  -> 明确准入 + manifest + hash
  -> Knowledge Base 新版本（可作为正式 runtime）
```

1. 资料进入 `data/01_public_baseline/`、`data/02_public_expansion/`、`data/04_public_staging/` 或 restricted 候选区时，仍只是采集/候选资产。
2. 公开 V2 候选只有同时满足既有准入、质量、正文、时效和重复性条件时，才可能进入 KB V1；restricted 候选还必须满足安全门控。
3. `review`、`reject`、`unresolved`、时效不清或内容不合格的记录必须 fail-closed，不能因为文本“看起来相关”而加入正式语料。
4. 人工检查标签是 `human_reference` 或 adjudication 记录，不自动等同于绝对 gold truth；它们应保留来源和分歧信息。
5. 新来源或任何分块、索引、模型、配置的变动都必须通过新的候选、审计、manifest 和冻结流程，版本号升级到 V2（或更高）。

## 项目目录总览

以下目录树用于快速定位。`[冻结]` 表示正式版本的不可原地改写工件；`[候选/实验]` 表示可研究但不能直接用于正式结论；`[历史]` 表示保留以支持追溯与回归。

```text
tsinghua_ai/
├── archive/                               [历史] 已弃用或非主流程资料
├── configs/                               项目级配置
├── data/
│   ├── 01_public_baseline/                [冻结] 初始公开/门户采集基线
│   ├── 02_public_expansion/
│   │   ├── v1/                            [历史] 公开扩展早期运行
│   │   └── v2/                            [冻结] 审计后的公开扩展与人审工件
│   ├── 03_knowledge_base/v1/              [冻结/正式] KB V1 + Retriever V1 bundle
│   ├── 04_kb_expansion_candidate/         [候选] 下一版知识库候选资料
│   ├── 04_public_staging/                 [冻结/非运行时] 准入前公开语料
│   ├── 05_restricted_expansion/v1/        [研究] restricted 准入、安全与内容资料
│   └── 06_human_annotation/               [进行中] 人审、标注、adjudication 状态
├── docs/                                  路径地图、开发史和协作文档
├── evaluation/
│   ├── answer_generation/{runtime_v1,v0,v1}/
│   ├── citation/{v1,v2}/
│   ├── citation_support/v1/               [冻结] 引用支持契约与验证
│   ├── e2e/v1/                            [准备中] exclusion registry 等 benchmark 前置物
│   ├── e2e_heldout/v1/                    [未运行] held-out 数据与审查协议
│   ├── e2e_orchestrator/runtime_v1/       [冻结] 编排器契约与完整性工件
│   ├── evidence_sufficiency/v1/           [冻结] 证据门控配置、测试、审计与回归
│   ├── model_selection/                   [历史/实验] 模型选择资料
│   ├── prompt_v3_2_blind_test_v1/         [冻结] Prompt V3.2 blind-test 资料
│   ├── rag/{v0,v1}/                       [历史] 检索/RAG 评估
│   └── retrieval_diagnostic_v1/           Retrieval V1 诊断资料
├── experiments/                           [候选/历史] 可追溯实验，不是 runtime 默认输入
│   ├── content_extraction_fix_v1/         抽取修复研究
│   ├── content_quality_diagnostic_v1/     内容质量诊断
│   ├── e2e12_router_v0_2/                 E2E-12 与路由器试验
│   ├── evaluation_reconciliation_v0_1/    指标/结果对账
│   ├── evidence_benchmark_expansion_v0_2/ 证据 benchmark 扩展
│   ├── evidence_sufficiency_v0_1..v0_4/  证据门控历史迭代
│   ├── generation_citation_eval_v0/       生成与引用实验
│   ├── public_rebuild_v1/                 公开数据重建实验
│   ├── retriever_v2/                      检索器候选版本
│   ├── review_outputs/                    人工/自动 review 的导出结果
│   ├── router_v0_2/                       Router V0.2 候选实现和评估
│   ├── training_v0/                       早期训练资料
│   ├── web_search_v0/                     Web Search 历史实验
│   └── web_search_v0_followup/            后续学术检索与误差分析
├── prompts/                               Prompt、模板与审计相关资产
├── reports/                               阶段结论和 freeze/readiness 报告
├── router_v0_2/                           本地兼容 junction（已忽略；canonical 路径为 experiments/router_v0_2/）
├── scripts/                               构建、freeze、integrity、unit/integration/regression 命令
├── src/                                   正式 V1 runtime 与共用模块
├── tests/                                 通用测试
├── web_search_v0_1/                       本地兼容 junction（已忽略；canonical 路径为 experiments/web_search_v0_followup/）
├── .gitignore                             凭据、缓存和非冻结模型权重等排除规则
└── README.md                              本项目说明
```

## 目录说明

### 根目录

- `README.md`：项目总说明、当前进度、运行边界和目录索引。
- `.gitignore`：排除凭据、浏览器状态、cookie、token、缓存、`node_modules`、临时产物和非冻结模型权重；唯一例外是 KB V1 的 `index/model/model.safetensors`。
- `configs/`：跨阶段配置及项目级运行参数。
- `prompts/`：Prompt 版本、模板和相关审计资料。
- `docs/`：项目结构、迁移关系、开发历史和协作说明。
- `tests/`：通用测试与跨模块测试。
- `scripts/`：构建知识库、捕获输入快照、冻结工件、执行 V1 单元/集成/回归测试的操作脚本。

### 数据与知识库：`data/`

- `data/01_public_baseline/`：最初的公开资料/门户采集基线，包含基线数据、证据和审计产物，已冻结。
- `data/02_public_expansion/`：公开扩展数据。
  - `v1/`：历史公开扩展运行。
  - `v2/`：审计后的公开扩展结果；当前包含 Public V3.2 人工复核、disagreement、metrics 和 report 等工件。
- `data/03_knowledge_base/v1/`：当前唯一正式 Knowledge Base V1 / RAG Retrieval V1 runtime bundle。
  - `audit/`：KB 与 Retriever 冻结清单、资格判断、输入不变性和 hash 校验。
  - `chunks/`：规范化后的 chunk 数据。
  - `config/`：chunking 与 retriever 配置。
  - `index/`：检索索引、row mapping、index manifest，以及 BGE encoder 的冻结权重、词表和模型配置。
  - `manifests/`：source、chunk、source-to-chunk 的关系清单。
  - `provenance/`：来源元数据和标准化原文，用于追溯证据。
  - `README.md`：知识库版本边界和使用说明。
- `data/04_public_staging/`：公开候选资料 staging 区，只用于准入前准备和审计，不是 V1 runtime 输入。
- `data/04_kb_expansion_candidate/`：下一轮知识库扩展候选资料，尚未进入 V1。
- `data/05_restricted_expansion/v1/`：restricted 阶段的计划、准入、审计、候选资料、原文和报告。
- `data/06_human_annotation/`：人工审核、标注、adjudication 和知识状态资料；其中部分仍需人工复核。

### 源码：`src/`

- `src/retrieval_v1/`：Retrieval V1 适配层，读取冻结的 KB V1 和 Top-5 检索结果契约。
- `src/evidence_sufficiency_v1/`：证据充分性门控；不负责检索、生成或最终引用渲染。
- `src/citation_support_v1/`：引用/支持门控；校验 provenance 并生成 citation-ready support units。
- `src/answer_generation_v1/`：答案生成门控；只接收 Citation Support package，并输出结构化答案状态。
- `src/e2e_orchestrator_v1/`：统一 E2E 编排器；校验四层契约并严格按规定顺序执行。
- `src/llm/`：模型适配与调用相关的通用代码。
- `src/reviewer/`：人工审核或审查辅助逻辑。
- `src/utils/`：跨模块工具函数。

### 评估与冻结工件：`evaluation/`

- `evaluation/evidence_sufficiency/v1/`：Evidence Sufficiency V1 的配置、测试、审计、历史回归、泄漏检查和冻结结果。
- `evaluation/citation_support/v1/`：Citation Support V1 的配置、lineage、validation、integrity 和冻结工件。
- `evaluation/answer_generation/runtime_v1/`：正式 Answer Generation V1 的 prompt、配置、审计、验证和冻结结果。
- `evaluation/e2e_orchestrator/runtime_v1/`：Orchestrator V1 的 schema、protocol、contract audit、integrity 和冻结工件。
- `evaluation/e2e_heldout/v1/`：待运行的 held-out E2E V1 数据集、污染审计、人工评估协议和 one-shot runner。
- `evaluation/e2e/v1/`：E2E benchmark 准备资料，例如历史 QA exclusion registry；不等同于已经完成的 held-out benchmark。
- `evaluation/retrieval_diagnostic_v1/`：Retrieval V1 的诊断和回归资料。
- `evaluation/rag/`：历史 RAG v0/v1 评估，不是正式 V1 runtime 依赖。
- `evaluation/answer_generation/`、`evaluation/citation/`、`evaluation/prompt_v3_2_blind_test_v1/`、`evaluation/model_selection/`：历史或实验性答案生成、引用、Prompt 和模型选择评估。

### 实验、报告与历史资料

- `experiments/`：可追溯的研究、诊断、重建、候选模型和 benchmark 扩展实验。这里的结果不能自动升级为正式 runtime 结论。
  - `experiments/router_v0_2/`：Router V0.2 候选实现、配置、评估和失败案例。
  - `experiments/retriever_v2/`：Retriever V2 候选实验，尚未替代 Retriever V1。
  - `experiments/evidence_sufficiency_v0_1/` 至 `v0_4/`：证据充分性历史迭代。
  - `experiments/generation_citation_eval_v0/`：答案生成与引用评估实验。
  - `experiments/e2e12_router_v0_2/`：路由器与 E2E-12 相关评估。
  - `experiments/public_rebuild_v1/`：公开数据重建实验。
  - `experiments/web_search_v0/`、`web_search_v0_followup/`：Web Search / Academic Retrieval 历史实验及误差分析。
- `reports/`：面向项目决策的汇总报告，包括 Knowledge Base、Evidence Sufficiency、Citation Support、Answer Generation 和统一 E2E readiness 报告。
- `archive/`：不再属于主流程但为审计和历史追溯保留的旧资料。
- `router_v0_2/`、`web_search_v0_1/`：部分本地工作区会创建这两个 Windows junction 以兼容早期路径；它们指向 `experiments/` 下的 canonical 目录，已由 `.gitignore` 排除，不能作为第二份仓库内容提交。

## 运行和验证

建议从仓库根目录执行，避免路径解析错误：

```powershell
python scripts/run_evidence_sufficiency_v1_unit_tests.py
python scripts/run_citation_support_v1_unit_tests.py
python scripts/run_answer_generation_v1_unit_tests.py
python scripts/run_e2e_orchestrator_v1_unit_tests.py
```

这些命令会写入相应评估目录的测试结果 JSON，因此运行后应检查 Git 工作区是否出现仅由时间戳或运行时长导致的结果文件变化。涉及模型、浏览器、外部数据或人工审核的实验，应先阅读对应目录的 README、配置和审计说明。

### 可用脚本按目的索引

| 目的 | 脚本 | 说明 |
| --- | --- | --- |
| 构建新知识库候选/正式包 | `scripts/build_knowledge_base_v1.py` | 现有 V1 的构建和冻结流程参考；不要用它覆写已冻结 V1 |
| 校验 KB V1 资产 | `scripts/verify_knowledge_base_v1_integrity.py` | 对 manifest、chunk、index、配置和 freeze sidecar 做完整性检查 |
| Retrieval V1 回归诊断 | `scripts/run_rag_retrieval_v1_regression.py` | 历史功能回归；不是 held-out 检索效果评估 |
| Evidence V1 单元/集成/历史回归 | `scripts/run_evidence_sufficiency_v1_{unit_tests,integration,historical_regression}.py` | 分别验证契约、Retriever 接口与历史兼容性；三者结论不可混同 |
| Citation Support V1 单元/集成 | `scripts/run_citation_support_v1_{unit_tests,integration}.py` | 校验 citation support package 的来源、span 与版本约束 |
| Answer Generation V1 单元/集成 | `scripts/run_answer_generation_v1_{unit_tests,integration}.py` | 校验生成层 fail-closed 行为与跨层接口 |
| E2E Orchestrator V1 单元/集成 | `scripts/run_e2e_orchestrator_v1_{unit_tests,integration}.py` | 校验编排顺序、跨层 schema 与错误处理 |
| 冻结输入快照/完整性 | `scripts/capture_*_input_snapshot.py`、`scripts/capture_e2e_orchestrator_integrity.py` | 在运行前后记录输入与工件不变性 |
| 完成阶段 freeze | `scripts/finalize_{evidence_sufficiency,citation_support,answer_generation,e2e_orchestrator}_v1.py` | 生成该阶段的正式审计/冻结产物；应在确认输入版本后使用 |
| 检查证据泄漏 | `scripts/audit_evidence_sufficiency_v1_leakage.py` | 审计历史数据、query family 和 calibration 的交叉使用 |

### 建议的本地验证顺序

1. `git status -sb`：确认当前修改范围，避免把缓存、模型或实验临时输出误纳入提交。
2. `python scripts/verify_knowledge_base_v1_integrity.py`：确认 KB V1、索引和 manifest 未被破坏。
3. 运行四个 V1 单元测试脚本；若需要验证真实接口，再运行相应 integration 脚本。
4. 检查评估目录中新生成的 JSON；区分“测试通过”与“仅时间戳变化”。
5. 若改动涉及语料、模型或配置，停止将其称为 V1，改在候选目录构建新版本并完成审计。

### 环境与依赖边界

- 以仓库根目录为工作目录；新代码应使用 root-relative path，不能写入 `D:\\python_projects\\...` 一类绝对路径。
- V1 Retriever 的索引、冻结 BGE encoder 权重、词表、模型配置和 freeze 工件已随项目路径组织；下载缓存和其它可再生运行缓存仍由 `.gitignore` 排除。
- 某些历史 Web Search、浏览器/门户采集与 restricted 研究需要外部服务或登录态。不要提交 cookie、storage state、token、密码、浏览器 profile 或 API key。
- `node_modules/`、`__pycache__/`、`tmp/`、`cache/`、`.pytest_cache/` 等均为本地产物；它们不是项目交接内容。
- 项目当前没有被 README 宣称为“单命令、全平台、完全离线复现”的依赖锁定方案。新增自动化前应将 Python/Node 依赖、模型版本和操作系统差异写入新的环境文档或 lockfile。

## 进度台账与下一步的完成标准

| 工作流 | 当前状态 | 已交付资产 | 下一步完成标准 |
| --- | --- | --- | --- |
| 公开数据基线/扩展 | 已完成并保留 | `data/01_public_baseline/`、`data/02_public_expansion/v2/`、审计与人审工件 | 新增公开来源时走新版本准入，不回写历史冻结结果 |
| KB V1 / Retriever V1 | 已冻结 | 122 sources、488 chunks、index、manifest、provenance、integrity report | 新语料/索引需求创建 KB/Retriever V2；V1 仅复现与审计 |
| Evidence Sufficiency V1 | 已冻结，保守基线 | deterministic 三态 runtime、10 项单测、接口验证、历史兼容性报告 | 用真正独立的标注/held-out 集校准或替换语义蕴含方案；不得把历史回归当作泛化证明 |
| Citation Support V1 | 已冻结 | runtime、lineage/validation/integrity 工件、16 项单测 | 结合独立人工审查验证 claim-to-evidence 支持正确性 |
| Answer Generation V1 | 已冻结 | runtime、prompt/config/audit、23 项单测 | 在独立 E2E 包中评估正确性、faithfulness、部分回答与拒答行为 |
| E2E Orchestrator V1 | 已冻结 | 四层顺序契约、schema、protocol、完整性工件、37 项单测 | 只在已冻结 held-out benchmark 上执行，不向 orchestrator 添加隐式 repair |
| Router V0.2 | 候选 | `experiments/router_v0_2/`、失误分析、shadow 记录 | 在不使用原 Shadow item 调参的前提下进行新独立验证；明确 route 到 downstream action 的产品边界 |
| Held-out E2E V1 | 准备中，未运行 | `evaluation/e2e_heldout/v1/` 的数据、污染审计、审查协议与 runner | 完成独立题集、双人 reference/adjudication、运行清单与正式一次性执行 |
| 人工审核 | 进行中 | `data/06_human_annotation/` 及 public V3.2 human-check 工件 | 清理 `needs-review`/分歧状态并记录最终 adjudication，不混淆 human reference 与 gold |
| KB/检索扩展 | 候选 | `data/04_kb_expansion_candidate/`、`experiments/retriever_v2/` | 完成来源准入、版本化 manifest、完整性检查和独立评估后，才考虑升级 |

### Held-out E2E 尚未运行的原因

项目已准备 E2E 的目录和协议，但正式执行仍必须满足以下前提。没有满足这些条件时，任何运行都只能叫 dry run 或诊断，不能叫正式 E2E 结论。

1. 每条题目必须与历史 Router、RAG、Evidence、Citation、Answer、Prompt 校准和错误分析样本做 exact、normalized、template/semantic、Query+Evidence 四类泄漏检查。
2. 每条题目应在运行前冻结 route、required points、requested attributes、参考 action、允许证据范围和 temporal validity。
3. 至少两名审核者独立完成 reference package；分歧要保留并由 adjudication 明确处理。
4. 运行时必须记录 corpus/retriever/model/prompt/config hash、Git commit、输入清单、每层结构化输出、错误、延迟、retry/cache 状态。
5. 指标口径必须在运行前固定，特别是 correctness、faithfulness、unsupported claim、correct refusal、false refusal 和 E2E success 的分子/分母。

## 报告的正确使用方式

| 报告 | 可以得出的结论 | 不可以得出的结论 |
| --- | --- | --- |
| `knowledge_base_v1_freeze_report.md` | KB V1 的来源、chunk、index、Retriever 配置和完整性已冻结 | 完整 E2E 已通过，或检索对新问题的效果已被独立评估 |
| `evidence_sufficiency_v1_report.md` | 确定性三态门控有明确契约、测试和 fail-closed 行为 | 已实现真正 semantic entailment，或具备高回答覆盖率 |
| `citation_support_v1_report.md` | Citation Support V1 的 provenance/lineage 约束已形式化 | 最终自然语言中每一个 citation 的人工正确率已获独立证明 |
| `answer_generation_v1_report.md` | 生成层的输入、策略、审计和失败保护已冻结 | 已在独立盲测上证实回答质量或事实正确率 |
| `unified_e2e_orchestrator_v1_report.md` | 四层调用顺序与跨层契约可被统一执行和审计 | held-out E2E benchmark 已经完成 |
| `e2e_evaluation_v1_readiness_report.md` | 正式 E2E 的风险、协议和最小前置条件已经梳理 | 已满足所有 GO 条件；该报告应按其自身状态阅读 |

## 版本与边界规则

- V1 冻结工件只允许用于复现、审计和回归，不应静默修改。
- 任何改变 corpus、chunking、embedding、index、retriever config 或 source admission 的工作，都应创建 V2 版本。
- `evaluation/` 中的分数只有在对应报告明确标记为 frozen / validated 时，才能作为阶段结论引用。
- Shadow set、held-out set、人工审核集和历史回归集必须区分，不能混用或将 provisional 结果写成 post-change validation。
- 数据、报告、代码和配置之间应保留 lineage；删除历史工件前必须确认不会破坏审计可追溯性。

## 安全与数据处理

任何 cookie、token、password、API key、`.env`、WebVPN/session、Playwright storage state、浏览器 profile 和登录凭据都不得进入 Git。模型权重默认也不得提交；唯一例外是为了离线复现 RAG Retrieval V1 而冻结并记录 hash 的 `data/03_knowledge_base/v1/index/model/model.safetensors`。相关本地文件由 `.gitignore` 排除；不要为了“整理项目”删除本地认证或缓存数据。

项目数据包含公开资料、实验记录和人工审核工件。发布或共享前应确认来源许可、隐私边界和 restricted 数据准入状态；restricted 数据不能因为出现在本地目录中就自动进入公开 Knowledge Base。

## 后续计划

1. 完成 `data/06_human_annotation/` 中待复核记录的人工 adjudication。
2. 运行并审查 `evaluation/e2e_heldout/v1/` 的 held-out E2E 评估。
3. 在不污染 Shadow Set 的前提下，重新验证 Router V0.2 的语义优先级修复。
4. 根据评估结果决定是否启动 Knowledge Base V2、Retriever V2 或新的公开扩展版本。
5. 为正式 runtime 补充更稳定的依赖锁定、环境说明和自动化 CI 校验。

## 相关文档

- [`docs/project_file_map.md`](docs/project_file_map.md)：旧路径到新路径的迁移表、active/legacy 边界。
- [`docs/development_history.md`](docs/development_history.md)：项目阶段和历史演进记录。
- [`reports/knowledge_base_v1_freeze_report.md`](reports/knowledge_base_v1_freeze_report.md)：Knowledge Base V1 冻结报告。
- [`reports/evidence_sufficiency_v1_report.md`](reports/evidence_sufficiency_v1_report.md)：Evidence Sufficiency V1 报告。
- [`reports/citation_support_v1_report.md`](reports/citation_support_v1_report.md)：Citation Support V1 报告。
- [`reports/answer_generation_v1_report.md`](reports/answer_generation_v1_report.md)：Answer Generation V1 报告。
- [`reports/unified_e2e_orchestrator_v1_report.md`](reports/unified_e2e_orchestrator_v1_report.md)：统一 E2E Orchestrator V1 报告。
