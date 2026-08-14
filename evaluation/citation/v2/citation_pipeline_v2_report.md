# Citation Pipeline V2 Report

## 1. Scope and Frozen Inputs

V2 保持38题、120 claims、104 factual claims、A baseline answer、V1 claim IDs 与每题原 Dense Top-5 完全冻结。输入不变性审计 PASS。未生成答案、未重切 claim、未训练模型、未使用 Web Search 或外部 API。

## 2. Architecture

Frozen claim → Top-5 evidence span extraction → BGE span ranking → normalization → pretrained cross-encoder relevance gate → deterministic safety veto → citation assignment/rendering。

## 3. Evidence Spans

从冻结 Top-5 提取 6405 个去重1–3句 spans（30–350字符）。V2-A coverage=49.04%，相对 V1 11.54% 显著上升，说明 whole-chunk mapping 过粗是 V1 低 coverage 的主要因素之一。

## 4. Normalization Contribution

V2-B coverage=52.88%，比 V2-A 增加 3.85 个百分点。实体 alias 只来自同一来源明确等价表达；没有逐题 alias。

## 5. Pretrained Verifier

使用已有 `BAAI/bge-reranker-base` revision `2cfc18c9415c912f9d8155881c133215df768a70`，CPU 推理。它是 cross-encoder relevance 模型，不是 NLI。Sanity 状态：`VERIFIER_NOT_RELIABLE_AS_ENTAILMENT`；正/负 median separation=0.000121，20/20 hard negatives 在0.95阈值上仍为高分。因此不能把它当 entailment verifier，只作为保守 relevance gate。

V2-C coverage=51.92%，较 V2-B 变化 -0.96 个百分点。Verifier 没有带来正向 coverage 增益，且显示明显 false-positive 风险。

## 6. Safety Guards

硬规则拦截 69 个“embedding/verifier高分但数字、时间、实体或流程不匹配”的候选。自动规则下错误 citation=0；Citation Precision Proxy=100.00%，但人工验证 precision=N/A。

## 7. Ablation

- V1: 11.54%
- V2-A spans+embedding+V1 rules: 49.04%
- V2-B + normalization: 52.88%
- V2-C + pretrained verifier+safety: 51.92%

提升主要来自 span-level mapping；normalization 有小幅增益；当前 cross-encoder verifier 没有提供可靠 entailment 增益。

## 8. Citation Metrics and Rendering

V2 分配 55 条 span citation（V1=12）。Answer-level compliance：A=5.26% → V1=21.05% → V2=21.05%。Claim coverage 提升没有转化为 answer-level 全覆盖，因为多-claim回答仍残留 unsupported claim。Answer Preservation=100.00%。

## 9. V1 Unsupported Reclassification

92条分布：V1_MAPPING_FAILURE=32, TOP5_EVIDENCE_PARTIAL=14, RETRIEVAL_FAILURE=0, SOURCE_QUALITY_FAILURE=1, GENERATION_HALLUCINATION=2, AMBIGUOUS=43。

## 10. Full-corpus Diagnostic

只作诊断，不污染正式指标。FOUND_OUTSIDE_TOP5=0，NOT_FOUND_IN_CORPUS=72，AMBIGUOUS=20。

## 11. Traffic Safety Stress Test

RET-09继续保持证据不足拒答且无错误 citation；PROV-009 被 source-gap override 保持 UNSUPPORTED。Cross-encoder 对错误交通候选也可能给高分，但实体/流程规则与已知 source-quality guard 拦截，未产生交通 citation。全库诊断结果记录于机器可读文件，未用于官方 coverage。

## 12. Performance

Span extraction=0.177s，span embedding=108.510s，ranking=0.417s，verifier claim pairs=34.773s，assignment=0.008s，总计=150.420s，平均每题=3.958s。V1 total latency 未被完整记录，因此比较值为 N/A。

## 13. Human Calibration

生成36行分层抽样（32条真实 claim + 4条 sanity hard negatives）。全部人工字段为空。Human-validated precision 仍为 N/A。

## 14. Core Research Answers

1. V1 低 coverage 的主要原因之一是 whole-chunk mapping 太粗；span-level带来37.50个百分点增益。
2. Span-level显著提升 coverage。
3. Normalization额外贡献3.85个百分点。
4. 当前 pretrained reranker没有正向增益，反而因0.95 gate降低0.96个百分点。
5. Verifier存在明确 false positive：20/20 synthetic hard negatives超过阈值。
6. Safety rules成功拦截69个风险候选。
7. 92条重归因见上节与逐条文件。
8. V2不宜直接进入最终系统；需先完成人工 citation calibration。
9. 推荐 V3，但本阶段不执行。
10. V3核心原因是 verifier 不足、entity/procedure resolution 仍脆弱，以及部分 retrieval/source/generation问题；不是单纯降低阈值。

## 15. Limitations and V3 Recommendation

Coverage proxy 与 precision proxy 均为自动规则结果；cross-encoder relevance ≠ entailment；full-corpus diagnostic 使用冻结 whole-chunk embedding 与规则，不能证明 corpus 绝对不存在事实。建议 V3 先引入真正的中文/多语 NLI或更可靠的预训练 verifier，并以本次人工 calibration 样本校准，不训练新模型、不修改生成答案作为第一步。
