# Parallel Phase V1 Report

日期：2026-08-13  
项目根目录：`D:\python_projects\tsinghua_ai\data_second`

## 总结

三条工作流均独立推进到本阶段可交付边界：Track A 完成 54 条人工抽检工作簿；Track B 将 238 条 approve 全部构建为可重建的 PROVISIONAL_KB_V0；Track C 完成硬件审计、官方 Base Model longlist、统一 scorecard 与可行范围内的实测，并给出条件性模型推荐。没有启动 Restricted Expansion V2，没有修改 Prompt V3.2、旧数据或 production，没有调用第三方大模型 API。

Track C 的完整权重 benchmark 没有伪造完成：Qwen3.5-2B 权重下载在两种官方通道均停滞，Gemma 因 gated/未认证得到 401。失败被写入 benchmark JSONL，不影响 A/B 完成。

## Track A — Human Audit Preparation

状态：**完成**。

- Public population：234；抽取 50。
- Restricted population：4；4 条全部纳入。
- 总抽检：54；54 个唯一 sample_id。
- 固定随机种子：`20260813`。
- 用户指定稀缺类别中，Public 输入实际存在的 6 类（学生事务、餐饮、交通、体育、奖助、就业）共 23 条全部纳入。
- “校园访问”在两个输入中均无记录；“校园综合服务”在 Public 为 0、Restricted 为 1，该 Restricted 条目已纳入。
- 剩余 27 条按非优先类别总体占比用最大余数法分配，类别内固定种子随机抽样；最终 54 条确定性打乱。
- 人工字段 `human_valid/category_correct/content_complete/useful_for_qa/human_note` 在导出后复读仍全部为空。

Public 抽样类别分布：

| 类别 | 数量 |
|---|---:|
| 教务与学籍 | 8 |
| 图书馆服务 | 6 |
| 就业与职业发展 | 6 |
| 学生事务 | 4 |
| 体育与场馆 | 4 |
| 奖助与资助 | 4 |
| 交通服务 | 3 |
| 科研参与与资源导航 | 3 |
| 国际事务与签证 | 2 |
| 网络与信息化 | 2 |
| 医疗健康 | 2 |
| 餐饮服务 | 2 |
| 教学与培养 | 1 |
| 校园机构与部门 | 1 |
| 校园文化与历史 | 1 |
| 住宿服务 | 1 |

Restricted 抽样类别分布：奖助与资助 1、教务与学籍 1、校园综合服务 1、医疗健康 1。

产物：`human_audit/human_audit_sample.xlsx`、`human_audit/human_audit_sampling_report.md`。

## Track B — PROVISIONAL_KB_V0

状态：**完成，可用于临时 retrieval evaluation；不是 production。**

- 实际进入 KB：238/238（Public 234、Restricted 4）。
- 入库前文件存在、UTF-8、正文非空、既有 canonical hash 全部通过。
- Chunk：717（Public 670、Restricted 47）。
- 717/717 chunks 均保存 `chunk_id/source_id/title/url/category/source_type/original_file/text/chunk_index`，URL 与原文件追溯完整。
- 规范化正文按 source_id 单独保存；post-build validation：`PASS`。
- 索引：中文字符 2–4 gram TF-IDF + SciPy CSR exact cosine；shape `717 × 60000`。
- embedding/index NPZ SHA-256：`be34ad63d1a14c42468565ded910beef56524cb3932635b75ab314836c5f708b`。
- 官方 `BAAI/bge-small-zh-v1.5` 固定 commit 元数据可访问，但约 96MB 权重下载两次停滞。管线如实降级为稀疏检索，没有伪造 dense embedding。

10 类 Top-5 retrieval smoke：

- keyword-hit：10/10。
- category-hit：9/10。
- 内容复核：7 pass、2 partial、1 fail。
- 教务/图书馆复合意图为 partial；交通为 fail。失败揭示现有“交通服务”标签下正文与查询需求不匹配，是数据质量问题，不应由生成模型掩盖。

产物完整位于 `rag_v0/`，包括 scripts、config、knowledge_base_manifest、normalized_documents、chunks、vector_index、retrieval_test_cases、retrieval_results、evidence、README 与报告。重建入口见 `rag_v0/README.md`。

## Track C — Base Model Selection + Training Pipeline

状态：**研究/scorecard 完成；权重级 benchmark 部分受网络与门控阻塞；未启动正式训练。**

### 硬件

- Windows 11，Intel i7-1360P，12 physical / 16 logical cores。
- RAM 31.72 GiB；D: 检测时可用约 347.27 GiB。
- 无 NVIDIA GPU；PyTorch `2.13.0+cpu`，CUDA 不可用。
- Transformers 5.13.0；为 smoke 安装 PEFT 0.20.0、Accelerate 1.14.0。
- TRL、bitsandbytes、flash-attn 未安装；SDPA API 存在但仅 CPU backend。
- 当前机器不能现实执行 1B–9B 正式训练。

### 候选与实测

| 候选 | 官方 Base | 许可 / 门控 | 权重 | 本轮实测 |
|---|---|---|---:|---|
| Qwen/Qwen3.5-2B-Base | 是 | Apache-2.0 / open | 约 4.55GB | Tokenizer PASS；完整权重下载停滞 |
| Qwen/Qwen3.5-4B-Base | 是 | Apache-2.0 / open | 约 9.32GB | Tokenizer PASS；硬件不现实，未下载权重 |
| Qwen/Qwen3.5-9B-Base | 是 | Apache-2.0 / open | 约 19.31GB | Tokenizer PASS；硬件不现实，未下载权重 |
| google/gemma-3-1b-pt | 是 | Gemma / manual gated | 约 2.00GB | 401 gated，未实测 tokenizer/权重 |
| google/gemma-3-270m | 是 | Gemma / manual gated | 约 0.54GB | 401 gated，未实测 tokenizer/权重 |

Qwen 三个规模使用同一 tokenizer；固定校园 held-out 子集为 6,135 tokens / 5,522 中文字符，约 1.111 tokens/中文字符。10 个 held-out source_id 已记录到 `model_selection/heldout/heldout_index.json`，后续严禁进入训练。

### 模型决策

- **条件性推荐：`Qwen/Qwen3.5-2B-Base`**，固定 revision `b1485b2fa6dfa1287294f269f5fb618e03d52d7c`。
- **第二候选：`Qwen/Qwen3.5-4B-Base`**，在 24–32 GiB NVIDIA VRAM 目标机上完成同口径 A/B 后再考虑升级。
- 推荐训练方法：BF16 LoRA；2B 建议最低 16 GiB、24 GiB 更稳健。
- QLoRA 只作为显存紧张时的待验证方案；Full Fine-tuning 不推荐，预计需要 48 GiB 以上并做显存剖析。
- 当前机器**不能真正训练**。正式 fine-tuning 前必须在目标 CUDA 环境完成 load、loss、tokens/s、显存、LoRA forward/backward/save/reload。

选择 2B 的原因是中文/多语言和长上下文适配、官方 Base 身份、Apache-2.0、开放下载和相对最低的现实部署成本；不是因为它“更小所以默认更好”。4B/9B 因当前硬件无法验证而不能优先，Gemma 对照受 gated/许可认证阻塞且中文项目适配证据较弱。

`training_v0/` 已建立为空骨架，只包含数据隔离说明与实验配置模板；没有训练数据、adapter、checkpoint，也未执行长时间训练。

## 四类数据隔离检查

| 数据角色 | 本阶段用途 | 状态 |
|---|---|---|
| Corpus / Training Data | 尚未构建 | 未把 KB 或 Gold 自动转为训练数据 |
| Knowledge Base | PROVISIONAL_KB_V0 retrieval | 与 generator/训练解耦 |
| Evaluation / Gold Set | 只供未来评估 | 未读取、未用于训练 |
| Human Audit Sample | 人工质量审核 | 54 条，人工字段为空 |

RAG 中出现某条知识不产生训练授权；Human Audit 未完成不阻塞临时 KB，但正式 KB V1 必须按人工结果清理。

## 下一阶段门槛

1. **Human Audit execution：可以。** 工作簿已生成并验证，可立即交给人工填写。
2. **RAG V1 evaluation：有条件可以。** 可以立即扩展 retrieval 标注与对照评估；正式 KB V1 发布/清洗需等待 Human Audit 结果，并应优先修复交通类与两个 partial 查询。
3. **SFT dataset construction：有条件可以。** 可以开始定义 schema、许可审查、去重和构造流程；不得直接把 238 条 KB 或未审 Human Audit 样本当训练集，Gold 与 10 条 model benchmark held-out 永久禁入。
4. **Base Model fine-tuning：当前机器不可以。** 迁移到至少 16 GiB、建议 24 GiB NVIDIA CUDA 机器，完成 Qwen3.5-2B 固定 revision 的权重级 benchmark 与 LoRA smoke 后才可开始短 SFT pilot。

## 主要产物

- `human_audit/human_audit_sample.xlsx`
- `human_audit/human_audit_sampling_report.md`
- `rag_v0/README.md`
- `rag_v0/rag_v0_report.md`
- `rag_v0/knowledge_base_manifest/post_build_validation.json`
- `model_selection/hardware_report.md`
- `model_selection/base_model_scorecard.xlsx`
- `model_selection/base_model_benchmark.jsonl`
- `model_selection/base_model_selection_report.md`
- `training_v0/README.md`

