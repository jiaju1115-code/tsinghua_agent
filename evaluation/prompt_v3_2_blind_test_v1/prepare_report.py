from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BASE = Path(r"D:\python_projects\tsinghua_ai\data_second\prompt_v3_2_blind_test_v1")
pool = json.loads((BASE / "manifest" / "blind_candidate_pool.json").read_text(encoding="utf-8"))
exclusion = json.loads((BASE / "manifest" / "blind_test_exclusion_list.json").read_text(encoding="utf-8"))
manifest = json.loads((BASE / "samples" / "blind_test_v1_sample_manifest.json").read_text(encoding="utf-8"))
summary = json.loads((BASE / "audit" / "final_sample_summary.json").read_text(encoding="utf-8"))
random_summary = json.loads((BASE / "audit" / "pool_random_summary.json").read_text(encoding="utf-8"))

domains = Counter(x["domain"] for x in manifest)
categories = Counter(x["category_hint"] for x in manifest)
content_types = Counter(x["content_type_hint"] for x in manifest)
max_domain, max_count = domains.most_common(1)[0]

coverage_order = ["科研成果/行业科研新闻", "教师获奖", "人物/荣誉", "校领导活动", "合作签约", "长期校园服务", "科研资源", "校园核心事务", "活动/新闻边界", "medium候选"]
coverage = dict(summary["coverage"])
coverage["教师获奖"] = 0

lines = [
    "# Prompt V3.2 Blind Test V1 抽样报告",
    "",
    "## A. 候选池",
    "",
    "- Public Clean Baseline 合格正文：217 条。",
    f"- 历史调参排除：{len(exclusion)} 条。",
    f"- 排除后候选池：{len(pool)} 条。",
    "- 排除按 ID、原始 URL、normalized URL 三重匹配，并合并人工标注、V3、V3.1、V3.2 的历史来源。历史文件理论上是同一批固定 30 条，复核后确实归并为 30 个唯一页面。",
    "",
    "## B. 最终样本",
    "",
    f"- 总数：{len(manifest)}。",
    f"- random：{sum(x['source_group']=='random' for x in manifest)}。",
    f"- targeted：{sum(x['source_group']=='targeted' for x in manifest)}。",
    f"- random_seed：`{random_summary['random_seed']}`。",
    "- 随机组没有读取标题、V2 action 或任何 V3.x 结果；先按候选池结构设置 domain 配额，再只用 category/content_type 做分散选择。",
    "",
    "## C. domain 分布",
    "",
    "| domain | 数量 | 占比 |",
    "|---|---:|---:|",
]
for k, v in domains.most_common(): lines.append(f"| {k} | {v} | {v/len(manifest):.1%} |")
lines += [
    "",
    f"最大 domain 为 `{max_domain}`，占 {max_count/len(manifest):.1%}。候选池本身有 170/187 来自图书馆站点，最终 82% 的图书馆占比是基线结构限制；未为强行平衡而加入范围外数据。",
    "",
    "## D. category_hint 分布（内部 manifest 的旧 V2 元数据，仅供抽样审计）",
    "",
    "| category_hint | 数量 |",
    "|---|---:|",
]
for k, v in categories.most_common(): lines.append(f"| {k} | {v} |")
lines += ["", "## E. content_type 分布（内部 manifest 的旧 V2 元数据）", "", "| content_type | 数量 |", "|---|---:|"]
for k, v in content_types.most_common(): lines.append(f"| {k} | {v} |")
lines += ["", "## F. 定向覆盖", "", "| 类型 | 覆盖数量 | 状态 |", "|---|---:|---|"]
for tag in coverage_order:
    count = coverage.get(tag, 0)
    status = "COVERED" if count else "NOT_AVAILABLE_IN_CURRENT_POOL"
    lines.append(f"| {tag} | {count} | {status} |")
lines += [
    "",
    "说明：候选池包含科研/行业成果新闻、人物或机构荣誉、校领导活动和合作签约；没有标题与正文明确属于“教师个人获奖”的合格页面，因此该细项标记为 `NOT_AVAILABLE_IN_CURRENT_POOL`，未用其他人物稿伪装。人物/荣誉大类仍覆盖 4 条。medium 候选共 5 条，依据标题和正文人工筛选为历史、概况、机构职能或专题资源边界，未调用 V3.2 预判。",
    "",
    "## G. 样本泄漏与去重检查",
    "",
    "- 最终 50 条中来自原 30 条调参集：0。",
    f"- normalized URL 唯一数：{summary['normalized_url_unique']}/50。",
    f"- 正文 SHA-256 唯一数：{summary['content_hash_unique']}/50。",
    f"- 高相似标题对：{len(summary['similar_title_pairs'])}。",
    "- 同一系列未集中选入超过 2 条；人物/活动覆盖来自不同标题与事件。",
    "- 人工标注表不含 V2/V3/V3.1/V3.2 action、AI reason、AI category 或 AI topic_relevance。`category_hint` 仅表示来源站点，`content_type_hint` 仅由标题关键词机械生成。",
    "- 7 个 human 字段全部留空；正文以完整 cleaned_content 写入，同时保留独立 Markdown 文件。",
    "",
    "## H. 阶段边界",
    "",
    "本阶段未调用 Prompt V2、Prompt V3.2 或任何 AI 审核 API，未自动生成 human 标签。样本与空白表已经冻结；下一步必须等待人工完成标注，才能运行真正的 blind test。",
]
(BASE / "reports" / "blind_test_v1_sampling_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"domains": dict(domains), "categories": dict(categories), "content_types": dict(content_types), "coverage": coverage}, ensure_ascii=False, indent=2))
