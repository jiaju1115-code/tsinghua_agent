# Answer Generation Evaluation V0 Report

> **PROVISIONAL Answer Generation Evaluation** — Human Audit 尚未完成；本报告不是最终 benchmark。

## 1. 实验目的

在冻结的 RAG V1 Dense Top-5 之上，测量完整 question → retrieval → context → generation → citation → evaluation 链路，区分检索、源数据与生成错误。

## 2. 数据与版本

- Corpus：238 documents / 717 chunks；输入直接复用并校验 RAG V1 冻结文件。
- Evaluation：38 题（10 CONFIRMED Existing Smoke + 28 PROVISIONAL_EVAL）。
- Retriever：`BAAI/bge-small-zh-v1.5`，Dense Top-K=5；未重训 embedding。
- Generator：`Qwen/Qwen2.5-1.5B-Instruct-GGUF`，revision `91cad51170dc346986eccefdc2dd33a9da36ead9`，Q4_K_M，llama.cpp CPU，temperature=0。
- Evaluator：同一模型的本地证据约束判读 + 确定性 citation/source 规则。其分数不是独立 Gold，必须结合人工字段复核。

## 3. Generation pipeline

38 题全部使用冻结 Dense Top-5；每题保存 chunk/document ID、score、完整 context、prompt、answer、citations、token 与时延。回答提示明确禁止外部知识、要求证据不足时拒答、关键事实逐句引用。未调用任何第三方 LLM/API。

## 4. Evaluation methodology

自动指标使用 0/1/2 rubric（正确性、忠实度、完整性、引用正确性）；Unsupported Claim Rate 为自动判定的不支持 claim / 总事实 claim。已知交通题 `RET-09` 与 `PROV-009` 强制优先归因 Source Quality Failure，不因参数调优改写结论。自动判读与生成使用同一小模型，存在自评偏差，因此所有结果标记 `PROVISIONAL_AUTO_EVAL`。

## 5. 总体结果

- Human-validated Answer Correctness / Faithfulness / Unsupported Claim Rate：**N/A**（人工复核未完成）。下列数值仅为同源本地 evaluator 的 provisional proxy。
- 完成：38/38 generation，38/38 auto evaluation。
- Answer Correctness：均值 1.2368/2（normalized 61.84%）；fully correct 11/38。
- Faithfulness：均值 1.2895/2（normalized 64.47%）。
- Unsupported Claim Rate：1/109 = 0.92%。
- 正确拒答：2。
- 含生成型幻觉/不支持推断/过度自信的回答：1。
- Citation Correctness：均值 0.2895/2；Citation Mismatch 32。
- 平均生成时延：21.37s/query（CPU）。

## 6. V0 smoke 结果

- 原结果：{'partial': 2, 'pass': 7, 'fail': 1}（对应 7 pass / 2 partial / 1 fail）。
- Answer Generation V0：{'partial': 9, 'pass': 1}。
- 变化：{'unchanged': 2, 'degraded': 7, 'improved': 1}。
- Smoke 中“检索正确但生成错误”：9。
- 交通题仍归因：source；检索排序不能创造 corpus 中不存在的答案。

## 7. 幻觉与 Unsupported Claim

类型分布：{'CITATION_MISMATCH': 32, 'SOURCE_QUALITY_FAILURE': 2, 'RETRIEVAL_FAILURE': 3, 'OVERCONFIDENT_ANSWER': 1, 'GENERATION_HALLUCINATION': 1}。小模型最突出的问题之一是未稳定遵守逐句 citation 约束；这类输出即使事实可在 context 中找到，也不能视为引用合格。没有为提高数字重跑或挑选输出。

## 8. Retrieval vs Generation 错误归因

- Retrieval Failure：3。
- Source Quality Failure：2。
- Retrieval 正确但 Answer 错误：32。
- 当前主要风险信号：generation constraints。Dense R@5 不能自动等价为端到端答案正确。

## 9. Source Quality Failure

交通/校车/路线相关题仍缺少充分源资料。生成器必须拒答；任何常识补全都计为过度自信或幻觉。此阶段没有启动新抓取或修改 corpus。

## 10. Failure Cases

逐例见 `analysis/failure_cases.md`，保留 question、evidence、answer 与诊断；缺少的类型明确写“未观察到”，没有凑数。

## 11. 当前局限

1. 28 题为 PROVISIONAL_EVAL；Human Audit 未完成。
2. 自动 evaluator 与 generator 同源且只有 1.5B 参数，可能错判语义支持、完整性与 claim 切分。
3. 只有一套本地生成 baseline；未做模型间比较。
4. 引用格式失败会显著拉低 citation 指标，但不等同于所有事实均错误。

## 12. Human Audit 未完成声明

Human Audit 的五个字段在工作簿中保持空白。本阶段不得作为最终 benchmark，也不得据此修改 production。

## 13. 下一阶段建议（不执行）

优先优化 grounded generation prompt / citation constraint，并在相同 38 题上做一次冻结 A/B；不要先做 SFT。交通类另列 corpus gap，等待 Human Audit 后决定是否补充/清洗。只有在正确 evidence 已到位而生成错误仍稳定复现时，才讨论 SFT 候选实验。
