# 清华校园智能问答 / Tsinghua Agent

以权威校园资料、可追溯检索与 RAG/答案生成评测为基础，降低清华校园场景问答的幻觉风险。

## 当前状态

- Completed/Frozen: public baseline、public expansion (v1/v2)、public staging、Restricted Expansion V1、Prompt V3.2 盲测与其审计材料。
- Experimental: retrieval/RAG、citation、model selection、answer generation，以及 `experiments/` 下的诊断和重建工作。
- Pending human review: `data/06_human_annotation/` 中明确标记为 needs-review 的材料。

## 技术路线

Data acquisition → Safety Gate → Quality Gate → Prompt Audit → Knowledge Base → Retrieval → RAG → Answer Generation → Evaluation.

## 目录

- `data/01_public_baseline/`: 初始公开/门户采集基线（冻结）。
- `data/02_public_expansion/`: 公开扩展，`v1` 为历史运行、`v2` 为审计后的正式结果。
- `data/04_public_staging/`: 公开候选的冻结 staging 语料与 manifest。
- `data/05_restricted_expansion/v1/`: restricted 阶段的计划、gate、audit、候选、正文与报告。
- `data/06_human_annotation/`: 人工审核和知识状态。
- `evaluation/`: Prompt V3.2、retrieval/RAG、citation、model selection、answer-generation 实验。
- `experiments/`: 可追溯的诊断、重建和探索性实验；`archive/` 存放不再是主流程的历史资产。

更完整的迁移地图见 `docs/project_file_map.md`，阶段时间线见 `docs/development_history.md`。

## 复现

当前仓库并非一键复现项目：部分评测需要本地模型下载、受限系统访问或人工标注。先根据目标阶段读取其 README 和脚本；以项目根目录为工作目录，使用相对路径。模型权重与可再生缓存不会进入 Git。

## 团队

团队成员信息由项目维护者在 GitHub 仓库设置中维护；本文件不猜测成员姓名或 GitHub 用户名。

## 安全

Cookie、token、password、API key、`.env`、WebVPN/session、Playwright storage state、浏览器 profile 和任何可登录凭据绝不进入 Git；相关本地文件仅由 `.gitignore` 排除，不在本次重构中删除。
