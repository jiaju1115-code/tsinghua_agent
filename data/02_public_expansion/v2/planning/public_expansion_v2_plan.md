# Public Expansion V2 执行计划

## 目标

形成约300条通过正文提取与 Quality Gate 的新候选，重点补齐 P0/P1 类别。所有结果仅作为 Candidate Pool，不合并生产库。

## 流程

官方入口发现 → 同域一层定向详情发现 → 历史与内部去重 → 限速抓取 → 修复后正文提取器 → Quality Gate → 冻结 Prompt V3.2 + Codex → Candidate Pool。

## 配额与边界

- P0每类以20–40条有效正文为目标，真实公开资源不足则标记 `PUBLIC_SOURCE_LIMITED`。
- P1每类以10–25条为目标；P2按缺口补充。
- 单一domain原则上不超过25%；核心教务或学生事务官方站点如合理超出必须说明。
- `lib.tsinghua.edu.cn`尽量不超过10%。
- list page只用于发现一层相关详情，不送V3.2，不无限下钻。
- 只允许清华官方域名；不使用百科、转载、聚合或第三方博客。

## 可回滚性

raw HTML、cleaned Markdown、Quality Gate结果、审核JSONL与候选Excel分离保存。后续若人工抽检发现问题，只需用已保存正文重新审核，无需重新抓取。
