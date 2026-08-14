# Prompt V3.2 Blind Test V1 抽样报告

## A. 候选池

- Public Clean Baseline 合格正文：217 条。
- 历史调参排除：30 条。
- 排除后候选池：187 条。
- 排除按 ID、原始 URL、normalized URL 三重匹配，并合并人工标注、V3、V3.1、V3.2 的历史来源。历史文件理论上是同一批固定 30 条，复核后确实归并为 30 个唯一页面。

## B. 最终样本

- 总数：50。
- random：25。
- targeted：25。
- random_seed：`20260813`。
- 随机组没有读取标题、V2 action 或任何 V3.x 结果；先按候选池结构设置 domain 配额，再只用 category/content_type 做分散选择。

## C. domain 分布

| domain | 数量 | 占比 |
|---|---:|---:|
| lib.tsinghua.edu.cn | 41 | 82.0% |
| www.itc.tsinghua.edu.cn | 7 | 14.0% |
| peace.tsinghua.edu.cn | 2 | 4.0% |

最大 domain 为 `lib.tsinghua.edu.cn`，占 82.0%。候选池本身有 170/187 来自图书馆站点，最终 82% 的图书馆占比是基线结构限制；未为强行平衡而加入范围外数据。

## D. category_hint 分布（内部 manifest 的旧 V2 元数据，仅供抽样审计）

| category_hint | 数量 |
|---|---:|
| 非目标范围 | 15 |
| 图书馆服务 | 12 |
| 科研参与与资源导航 | 10 |
| 校园生活 | 7 |
| 网络与信息化 | 3 |
| 校园基本信息 | 2 |
| 学生事务 | 1 |

## E. content_type 分布（内部 manifest 的旧 V2 元数据）

| content_type | 数量 |
|---|---:|
| news_event | 9 |
| organization_intro | 9 |
| resource_directory | 5 |
| current_notice | 5 |
| service_entry | 5 |
| research_news | 5 |
| procedure_guide | 3 |
| promotional_content | 2 |
| policy | 2 |
| mixed | 2 |
| achievement_report | 2 |
| faq | 1 |

## F. 定向覆盖

| 类型 | 覆盖数量 | 状态 |
|---|---:|---|
| 科研成果/行业科研新闻 | 3 | COVERED |
| 教师获奖 | 0 | NOT_AVAILABLE_IN_CURRENT_POOL |
| 人物/荣誉 | 4 | COVERED |
| 校领导活动 | 2 | COVERED |
| 合作签约 | 2 | COVERED |
| 长期校园服务 | 5 | COVERED |
| 科研资源 | 5 | COVERED |
| 校园核心事务 | 5 | COVERED |
| 活动/新闻边界 | 5 | COVERED |
| medium候选 | 5 | COVERED |

说明：候选池包含科研/行业成果新闻、人物或机构荣誉、校领导活动和合作签约；没有标题与正文明确属于“教师个人获奖”的合格页面，因此该细项标记为 `NOT_AVAILABLE_IN_CURRENT_POOL`，未用其他人物稿伪装。人物/荣誉大类仍覆盖 4 条。medium 候选共 5 条，依据标题和正文人工筛选为历史、概况、机构职能或专题资源边界，未调用 V3.2 预判。

## G. 样本泄漏与去重检查

- 最终 50 条中来自原 30 条调参集：0。
- normalized URL 唯一数：50/50。
- 正文 SHA-256 唯一数：50/50。
- 高相似标题对：0。
- 同一系列未集中选入超过 2 条；人物/活动覆盖来自不同标题与事件。
- 人工标注表不含 V2/V3/V3.1/V3.2 action、AI reason、AI category 或 AI topic_relevance。`category_hint` 仅表示来源站点，`content_type_hint` 仅由标题关键词机械生成。
- 7 个 human 字段全部留空；正文以完整 cleaned_content 写入，同时保留独立 Markdown 文件。

## H. 阶段边界

本阶段未调用 Prompt V2、Prompt V3.2 或任何 AI 审核 API，未自动生成 human 标签。样本与空白表已经冻结；下一步必须等待人工完成标注，才能运行真正的 blind test。
