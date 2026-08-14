from __future__ import annotations

import csv, json
from collections import Counter
from pathlib import Path

BASE = Path(r"D:\python_projects\tsinghua_ai\data_second\public_expansion_v1\run_6")
AUDIT = BASE / "audit" / "audit_results.csv"
FIELDS = ["id","title","url","source_domain","crawl_time","action","category","content_type","audience","time_status","candidate_user_question","positive_evidence","negative_evidence","possible_duplicate","reason"]

with AUDIT.open(encoding="utf-8-sig", newline="") as f: rows = list(csv.DictReader(f))
rows.sort(key=lambda x: x["id"])
if len(rows) != 300: raise SystemExit(f"Expected 300 audited rows, got {len(rows)}")

def write_csv(name, data, fields):
    with (BASE / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(data)

write_csv("_all.csv", rows, FIELDS)
write_csv("_approved.csv", [r for r in rows if r["action"] == "approve"], FIELDS)
write_csv("_review.csv", [r for r in rows if r["action"] == "review"], FIELDS)
(BASE / "_all.json").write_text(json.dumps([{k:r.get(k,"") for k in FIELDS} for r in rows], ensure_ascii=False), encoding="utf-8")
(BASE / "_approved.json").write_text(json.dumps([{k:r.get(k,"") for k in FIELDS} for r in rows if r["action"]=="approve"], ensure_ascii=False), encoding="utf-8")
(BASE / "_review.json").write_text(json.dumps([{k:r.get(k,"") for k in FIELDS} for r in rows if r["action"]=="review"], ensure_ascii=False), encoding="utf-8")

# Deterministic action-stratified sample. Within each class prefer varied
# content types/domains and known boundary types before filling in ID order.
boundary = {"mixed": 0, "current_notice": 1, "organization_intro": 2, "resource_directory": 3, "service_entry": 4, "news_event": 5, "promotional_content": 6}
sample = []
for action in ("approve", "review", "reject"):
    pool = [r for r in rows if r["action"] == action]
    pool.sort(key=lambda r: (boundary.get(r["content_type"], 9), r["source_domain"], r["id"]))
    selected, used_types, used_domains = [], set(), set()
    for r in pool:
        if len(selected) >= 10: break
        if r["content_type"] not in used_types or r["source_domain"] not in used_domains:
            selected.append(r); used_types.add(r["content_type"]); used_domains.add(r["source_domain"])
    for r in pool:
        if len(selected) >= 10: break
        if r not in selected: selected.append(r)
    sample.extend(selected)
human_fields = FIELDS + ["human_action", "human_category", "human_note"]
write_csv("_human_check.csv", [{**r, "human_action":"", "human_category":"", "human_note":""} for r in sample], human_fields)
(BASE / "_human_check.json").write_text(json.dumps([{k:{**r,"human_action":"","human_category":"","human_note":""}.get(k,"") for k in human_fields} for r in sample], ensure_ascii=False), encoding="utf-8")

crawl = json.loads((BASE / "reports" / "crawl_stats.json").read_text(encoding="utf-8"))
api = json.loads((BASE / "audit" / "api_summary.json").read_text(encoding="utf-8"))
actions, cats, types, domains, times = (Counter(r[k] for r in rows) for k in ("action","category","content_type","source_domain","time_status"))

def pct(n): return f"{n/len(rows):.1%}"
def dist(counter): return "\n".join(f"- {k}: {v}（{pct(v)}）" for k,v in counter.most_common())
def examples(action, n=10):
    chosen = [r for r in rows if r["action"] == action]
    chosen.sort(key=lambda r: (boundary.get(r["content_type"], 9), r["id"]))
    return "\n".join(f"- **{r['title']}**（{r['id']}，{r['content_type']}）：{r['reason']}" for r in chosen[:n])

approve_news = sum(r["action"] == "approve" and r["content_type"] in {"news_event","research_news","promotional_content","achievement_report"} for r in rows)
approve_aggregates = sum(r["action"] == "approve" and r["content_type"] in {"mixed","organization_intro"} for r in rows)
approve_outdated = sum(r["action"] == "approve" and r["time_status"] == "outdated" for r in rows)
lib_share = domains.get("lib.tsinghua.edu.cn", 0) / len(rows)
conclusion = "PUBLIC_NEEDS_ADJUSTMENT"

report = f"""# Public 数据第一轮规模化扩展报告

正式结果目录：`{BASE}`。本报告仅统计 `run_6`；此前因编码诊断产生的 `run_1`—`run_5` 文件均作为异常证据保留，未纳入候选、审核或统计。

## A. 抓取情况

- 发现 URL：{crawl['discovered_urls']}
- 实际尝试抓取：{crawl['attempted']}
- 抓取失败：{crawl['fetch_failed']}
- 基础质量检查淘汰：{crawl['crawl_invalid']}
- 登录/认证页跳过：{crawl['auth_skipped']}
- 历史重复：{crawl['historical_duplicates']}
- 本轮内部重复：{crawl['internal_duplicates']}
- 去重总量：{crawl['historical_duplicates'] + crawl['internal_duplicates']}
- 最终有效候选：{crawl['valid_candidates']}
- 新域名/未批准域名链接发现次数：{crawl['outside_or_new_domain']}；仅记录候选域名，没有自动加入白名单。

质量复核：300 个 Markdown 与候选索引数量一致；候选 URL 与内容哈希均无批内精确重复；中文编码抽查无乱码；未把登录页送入 Prompt V2。

## B. Prompt V2 审核分布

{dist(actions)}

API 统计：逻辑审核调用 {api['total_calls']}，成功 {api['successes']}，失败 {api['failures']}；网络请求尝试 {api['network_request_attempts']}，实际重试 {api['actual_retries']}；自动追加模型修复轮次 {api['automatic_extra_model_rounds']}。模型、temperature、超时和单调用重试上限沿用项目配置；最大并发 3。

## C. category 分布

{dist(cats)}

## D. content_type 分布

{dist(types)}

## E. 典型 approve

{examples('approve')}

## F. 典型 reject

{examples('reject')}

## G. review 分析

review 共 {actions['review']} 条，主要原因是：标题显示为高价值通知/规则/资源，但抓取正文没有展开核心时间、规则、入口或数据库详情；聚合页同时混合稳定服务和活动/通知；部分时效性信息无法从正文确认仍然有效。它们已进入独立 review 表，并在 30 条人工抽检中按 10 条纳入。

## H. 风险

- 新闻过滤：approve 中 news_event / research_news / promotional_content / achievement_report 共 {approve_news} 条，未发现科研新闻或宣传新闻被直接准入。
- 聚合与机构页：approve 中 mixed/organization_intro 共 {approve_aggregates} 条。其中部分页面确有地点、电话、开放时间或服务范围，但也出现“正文主体缺失、仅凭通用咨询方式 approve”的边界偏宽现象，需人工抽检。
- 科研资源导航：科研参与与资源导航共 {cats.get('科研参与与资源导航',0)} 条，其中 approve {sum(r['action']=='approve' and r['category']=='科研参与与资源导航' for r in rows)} 条。未将 research_news 准入，但对开放获取文章、出版支持页的通用咨询入口可能判断偏宽。
- 过期内容：time_status=outdated 共 {times.get('outdated',0)} 条，approve {approve_outdated} 条；模型总体没有将明确过期页面直接准入。
- 重复：抓取阶段排除 {crawl['historical_duplicates'] + crawl['internal_duplicates']} 条重复，最终 possible_duplicate 标记 {sum(r['possible_duplicate'].lower()=='true' for r in rows)} 条；仍需关注相同图书馆页尾咨询信息对语义判断的干扰。
- 站点偏斜：`lib.tsinghua.edu.cn` 占 {domains.get('lib.tsinghua.edu.cn',0)}/{len(rows)}（{lib_share:.1%}），显著高于其他站点；ITC {domains.get('www.itc.tsinghua.edu.cn',0)} 条，保卫处 {domains.get('peace.tsinghua.edu.cn',0)} 条。该批不能代表教务、医疗、住宿、餐饮、交通、国际事务、就业等 Public 基础覆盖。
- 采集异常：最初站点字符集声明/自动探测导致乱码；乱码批次被隔离保留并完全排除。正式 `run_6` 改为原始字节严格 UTF-8 优先、GB18030 回退后通过复核。

## I. 下一阶段建议

### {conclusion}

Prompt V2 本身已展示实质筛选能力：reject 115 条、review 32 条，且没有新闻/科研新闻/宣传成果类页面被 approve。但本轮来源严重集中于图书馆站点，且少量 approve 依赖页面通用页尾联系方式而非标题所指核心正文，说明 Public 发现策略和正文抽取仍需调整。

建议先做两项小范围调整再继续：

1. 对单站点设置发现/有效候选配额，补齐教务学籍、学生事务、医疗、住宿餐饮、交通、国际事务、就业与校级服务目录；新域名继续只进入候选清单，人工确认后再加入。
2. 优化图书馆详情页正文抽取，移除重复页尾咨询模板；当标题主题正文缺失时，不应仅凭通用电话/邮箱形成 approve，优先 review/reject。

本轮结束后停止，不自动启动第二批 Public、新生专项、办事专项或 Portal 扩展。
"""
(BASE / "public_expansion_v1_report.md").write_text(report, encoding="utf-8")
(BASE / "_output_stats.json").write_text(json.dumps({"actions":actions,"categories":cats,"content_types":types,"domains":domains,"sample_actions":Counter(r['action'] for r in sample),"conclusion":conclusion}, ensure_ascii=False, indent=2, default=dict), encoding="utf-8")
print(json.dumps({"rows":len(rows),"sample":len(sample),"actions":actions,"conclusion":conclusion}, ensure_ascii=False, default=dict))
