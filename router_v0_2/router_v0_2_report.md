# Router V0.2 专项修复报告

评测全程离线，无 Tavily Search/Extract 请求。既有24题已标记为 DEVELOPMENT_SET；新增42题（30 Academic、12 hard negatives）已冻结并记录 SHA256。

## 结果

- Development 24：24/24，Accuracy 100%，Academic Recall/Precision 100%。V0.1 的8个路由错误在该集合中全部修复。
- Frozen Full30：30/30，Accuracy 100%，三类各10题均保持100%。
- Blind Shadow 42：42/42，Accuracy 100%；Academic Recall 100%，Precision 100%；Campus 100%；General/Hard Negative 100%；False Academic 0；Missed Academic 0。
- 分学科 Recall：高等数学、线性代数、概率统计、大学物理、经济学/计量、计算机/算法均100%。

## 归因与决策

8个历史错误主要是学科本体覆盖不足与任务结构信号缺失；修复加入了公式/任务/领域组合判定，并保留当前性和校园事实优先级。新增盲集未发现 Ontology overmatch 或 under-match。由于 Blind 通过（Academic Recall≥90%、Overall Accuracy≥90%、hard negatives 全部正确），满足可选条件；本 V0.2 仍不发起联网 E2E，Search/Extract calls 为 N/A（本专项明确要求离线）。

建议：可进入 Integration V0 的 Router 集成门槛；建议 V1 前补充更广泛的歧义意图和多语种术语对照。最小下一修复是继续扩展 ontology/task 配置，而非改变路由架构。

首次 Web Search V0 因 API Key 未配置曾安全阻断；本专项与 Academic Retrieval V0.1 的 Router 评测不依赖该 Key。

详见 `results/router_metrics.json`、`analysis/`、`audit/blind_set_freeze.json`。
