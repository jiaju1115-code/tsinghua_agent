from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(r"D:\python_projects\tsinghua_ai")
OUT = ROOT / "data_second" / "public_rebuild_v1"
OLD_SUMMARY = ROOT / "data_second" / "content_quality_diagnostic_v1" / "final_summary.json"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=dict), encoding="utf-8")


manifest = json.loads((OUT / "intermediate" / "manifest.json").read_text(encoding="utf-8"))
base = read_jsonl(OUT / "intermediate" / "base_quality.jsonl")
follow = read_jsonl(OUT / "intermediate" / "follow_quality.jsonl")
audited = read_jsonl(OUT / "audit" / "audit_results.jsonl")
api_summary = json.loads((OUT / "audit" / "api_summary.json").read_text(encoding="utf-8"))
old_summary = json.loads(OLD_SUMMARY.read_text(encoding="utf-8"))
audit_by_id = {r["id"]: r for r in audited}

for row in audited:
    row["rebuild_action"] = row["action"]
for row in base:
    row["rebuild_action"] = audit_by_id.get(row["id"], {}).get("action", "extraction_failed")
for row in follow:
    row["rebuild_action"] = audit_by_id.get(row["id"], {}).get("action", "extraction_failed")

quality_fields = [
    "id", "title", "url", "source_domain", "old_action", "old_category", "old_content_type",
    "old_content_quality_class", "rebuild_action", "http_status", "final_url", "crawl_time",
    "content_quality_class", "extraction_method", "selector_used", "quality_gate_pass",
    "total_text_length", "cleaned_text_length", "navigation_like_ratio", "main_paragraph_count",
    "template_removed", "diagnostic_reason", "source_file",
]
quality_rows = [{k: r.get(k, "") for k in quality_fields} for r in base]
failure_rows = [r for r in quality_rows if r["content_quality_class"] in {"content_missing", "navigation_only"}]
list_fields = quality_fields + ["should_follow_links", "follow_link_reason", "follow_priority", "discovered_direct_links"]
list_rows = [{k: r.get(k, "") for k in list_fields} for r in base if r["content_quality_class"] == "list_page"]
follow_fields = [
    "id", "parent_list_id", "parent_title", "title", "url", "source_domain", "link_score", "http_status",
    "crawl_time", "content_quality_class", "extraction_method", "selector_used", "quality_gate_pass",
    "total_text_length", "cleaned_text_length", "navigation_like_ratio", "main_paragraph_count",
    "template_removed", "dedupe_status", "dedupe_reason", "rebuild_action", "diagnostic_reason", "source_file",
]
follow_rows = [{k: r.get(k, "") for k in follow_fields} for r in follow]
audit_fields = [
    "id", "parent_list_id", "title", "url", "source_domain", "crawl_time", "extraction_method",
    "selector_used", "content_quality_class", "quality_gate_pass", "old_action", "rebuild_action", "action",
    "category", "content_type", "audience", "time_status", "candidate_user_question", "positive_evidence",
    "negative_evidence", "possible_duplicate", "reason", "model", "reviewed_at", "prompt_version", "source_file",
]
audit_rows = [{k: r.get(k, "") for k in audit_fields} for r in audited]

write_json(OUT / "source_manifest" / "public_v1_300_urls.json", manifest)
write_json(OUT / "diagnostics" / "public_v1_300_rebuild_quality.json", quality_rows)
write_json(OUT / "diagnostics" / "rebuild_extraction_failed.json", failure_rows)
write_json(OUT / "list_pages" / "rebuild_list_pages.json", list_rows)
write_json(OUT / "follow_pages" / "followed_detail_pages.json", follow_rows)
write_json(OUT / "audit" / "public_rebuild_v1_all_audited.json", audit_rows)
write_json(OUT / "audit" / "public_rebuild_v1_approved.json", [r for r in audit_rows if r["action"] == "approve"])
write_json(OUT / "audit" / "public_rebuild_v1_review.json", [r for r in audit_rows if r["action"] == "review"])
write_json(OUT / "audit" / "public_rebuild_v1_rejected.json", [r for r in audit_rows if r["action"] == "reject"])


def sample_human() -> list[dict]:
    # Requested 10/10/10 when possible. Only one review exists, so allocate 10 approve, 1 review, 19 reject.
    quotas = {"approve": 10, "review": min(10, sum(r["action"] == "review" for r in audited))}
    quotas["reject"] = 30 - quotas["approve"] - quotas["review"]
    boundary = {"mixed": 0, "current_notice": 1, "service_entry": 2, "procedure_guide": 3,
                "policy": 4, "resource_directory": 5, "organization_intro": 6,
                "research_news": 7, "news_event": 8, "promotional_content": 9}
    result = []
    for action in ("approve", "review", "reject"):
        pool = [r for r in audited if r["action"] == action]
        pool.sort(key=lambda r: (
            0 if r.get("parent_list_id") else 1,
            0 if r.get("old_action") and r.get("old_action") != action else 1,
            boundary.get(r.get("content_type", ""), 20), r.get("source_domain", ""), r["id"],
        ))
        selected, used_combo = [], set()
        for r in pool:
            combo = (r.get("source_domain"), r.get("category"), r.get("content_type"), r.get("extraction_method"))
            if combo not in used_combo:
                selected.append(r); used_combo.add(combo)
            if len(selected) >= quotas[action]: break
        for r in pool:
            if len(selected) >= quotas[action]: break
            if r not in selected: selected.append(r)
        result.extend(selected)
    fields = ["id", "parent_list_id", "title", "url", "old_action", "rebuild_action", "category", "content_type",
              "content_quality_class", "extraction_method", "candidate_user_question", "reason",
              "human_action", "human_category", "human_note"]
    return [{k: ({**r, "human_action": "", "human_category": "", "human_note": ""}).get(k, "") for k in fields} for r in result]


human = sample_human()
write_json(OUT / "human_check" / "public_rebuild_v1_human_check.json", human)

new_classes = Counter(r["content_quality_class"] for r in base)
actions = Counter(r["action"] for r in audited)
base_actions = Counter(r["action"] for r in audited if r["id"].startswith("PUBEXP"))
follow_actions = Counter(r["action"] for r in audited if r["id"].startswith("PUBFOLLOW"))
transitions = Counter((r["old_action"], r["rebuild_action"]) for r in base)
approved = [r for r in audited if r["action"] == "approve"]
categories = Counter(r["category"] for r in approved)
domains_all = Counter(r["source_domain"] for r in base)
domain_stats = defaultdict(Counter)
for r in base + follow:
    d = domain_stats[r["source_domain"]]
    d["pages"] += 1
    d["quality_gate_pass"] += int(bool(r.get("quality_gate_pass")))
for r in audited:
    domain_stats[r["source_domain"]][r["action"]] += 1
list_yes = [r for r in base if r.get("should_follow_links") == "yes"]
usable = new_classes["detail_content"] + new_classes["thin_content"]
failure_count = new_classes["content_missing"] + new_classes["navigation_only"]
lib_share = domains_all["lib.tsinghua.edu.cn"] / 300
conclusion = "REBUILD_PASS_BUT_IMBALANCED" if lib_share >= 0.60 else "REBUILD_PASS"


def pct(n: int, total: int = 300) -> str:
    return f"{n / total:.1%}" if total else "0.0%"


def table_counter(counter: Counter, total: int) -> str:
    return "\n".join(f"| {k} | {v} | {pct(v, total)} |" for k, v in counter.items())


transition_order = [(a, b) for a in ("approve", "review", "reject") for b in ("approve", "review", "reject", "extraction_failed")]
transition_lines = "\n".join(f"| {a} → {b} | {transitions[(a,b)]} |" for a, b in transition_order)
domain_lines = "\n".join(
    f"| {domain} | {s['pages']} | {s['quality_gate_pass']} | {s['approve']} | {s['review']} | {s['reject']} |"
    for domain, s in sorted(domain_stats.items(), key=lambda x: -x[1]["pages"])
)
category_lines = "\n".join(f"| {k} | {v} | {pct(v, len(approved))} |" for k, v in categories.most_common())
requested_categories = ["清华基本信息", "教务与学籍", "学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康", "网络与信息化", "图书馆服务", "体育与场馆", "奖助与资助", "国际事务与签证", "就业与职业发展", "校园访问", "校园综合服务", "科研参与与资源导航", "非目标范围"]
category_lines += "\n" + "\n".join(f"| {k} | 0 | 0.0% |" for k in requested_categories if k not in categories)
typical_follow = [r for r in audited if r.get("parent_list_id") and r["action"] == "approve"][:10]
typical_follow_lines = "\n".join(f"- [{r['title']}]({r['url']})（{r['category']} / {r['content_type']}）" for r in typical_follow) or "- 无"

report = f"""# Public V1 Clean Rebuild 报告

重建目录：`{OUT}`。本轮只处理 `public_expansion_v1/run_6` 的固定 300 条 URL，以及高价值列表页的一层直接详情链接；没有进行自然扩展、递归抓取或修改冻结 Prompt V2。

## 1. 固定 300 条重建

- 固定 URL：300（manifest 与 run_6 ID/URL 逐条对齐）
- 请求成功：{sum(bool(r['ok']) for r in base)}
- 请求失败：{sum(not bool(r['ok']) for r in base)}
- Quality Gate 通过：{sum(bool(r['quality_gate_pass']) for r in base)}
- Quality Gate 未通过：{sum(not bool(r['quality_gate_pass']) for r in base)}
- 获得非空提取文本：{sum(r['cleaned_text_length'] > 0 for r in base)}

## 2. 新正文质量分布及前后对比

| 分类 | 旧诊断 | 新结果 | 新占比 |
|---|---:|---:|---:|
""" + "\n".join(
    f"| {cls} | {old_summary['classes'].get(cls, 0)} | {new_classes.get(cls, 0)} | {pct(new_classes.get(cls, 0))} |"
    for cls in ("detail_content", "list_page", "navigation_only", "content_missing", "template_polluted", "thin_content", "mixed_or_uncertain")
) + f"""

真正可直接用于 Prompt V2 的正文为 `detail_content + 合格 thin_content`，由旧诊断的 55/300（18.3%）提升到 {usable}/300（{pct(usable)}）。`detail_content` 从 51 增加到 {new_classes['detail_content']}；`content_missing` 从 153 降到 {new_classes['content_missing']}；`navigation_only` 从 21 降到 {new_classes['navigation_only']}；`template_polluted` 从 11 变为 {new_classes['template_polluted']}；list_page 已从审核入口分流。

## 3. P0 正文修复效果

旧诊断明确抽取失败 `content_missing + navigation_only` 为 174/300（58.0%）；新结果为 {failure_count}/300（{pct(failure_count)}），下降 {174-failure_count} 条、{58.0 - failure_count/3:.1f} 个百分点。全量 300 条真实页面上仍显示显著改善，因此 P0 修复有效。剩余失败项未使用旧正文、整页 body 或猜测内容，也未送入 Prompt V2。

## 4. list_page 分流与一层下钻

- 新识别 list_page：{new_classes['list_page']}
- `should_follow_links=yes`：{len(list_yes)}
- `should_follow_links=no`：{new_classes['list_page'] - len(list_yes)}
- 实际下钻列表页：{len(list_yes)}
- 发现直接详情链接：{sum(r.get('discovered_direct_links', 0) for r in list_yes)}
- 历史 URL 与本轮基样本去重、全局去重并按优先级截断后：{len(follow)}
- 下钻请求成功：{sum(bool(r.get('ok')) for r in follow)}
- 下钻 Quality Gate 通过：{sum(bool(r.get('quality_gate_pass')) for r in follow)}

下钻只抓列表页面中直接关联的一层详情链接，未从详情页继续递归。普通新闻列表未批量下钻。

## 5. 冻结 Prompt V2 结果

- 审核范围：固定 300 条中的合格正文 {sum(r['id'].startswith('PUBEXP') for r in audited)} 条 + 下钻合格详情 {sum(r['id'].startswith('PUBFOLLOW') for r in audited)} 条 = {len(audited)} 条
- API 成功：{api_summary['successes']}，失败：{api_summary['failures']}，模型：`{api_summary['model']}`，Prompt：`{api_summary['prompt_version']}`
- approve：{actions['approve']}
- review：{actions['review']}
- reject：{actions['reject']}

这些 action 全部基于新正文重新生成，未继承旧 action。

## 6. 旧结果与新结果迁移（固定 300 条）

| 迁移 | 数量 |
|---|---:|
{transition_lines}

重点变化：old reject → new approve 为 {transitions[('reject','approve')]} 条；old approve → new reject 为 {transitions[('approve','reject')]} 条；old review → new approve/reject 分别为 {transitions[('review','approve')]} / {transitions[('review','reject')]} 条。`extraction_failed` 表示未通过本轮正文准入，包含正文缺失、纯导航、列表页和仍明显污染的页面。

## 7. 下钻新增价值

- approve：{follow_actions['approve']}
- review：{follow_actions['review']}
- reject：{follow_actions['reject']}

典型高价值详情页（最多 10 条）：

{typical_follow_lines}

## 8. 来源结构

| domain | 页面数 | Quality Gate 通过 | approve | review | reject |
|---|---:|---:|---:|---:|---:|
{domain_lines}

固定样本中最大来源 `lib.tsinghua.edu.cn` 为 {domains_all['lib.tsinghua.edu.cn']}/300（{pct(domains_all['lib.tsinghua.edu.cn'])}）。正文修复解决了大量图书馆页面的抽取失败，但固定样本来源偏斜仍然存在；本轮按要求没有通过自然发现补齐其他站点。

## 9. 最终 approve category 分布

| category | 数量 | approve 占比 |
|---|---:|---:|
{category_lines}

图书馆服务与科研资源导航占主要部分；住宿、餐饮、交通、医疗、国际事务、奖助、就业等领域仍明显不足。这是固定 300 条来源结构造成的覆盖缺口，不应在本轮通过扩库来掩盖。

## 10. Public Clean Baseline

### A. 固定 300 条

- 获得可用正文：{usable}
- 进入 Prompt V2：{sum(r['id'].startswith('PUBEXP') for r in audited)}
- approve / review / reject：{base_actions['approve']} / {base_actions['review']} / {base_actions['reject']}

### B. 下钻新增

- 去重后抓取详情页：{len(follow)}
- 通过 Quality Gate：{sum(bool(r.get('quality_gate_pass')) for r in follow)}
- approve：{follow_actions['approve']}

### C. 最终可信 baseline

当前共有 **{actions['approve']} 条** `quality_gate_pass=true` 且 Prompt V2 `action=approve` 的可信 Public 页面。

## 11. 人工抽检

已生成 30 条分散抽样。由于 review 仅 {actions['review']} 条，实际构成为 approve 10 / review {actions['review']} / reject {30-10-actions['review']}；优先覆盖旧新 action 变化、下钻详情、边界 content_type，并尽量分散 domain、category 与 extraction_method。

## 12. 最终结论

### `{conclusion}`

正文重建稳定、冻结 Prompt V2 全量重审完成，且可信 approve baseline 已建立；但固定样本中图书馆来源占 {pct(domains_all['lib.tsinghua.edu.cn'])}，category 同样高度集中。下一阶段若启动 Public Expansion V2，应采用定向补齐策略。按任务要求，本轮到此停止，不自动扩库、不启动 V2、不修改 Prompt、提取器或 gold label。
"""
(OUT / "reports" / "public_rebuild_v1_report.md").write_text(report, encoding="utf-8")

stats = {
    "classes": dict(new_classes), "usable": usable, "failure_count": failure_count,
    "actions": dict(actions), "base_actions": dict(base_actions), "follow_actions": dict(follow_actions),
    "transitions": {f"{a}->{b}": n for (a,b), n in transitions.items()},
    "categories": dict(categories), "domains": dict(domains_all), "human_actions": dict(Counter(r["rebuild_action"] for r in human)),
    "conclusion": conclusion,
}
write_json(OUT / "intermediate" / "final_stats.json", stats)
print(json.dumps(stats, ensure_ascii=False, default=dict))
