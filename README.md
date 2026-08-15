# 清华校园智能问答 / Tsinghua Agent

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
5. 项目不是一键复现工程。部分实验需要本地模型、浏览器认证、人工标注、外部数据访问或较大的本地索引；这些凭据、模型权重、浏览器状态和缓存不会进入 Git。
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

## 目录说明

### 根目录

- `README.md`：项目总说明、当前进度、运行边界和目录索引。
- `.gitignore`：排除凭据、浏览器状态、cookie、token、缓存、`node_modules`、模型权重和临时产物。
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
  - `index/`：检索索引、row mapping、index manifest 及必要的模型配置。
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
- `router_v0_2/`：早期 Router V0.2 工作目录的保留副本；正式候选实验以 `experiments/router_v0_2/` 为准。
- `web_search_v0_1/`：早期 Academic Retrieval / Web Search V0.1 代码、配置、结果和报告的保留副本。

## 运行和验证

建议从仓库根目录执行，避免路径解析错误：

```powershell
python scripts/run_evidence_sufficiency_v1_unit_tests.py
python scripts/run_citation_support_v1_unit_tests.py
python scripts/run_answer_generation_v1_unit_tests.py
python scripts/run_e2e_orchestrator_v1_unit_tests.py
```

这些命令会写入相应评估目录的测试结果 JSON，因此运行后应检查 Git 工作区是否出现仅由时间戳或运行时长导致的结果文件变化。涉及模型、浏览器、外部数据或人工审核的实验，应先阅读对应目录的 README、配置和审计说明。

## 版本与边界规则

- V1 冻结工件只允许用于复现、审计和回归，不应静默修改。
- 任何改变 corpus、chunking、embedding、index、retriever config 或 source admission 的工作，都应创建 V2 版本。
- `evaluation/` 中的分数只有在对应报告明确标记为 frozen / validated 时，才能作为阶段结论引用。
- Shadow set、held-out set、人工审核集和历史回归集必须区分，不能混用或将 provisional 结果写成 post-change validation。
- 数据、报告、代码和配置之间应保留 lineage；删除历史工件前必须确认不会破坏审计可追溯性。

## 安全与数据处理

任何 cookie、token、password、API key、`.env`、WebVPN/session、Playwright storage state、浏览器 profile、登录凭据和模型权重都不得进入 Git。相关本地文件由 `.gitignore` 排除；不要为了“整理项目”删除本地认证或缓存数据。

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
