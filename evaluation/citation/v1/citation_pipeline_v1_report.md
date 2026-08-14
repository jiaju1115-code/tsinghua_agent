# Citation Pipeline V1 Report

## 1. Motivation

在不改写冻结 A baseline 的前提下，将答案生成与证据引用解耦，并用保守规则阻止“看起来有引用但事实不受支持”的引用。

## 2. Frozen Inputs

- 38/38 A answers 与 Answer Eval V0 逐字一致。
- 每题仅使用冻结 Dense Top-5，不扩大检索。
- BGE：`BAAI/bge-small-zh-v1.5` revision `7999e1d3359715c523056ef9478215996d62a620`。
- 输入冻结检查：PASS；详细 hash 见 `audit/input_freeze.json`。

## 3. Pipeline Architecture

Frozen A answer → deterministic claim segmentation → BGE claim embedding → frozen Top-5 matching → deterministic rules → citation assignment → marker-only rendering → evaluation。

## 4. Claim Segmentation

共 120 个 claim，其中 factual claim 104 个。方法为 `DETERMINISTIC_RULE_V1`，未调用 generation model。

## 5. Evidence Matching

Claim embeddings 为 120×512，文件 SHA-256 `2ab812a2571d95744b05c68d384443af8d07331950d53ea3e66d0edd8958558e`。候选严格限制在每题原 Dense Top-5。

## 6. Deterministic Support Rules

数字、时间、实体、流程、顺序分别执行直接匹配规则；拒答不强制事实 citation；冲突采用保守规则。高语义但硬规则失败共 2 个典型案例。

## 7. Citation Assignment

主阈值预先固定为 SUPPORTED≥0.75、PARTIALLY_SUPPORTED≥0.68。仅 SUPPORTED/PARTIALLY_SUPPORTED 分配引用，共 12 条；UNSUPPORTED 与冲突不分配。

## 8. Citation Rendering

仅插入 `[n]` marker 和参考资料列表，不改写正文。Answer Preservation Rate=100.00%。

## 9. Metrics

- SUPPORTED=5，PARTIALLY_SUPPORTED=7，UNSUPPORTED=92，CONFLICTING_EVIDENCE=0。
- Claim-level Citation Coverage=11.54%。
- Citation Precision Proxy=100.00%；这是确定性规则通过率，不是人工准确率。
- Unsupported Claim Rate=88.46%；Partial Support Rate=6.73%；Conflict Rate=0.00%。

## 10. Comparison with A Baseline

Answer-level citation compliance 从 5.26%（2/38）提升至 21.05%（8/38），增加 15.79 个百分点；绝对水平仍低。正文保持率 100%。

## 11. Unsupported Claims

92 个事实 claim 未获支持。自动归因：AMBIGUOUS=85, GENERATION_HALLUCINATION=5, RETRIEVAL_LIMITATION=1, SOURCE_QUALITY_FAILURE=1。大量 claim 低于保守阈值；该结果不能直接等同于事实错误。详见 `analysis/unsupported_claims.md`。

## 12. Traffic Source Quality Failure

RET-09 是证据不足型拒答，未强制 citation；PROV-009 生成了“公众号或小程序”等冻结证据外事实，实体/流程规则拦截并拒绝分配 citation。两题继续标记 SOURCE_QUALITY_FAILURE，没有把语义近似候选包装成支持证据。

## 13. Failure Cases

实际案例与“未检测到”的类别均保留在 `analysis/failure_cases.md`。自动错误 citation proxy=0；真实错误 citation 数量在人工审核前为 N/A。

## 14. Threshold Analysis

敏感性分析固定比较 0.60/0.65/0.70/0.75/0.80，且只统计 factual claims。阈值降低会提高自动覆盖 proxy，但 deterministic-rule proxy 不能估计人工 precision，因此不据 38 题反向选择最“好看”的阈值。主方案保持预声明的保守阈值。

## 15. Limitations

短 claim 对长 chunk 的 embedding 分数存在尺度问题；实体规则依赖表面形式；没有 pretrained NLI/verifier；只查看 Top-5；没有人工 citation 标签。高 precision proxy 与低 coverage 同时存在，表明 embedding+rules 可作安全基线，但不足以完成高覆盖 citation mapping。

## 16. Human Validation Status

Human Audit 尚未完成。Human-validated citation correctness=N/A；工作簿中的三个人工字段全部为空。本报告属于 `PROVISIONAL_AUTO_EVAL`。

## 17. Recommendation for V2

有必要开展 Citation Pipeline V2，但本阶段不执行。优先候选是冻结 Top-5 上的 pretrained cross-encoder/NLI verifier、claim-aware evidence spans 和更稳健的实体别名表；仍应先做人审抽样，校准 precision/coverage，再决定是否引入额外组件。无需 SFT 或训练 citation 模型作为第一步。
