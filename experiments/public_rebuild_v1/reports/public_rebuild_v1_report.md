# Public V1 Clean Rebuild 报告

重建目录：`D:\python_projects\tsinghua_ai\data_second\public_rebuild_v1`。本轮只处理 `public_expansion_v1/run_6` 的固定 300 条 URL，以及高价值列表页的一层直接详情链接；没有进行自然扩展、递归抓取或修改冻结 Prompt V2。

## 1. 固定 300 条重建

- 固定 URL：300（manifest 与 run_6 ID/URL 逐条对齐）
- 请求成功：300
- 请求失败：0
- Quality Gate 通过：208
- Quality Gate 未通过：92
- 获得非空提取文本：300

## 2. 新正文质量分布及前后对比

| 分类 | 旧诊断 | 新结果 | 新占比 |
|---|---:|---:|---:|
| detail_content | 51 | 178 | 59.3% |
| list_page | 60 | 24 | 8.0% |
| navigation_only | 21 | 7 | 2.3% |
| content_missing | 153 | 51 | 17.0% |
| template_polluted | 11 | 10 | 3.3% |
| thin_content | 4 | 30 | 10.0% |
| mixed_or_uncertain | 0 | 0 | 0.0% |

真正可直接用于 Prompt V2 的正文为 `detail_content + 合格 thin_content`，由旧诊断的 55/300（18.3%）提升到 208/300（69.3%）。`detail_content` 从 51 增加到 178；`content_missing` 从 153 降到 51；`navigation_only` 从 21 降到 7；`template_polluted` 从 11 变为 10；list_page 已从审核入口分流。

## 3. P0 正文修复效果

旧诊断明确抽取失败 `content_missing + navigation_only` 为 174/300（58.0%）；新结果为 58/300（19.3%），下降 116 条、38.7 个百分点。全量 300 条真实页面上仍显示显著改善，因此 P0 修复有效。剩余失败项未使用旧正文、整页 body 或猜测内容，也未送入 Prompt V2。

## 4. list_page 分流与一层下钻

- 新识别 list_page：24
- `should_follow_links=yes`：11
- `should_follow_links=no`：13
- 实际下钻列表页：11
- 发现直接详情链接：274
- 历史 URL 与本轮基样本去重、全局去重并按优先级截断后：17
- 下钻请求成功：17
- 下钻 Quality Gate 通过：9

下钻只抓列表页面中直接关联的一层详情链接，未从详情页继续递归。普通新闻列表未批量下钻。

## 5. 冻结 Prompt V2 结果

- 审核范围：固定 300 条中的合格正文 208 条 + 下钻合格详情 9 条 = 217 条
- API 成功：217，失败：0，模型：`gpt-5.4-mini`，Prompt：`v2_frozen`
- approve：89
- review：1
- reject：127

这些 action 全部基于新正文重新生成，未继承旧 action。

## 6. 旧结果与新结果迁移（固定 300 条）

| 迁移 | 数量 |
|---|---:|
| approve → approve | 58 |
| approve → review | 1 |
| approve → reject | 31 |
| approve → extraction_failed | 63 |
| review → approve | 15 |
| review → review | 0 |
| review → reject | 13 |
| review → extraction_failed | 4 |
| reject → approve | 13 |
| reject → review | 0 |
| reject → reject | 77 |
| reject → extraction_failed | 25 |

重点变化：old reject → new approve 为 13 条；old approve → new reject 为 31 条；old review → new approve/reject 分别为 15 / 13 条。`extraction_failed` 表示未通过本轮正文准入，包含正文缺失、纯导航、列表页和仍明显污染的页面。

## 7. 下钻新增价值

- approve：3
- review：0
- reject：6

典型高价值详情页（最多 10 条）：

- [关于参加2026北京国际图书博览会（BIBF）外文原版图书现场荐购活动的通知](https://lib.tsinghua.edu.cn/info/1073/8100.htm)（图书馆服务 / current_notice）
- [“毕”读报告 | 2026年毕业生个人阅读报告](https://lib.tsinghua.edu.cn/info/1073/8103.htm)（图书馆服务 / current_notice）
- [关于6月25日取消2026年6月毕业生借书权限的通知](https://lib.tsinghua.edu.cn/info/1073/8121.htm)（图书馆服务 / current_notice）

## 8. 来源结构

| domain | 页面数 | Quality Gate 通过 | approve | review | reject |
|---|---:|---:|---:|---:|---:|
| lib.tsinghua.edu.cn | 280 | 198 | 82 | 1 | 115 |
| www.itc.tsinghua.edu.cn | 23 | 17 | 6 | 0 | 11 |
| peace.tsinghua.edu.cn | 14 | 2 | 1 | 0 | 1 |

固定样本中最大来源 `lib.tsinghua.edu.cn` 为 263/300（87.7%）。正文修复解决了大量图书馆页面的抽取失败，但固定样本来源偏斜仍然存在；本轮按要求没有通过自然发现补齐其他站点。

## 9. 最终 approve category 分布

| category | 数量 | approve 占比 |
|---|---:|---:|
| 图书馆服务 | 60 | 67.4% |
| 科研参与与资源导航 | 19 | 21.3% |
| 网络与信息化 | 5 | 5.6% |
| 校园生活 | 4 | 4.5% |
| 学生事务 | 1 | 1.1% |
| 清华基本信息 | 0 | 0.0% |
| 教务与学籍 | 0 | 0.0% |
| 住宿服务 | 0 | 0.0% |
| 餐饮服务 | 0 | 0.0% |
| 交通服务 | 0 | 0.0% |
| 医疗健康 | 0 | 0.0% |
| 体育与场馆 | 0 | 0.0% |
| 奖助与资助 | 0 | 0.0% |
| 国际事务与签证 | 0 | 0.0% |
| 就业与职业发展 | 0 | 0.0% |
| 校园访问 | 0 | 0.0% |
| 校园综合服务 | 0 | 0.0% |
| 非目标范围 | 0 | 0.0% |

图书馆服务与科研资源导航占主要部分；住宿、餐饮、交通、医疗、国际事务、奖助、就业等领域仍明显不足。这是固定 300 条来源结构造成的覆盖缺口，不应在本轮通过扩库来掩盖。

## 10. Public Clean Baseline

### A. 固定 300 条

- 获得可用正文：208
- 进入 Prompt V2：208
- approve / review / reject：86 / 1 / 121

### B. 下钻新增

- 去重后抓取详情页：17
- 通过 Quality Gate：9
- approve：3

### C. 最终可信 baseline

当前共有 **89 条** `quality_gate_pass=true` 且 Prompt V2 `action=approve` 的可信 Public 页面。

## 11. 人工抽检

已生成 30 条分散抽样。由于 review 仅 1 条，实际构成为 approve 10 / review 1 / reject 19；优先覆盖旧新 action 变化、下钻详情、边界 content_type，并尽量分散 domain、category 与 extraction_method。

## 12. 最终结论

### `REBUILD_PASS_BUT_IMBALANCED`

正文重建稳定、冻结 Prompt V2 全量重审完成，且可信 approve baseline 已建立；但固定样本中图书馆来源占 87.7%，category 同样高度集中。下一阶段若启动 Public Expansion V2，应采用定向补齐策略。按任务要求，本轮到此停止，不自动扩库、不启动 V2、不修改 Prompt、提取器或 gold label。
