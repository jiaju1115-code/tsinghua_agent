# Prompt V3 30条人工样本回归评估

## 1. 范围与执行

本次仅使用第一轮 Public 正式数据中已经人工标注的同一批 30 条固定样本，复用现有受控模型配置完成 Prompt V3 回归；未抓取新页面、未修改正文提取器、Quality Gate、Restricted/Portal、人工标签或历史结果。模型调用 30/30 成功，失败 0，网络请求 30 次，实际重试 0 次，模型为 `gpt-5.4-mini`，temperature=0.1，并发=3。

## 2. 一致性结果

- V2 vs 人工：24/30 = 80.0%（不一致 6 条）。
- V3 vs 人工：24/30 = 80.0%（不一致 6 条）。
- V3 相比 V2：一致率变化 +0 条；V3 动作为 approve=15、review=2、reject=13。

### V2→V3 动作迁移

| 迁移 | 条数 |
|---|---:|
| approve→approve | 9 |
| approve→reject | 1 |
| reject→approve | 5 |
| reject→reject | 12 |
| reject→review | 2 |
| review→approve | 1 |

### V3 reject_type

| reject_type | 条数 |
|---|---:|
| `expired_event` | 6 |
| `out_of_scope` | 7 |

## 3. 典型变化与剩余差异

V3 正确吸收了人工对 `图书借还`、`信息系统开发` 等长期校园服务页的放宽判断，并把 BIBF 通知、已结束课堂等一次性过期内容纳入 `expired_event` 规则。V3 仍有 6 条与人工不一致，主要是：

- `PUBEXP000076`：V3=approve，人工=review；East View斯大林数字化档案数据库开通试用（2026年7月14日-2026年9月8日）-清华大学图书馆。
- `PUBEXP000233`：V3=approve，人工=reject；2026经济与金融数据课堂第五讲 | 利用排排网私募数据库进行金融研究-清华大学图书馆。
- `PUBFOLLOW000007`：V3=review，人工=reject；新展|从觉醒到黎明：文献里的清华红色记忆（1919-1949）。
- `PUBEXP000119`：V3=approve，人工=reject；期刊编辑进校园IEEE专场活动在图书馆举办-清华大学图书馆。
- `PUBEXP000293`：V3=approve，人工=reject；第51期：前UNESCO教育助理总干事唐虔——我在国际组织的25年-清华大学图书馆。
- `PUBEXP000299`：V3=approve，人工=reject；第32期：金峰——工程的魅力-清华大学图书馆。

其中 East View 数据库试用属于人工 review 而 V3 approve，说明有明确截止日期的当前资源仍需更保守地进入 review；已结束的经济金融数据课堂被 V3 判为 approve，说明“历史但有潜在知识价值”规则对一次性讲座/课堂的边界还不够紧；若干图书馆活动/讲座回顾被 V3 approve 或 review，而人工 reject，说明需进一步区分可复用的稳定知识与纯活动报道。

## 4. 风险与建议

- 样本只有 30 条，且人工标签本身是本轮评估基准，不能外推到全部 217 条审核结果。
- V3 的 approve 数从 10 增至 15，存在把历史活动报道、已结束课堂或活动回顾放宽收录的风险；应在扩大回归前收紧一次性事件的 `historical_but_valuable` 适用条件。
- reject_type 已稳定落在 `out_of_scope` 与 `expired_event` 两类，本轮没有出现 `other`，分类设计可继续保留。

## 5. 结论

**V3_NEEDS_REVISION**。V3 没有达到可直接替换的稳定性要求：与人工一致率未提升（或仍有明显边界误判），建议先针对“已结束课堂/讲座/活动报道”和“有截止日期的当前资源”补充规则，再进行下一轮固定样本回归。本任务到此停止，不进行生产批量重审。
