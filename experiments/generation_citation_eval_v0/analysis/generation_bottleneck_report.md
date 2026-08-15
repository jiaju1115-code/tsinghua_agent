# Generation bottleneck report

Freeze SHA256: `6ae8bb6c41518f75fb2efc3ea5287283be5792fdeaf232095f82ba75587a1710`。全部语义指标均为 Provisional Proxy，不是 Human Validated。

## Evidence-Sufficient Generation-Only Subset

上游正常且 evidence sufficient 的样本共43题：Track A 33题、Track B 10题。

- Correctness：1.186/2（59.30% normalized）
- Faithfulness：1.326/2（66.28% normalized）
- Completeness proxy：37.98%
- Unsupported factual/procedural claim proxy：23.66%
- Claim-level citation coverage：9.16%
- Citation validity（已有 citation）：100%
- Citation support（已有 citation，deterministic proxy）：66.67%

这说明上游成功后仍存在显著 Generation 损失。Completeness 是首要问题：43题中39题带有 INCOMPLETE 标签，27题以其为 primary failure。

## Failure priority

- P0：UNSUPPORTED_ADDITION，12/43（27.91% primary）。可能造成事实误导，优先约束无证据推断。
- P1：INCOMPLETE，27/43（62.79% primary）；其次是 TASK_COMPLETION 和 Citation coverage。
- P2：没有观察到需要单独优先处理的纯格式问题。

Wrong Refusal 在 evidence-sufficient 集合中出现3个标签、1个 primary；Failed Refusal 仅出现在 evidence-insufficient Track A，共3题。两者存在，但不是最大频率问题。

## Citation diagnosis

主要是 Citation Coverage Failure，而不是 Mapping Failure。跨 Track 共134个需要 citation 的 factual/procedural claims，只有12个具有 claim-level citation，coverage 8.96%。已出现 citation 的 ID mapping 为12/12有效；支持性 proxy 为8/12。Source availability 不是主因，因为 clean subset 已限定 evidence sufficient。

## Academic E2E12

Academic 6题全部 evidence sufficient：Correctness 1.0/2，Faithfulness 1.667/2，Completeness proxy 16.67%，Claim-level Citation Coverage 23.53%。Unsupported proxy 88.24%受保守词法支持阈值影响，6题全部进入人工复核队列，不应直接当成人工事实错误率。

## Optimization Priority 1

提高 evidence-sufficient 场景的任务完成度：覆盖 query 所要求的全部定义、条件、步骤或比较点。

## Optimization Priority 2

建立 claim-level citation coverage 约束，要求每个需引用的事实/步骤都映射到证据，而不仅是答案末尾出现一个 citation。

## Optimization Priority 3

抑制 unsupported inference/background-knowledge injection，并校准 sufficient/insufficient 条件下的拒答行为。
