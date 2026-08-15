# Router V0.2 E2E impact

Router V0.2 在新的冻结 E2E12 上保持12/12路由正确。Academic 6/6全部进入 Academic Retrieval，Search Trigger、Search Success、Extract Success 和 Evidence Sufficiency 均为100%；Missed Academic 0，False Academic 0。Campus 2/2、General 2/2、Hard Negative 2/2亦路由正确。

因此，在本冻结样本上，Router 已不再是主要瓶颈，可以继续保持冻结。此结论不能表述为从66.67%提升到某个 E2E 数字，因为 Development24 与本 E2E12 不是相同样本，也不是相同评价口径。

主失败分布为 Generation 10、Evidence 1；Router/Search/Extract/Infrastructure 均为0。当前最大瓶颈是 Answer Generation：总体 correctness 仅0.833/2（normalized 41.67%），Academic 为1.0/2；Citation Presence 58.33%和 unsupported-claim proxy 37.04%构成次级风险。下一阶段最值得做的是 Generation/Citation 的独立冻结评测与修复，而不是继续优化 Router。
