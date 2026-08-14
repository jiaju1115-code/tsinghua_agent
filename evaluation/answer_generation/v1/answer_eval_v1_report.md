# Grounded Generation Prompt A/B V1 Report

> **PROVISIONAL_AUTO_EVAL** — Human Audit/人工复核未完成，不是最终 benchmark。

## 1. 实验设计

- 同一冻结 38 题、同一 RAG V1 Dense Top-5、同一 context、同一 `Qwen2.5-1.5B-Instruct-GGUF` revision、同一量化、seed、temperature、token limit 和运行时。
- A：字节级复现 Answer Eval V0 prompt。
- B：只修改 system prompt，强化 evidence-only、逐事实句末 citation、证据不足拒答、禁止证据外渠道/常识。
- A/B 使用完全相同的本地 evaluator 与确定性规则。没有人工字段参与计算。

## 2. 冻结与复现

- A prompt SHA 与 V0 一致：是。
- A 生成答案与 V0 逐字一致：38/38。
- Retrieval、model revision 与解码配置未变。

## 3. 总体指标

| Metric | A baseline | B strict | Δ B−A |
|---|---:|---:|---:|
| Correctness normalized | 98.68% | 96.05% | -2.63% |
| Faithfulness normalized | 98.68% | 100.00% | 1.32% |
| Unsupported Claim Rate | 2.10% | 3.29% | 1.19% |
| Citation compliance | 5.26% | 0.00% | -5.26% |
| Correct refusals | 2 | 0 | -2 |
| Hallucination answers | 3 | 5 | +2 |

Human-validated correctness、faithfulness、unsupported claim rate、citation compliance：**N/A**。

## 4. Citation error taxonomy

A：{'MISSING_CITATION': 34, 'CITATION_FORMAT_ERROR': 2, 'SOURCE_QUALITY_FAILURE': 2, 'RETRIEVAL_FAILURE': 3, 'GENERATION_HALLUCINATION': 3, 'OVERCONFIDENT_ANSWER': 3}  
B：{'MISSING_CITATION': 36, 'SOURCE_QUALITY_FAILURE': 2, 'GENERATION_HALLUCINATION': 5, 'OVERCONFIDENT_ANSWER': 5, 'RETRIEVAL_FAILURE': 3, 'CITATION_FORMAT_ERROR': 1}

`MISSING_CITATION` 表示事实回答完全没有有效引用；`WRONG_CITATION` 表示引用资料不支持对应事实；`INSUFFICIENT_CITATION_COVERAGE` 表示只有部分事实单元有引用；`CITATION_FORMAT_ERROR` 表示引用格式或句末位置不合规。

## 5. Refusal 与安全性

A 正确拒答 2，B 正确拒答 0。已知交通 source gap 继续优先归因 `SOURCE_QUALITY_FAILURE`；B 若避免 V0 的证据外“公众号/小程序”补全，属于 prompt 改善，不代表 corpus gap 已修复。

## 6. 逐题变化

{'uncertain': 28, 'degraded': 4, 'unchanged': 6}。`improved` 只在 correctness/faithfulness/unsupported claims 不劣且 citation compliance 实质提升时成立；安全性下降直接记为 `degraded`；答案改变但缺乏合规引用、无法可靠归因时记为 `uncertain`。完整逐题 A/B、指标 delta、引用错误及诊断见 `results/ab_per_question.jsonl` 与 `analysis/ab_change_analysis.md`。所有 degraded case 均保留。

## 7. 结论与限制

本轮 **不推荐采用 B prompt**。虽然 B 的 provisional faithfulness proxy 增加 1.32 个百分点，但 correctness 降低 2.63 个百分点、Unsupported Claim Rate 增加 1.19 个百分点、citation compliance 从 5.26% 降至 0、正确拒答从 2 降至 0，hallucination answers 从 3 增至 5。更严格的自然语言指令没有改善该 1.5B 模型的 citation instruction-following，且在交通 source gap 等题上出现安全退化。

本实验只回答“更严格 prompt 在同一小模型与同一 evidence 上是否改善 grounded generation”。自动 evaluator 与 generator 同源，语义正确性仍需人工复核；不能把 proxy 当作 Gold。建议保留 A 作为当前 baseline，下一步先研究结构化/受约束解码或答案后置 citation validator，而不是继续堆叠 prompt 文本；不据此启动 SFT。
