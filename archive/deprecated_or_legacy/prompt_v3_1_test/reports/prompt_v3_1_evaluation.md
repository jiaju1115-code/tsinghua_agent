# Prompt V3.1 固定30条回归评估

## A. V3.1 定向修改

V3.1 仅修改三类规则：事件页面先判时效再判知识价值；`historical_but_valuable` 仅允许过去事件形成当前仍存在的实体、制度、服务、平台、资源或设施；所有当前有效且核心价值依赖明确未来截止日期的页面统一 `review + active_time_bound`。主体归属、Quality Gate 边界、category、JSON 结构和长期清华服务/资源的知识价值定义保持不变。

实验使用与 V3 完全相同的 30 条正文和人工标签，固定输入 SHA-256 为 `60C385C5DA026DF0F25B03034D63DA97F62FBDF2FF365A8DD83A27E14990BC1C`。模型为 `gpt-5.4-mini`，temperature=0.1，并发=3，max_completion_tokens=900；30/30 调用成功，失败 0，实际重试 0。

## B. 三代 Prompt 与人工一致率

- V2 vs Human：24/30 = 80.0%。
- V3 vs Human：24/30 = 80.0%。
- V3.1 vs Human：27/30 = 90.0%。
- V3.1 动作：approve=10，review=3，reject=17。

### V3 → V3.1 迁移

| 迁移 | 条数 |
|---|---:|
| approve→approve | 9 |
| approve→review | 2 |
| approve→reject | 4 |
| review→approve | 1 |
| review→review | 1 |
| review→reject | 0 |
| reject→approve | 0 |
| reject→review | 0 |
| reject→reject | 13 |

## C. 6条已知分歧

- `PUBEXP000076`：V3.1=review，Human=review，通过。East View斯大林数字化档案数据库开通试用（2026年7月14日-2026年9月8日）-清华大学图书馆
- `PUBEXP000233`：V3.1=reject + expired_event，Human=reject，通过。2026经济与金融数据课堂第五讲 | 利用排排网私募数据库进行金融研究-清华大学图书馆
- `PUBFOLLOW000007`：V3.1=review，Human=reject，未通过。新展|从觉醒到黎明：文献里的清华红色记忆（1919-1949）
- `PUBEXP000119`：V3.1=reject + expired_event，Human=reject，通过。期刊编辑进校园IEEE专场活动在图书馆举办-清华大学图书馆
- `PUBEXP000293`：V3.1=reject + expired_event，Human=reject，通过。第51期：前UNESCO教育助理总干事唐虔——我在国际组织的25年-清华大学图书馆
- `PUBEXP000299`：V3.1=reject + expired_event，Human=reject，通过。第32期：金峰——工程的魅力-清华大学图书馆

已知问题修正 5/6。`PUBFOLLOW000007` 仍为 review：正文未提供明确展期或截止日，模型按 `unknown` 处理；人工外部判断为过期展览。这说明当正文缺失活动结束证据时，Prompt 单靠正文无法稳定强制 `expired_event`。

## D. 新回归

V3 原本与人工一致、V3.1 变成不一致的页面共 2 条：

- `PUBEXP000170`：V3=approve，V3.1=review，Human=approve。元阅读精品电子书数据库开通试用(2025年11月3日-2026年12月31日)-清华大学图书馆
- `PUBEXP000221`：V3=review，V3.1=approve，Human=review。专题书架：好读书 读好书——纪念钱锺书、杨绛学长暨图书馆“钱杨书屋”启用特别专题书架-清华大学图书馆

`PUBEXP000170` 是规则预期带来的边界冲突：V3.1 按“明确截止日期一律 review”执行，但人工因试用期持续到 2026 年末而标 approve。`PUBEXP000221` 被 V3.1 判为已形成持续书架/阅读空间而 approve，人工认为年度有效信息应 review；这不是一次性事件误杀，但显示持续性证据的判断仍有边界波动。

## E. reject 结构

- `out_of_scope`：7。
- `expired_event`：10。
- `other`：0。

本轮没有 `other`，无需逐条解释。

## F. 一次性事件规则表现

V3.1 将 10 条明确过期事件归为 `reject + expired_event`，覆盖课堂、培训、活动报道、单场讲堂、领奖通知和荐购活动。已知的 5 个结束事件硬检查中 4 个成功，展览样本 `PUBFOLLOW000007` 因正文缺少可核实结束日期仍为 review。因此事件规则明显改善，但没有达到“5 条全部 reject”的通过条件。

## G. active_time_bound 表现

本轮共有 2 条 `active_time_bound`，全部进入 review，规则执行稳定：

- `PUBEXP000076`：V3.1=review；Human=review。East View斯大林数字化档案数据库开通试用（2026年7月14日-2026年9月8日）-清华大学图书馆
- `PUBEXP000170`：V3.1=review；Human=approve。元阅读精品电子书数据库开通试用(2025年11月3日-2026年12月31日)-清华大学图书馆

其中 `PUBEXP000076` 与人工一致；`PUBEXP000170` 与人工不一致，但 V3.1 的动作符合本轮明确制定的“一律 review”规则。

## H. 是否过度收紧

抽查的 8 条长期服务、机构、资源、数据库、系统和科研资源页面均未被 reject，长期页面误杀为 0。图书借还、信息系统开发、教学环境服务、组织机构、长期数据库导航、正式订购资源和 ACM OA 政策均保持 approve。没有发现系统性过度收紧。

## 结论

**V3_1_NEEDS_REVISION**。V3.1 将一致率从 24/30 提升到 27/30，并明显纠正了活动报道和历史讲座的误放行；但未达到原则上的 28/30，且 5 个已结束事件硬检查未全部通过，同时产生 2 条新回归。因此不建议直接进入新样本盲测。建议只再处理两个可泛化边界：正文缺少结束日的单次展览/活动如何保守判定，以及“明确截止日期一律 review”与长期试用资源人工口径的冲突。完成定向复核后再进入盲测。

本任务到此停止：未替换生产 Prompt、未重审 217 条、未启动 Public Expansion V2。
