from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


OUT = Path(r"D:\python_projects\tsinghua_ai\data_second\content_quality_diagnostic_v1")
rows = json.loads((OUT / "diagnostic_draft.json").read_text(encoding="utf-8"))

LOADING_EXCEPTIONS = {"PUBEXP000010", "PUBEXP000027"}
FORCE_MISSING = {
    "PUBEXP000036", "PUBEXP000038",  # ITC detail URLs containing only navigation
    "PUBEXP000059", "PUBEXP000061", "PUBEXP000062", "PUBEXP000081", "PUBEXP000087",
    "PUBEXP000232", "PUBEXP000233", "PUBEXP000234", "PUBEXP000235", "PUBEXP000236",
    "PUBEXP000237", "PUBEXP000238", "PUBEXP000239",
}
FORCE_DETAIL = {
    "PUBEXP000011", "PUBEXP000021", "PUBEXP000031", "PUBEXP000042", "PUBEXP000048",
    "PUBEXP000063", "PUBEXP000067", "PUBEXP000130", "PUBEXP000141", "PUBEXP000142",
    "PUBEXP000143", "PUBEXP000144", "PUBEXP000147", "PUBEXP000152", "PUBEXP000155",
    "PUBEXP000156", "PUBEXP000158", "PUBEXP000214", "PUBEXP000215", "PUBEXP000216",
    "PUBEXP000217", "PUBEXP000218", "PUBEXP000247",
}
FORCE_THIN = {"PUBEXP000132", "PUBEXP000135", "PUBEXP000136", "PUBEXP000154"}
FORCE_POLLUTED = {
    "PUBEXP000010", "PUBEXP000017", "PUBEXP000019", "PUBEXP000029", "PUBEXP000057",
    "PUBEXP000134", "PUBEXP000139", "PUBEXP000145", "PUBEXP000153", "PUBEXP000243",
    "PUBEXP000245",
}
FORCE_NAV = {
    "PUBEXP000020", "PUBEXP000032", "PUBEXP000033", "PUBEXP000086", "PUBEXP000092",
    "PUBEXP000093", "PUBEXP000094", "PUBEXP000133", "PUBEXP000146", "PUBEXP000149",
    "PUBEXP000150", "PUBEXP000151", "PUBEXP000157", "PUBEXP000160", "PUBEXP000161",
    "PUBEXP000162", "PUBEXP000241", "PUBEXP000242", "PUBEXP000252", "PUBEXP000253",
    "PUBEXP000254",
}
FORCE_LIST = {
    "PUBEXP000008", "PUBEXP000012", "PUBEXP000016", "PUBEXP000028", "PUBEXP000035",
    "PUBEXP000037", "PUBEXP000039", "PUBEXP000044", "PUBEXP000045", "PUBEXP000046",
    "PUBEXP000047", "PUBEXP000054", "PUBEXP000058", "PUBEXP000060", "PUBEXP000064",
    "PUBEXP000065", "PUBEXP000066", "PUBEXP000069", "PUBEXP000071", "PUBEXP000075",
    "PUBEXP000080", "PUBEXP000082", "PUBEXP000083", "PUBEXP000084", "PUBEXP000085",
    "PUBEXP000090", "PUBEXP000091", "PUBEXP000095", "PUBEXP000096", "PUBEXP000097",
    "PUBEXP000098", "PUBEXP000104", "PUBEXP000112", "PUBEXP000115", "PUBEXP000122",
    "PUBEXP000123", "PUBEXP000124", "PUBEXP000125", "PUBEXP000126", "PUBEXP000137",
    "PUBEXP000138", "PUBEXP000140", "PUBEXP000148", "PUBEXP000163", "PUBEXP000175",
    "PUBEXP000181", "PUBEXP000185", "PUBEXP000191", "PUBEXP000197", "PUBEXP000202",
    "PUBEXP000203", "PUBEXP000206", "PUBEXP000207", "PUBEXP000208", "PUBEXP000211",
    "PUBEXP000212", "PUBEXP000213", "PUBEXP000219", "PUBEXP000244", "PUBEXP000246",
}


def detail_url(url: str) -> bool:
    return bool(re.search(r"/(?:info|article|news|content|detail)/[^?#]*\d+[^/?#]*\.(?:htm|html)$", url, re.I))


def classify(r: dict) -> str:
    i = r["id"]
    if r["loading_marker"] and i not in LOADING_EXCEPTIONS:
        return "content_missing"
    if i in FORCE_MISSING:
        return "content_missing"
    if i in FORCE_DETAIL:
        return "detail_content"
    if i in FORCE_THIN:
        return "thin_content"
    if i in FORCE_POLLUTED:
        return "template_polluted"
    if i in FORCE_NAV:
        return "navigation_only"
    if i in FORCE_LIST:
        return "list_page"
    # Remaining records are generally clean ITC/library service details.
    if detail_url(r["url"]) and r["main_paragraph_count"] == 0 and r["navigation_like_ratio"] >= 0.68:
        return "content_missing"
    if r["main_paragraph_count"] >= 2 or r["long_paragraph_count"] >= 1 or r["total_text_length"] >= 500:
        return "detail_content"
    if r["total_text_length"] < 260 and r["main_paragraph_count"] >= 1:
        return "thin_content"
    return "mixed_or_uncertain"


def list_type(title: str) -> str:
    if re.search(r"招聘|勤工助学|岗位", title): return "招聘"
    if re.search(r"政策", title): return "政策"
    if re.search(r"法律|法规|规章制度|知识产权声明", title): return "法规"
    if re.search(r"FAQ|常见问题", title, re.I): return "FAQ"
    if re.search(r"默认排序|服务$|借阅&服务|站点地图|按类型查", title): return "办事"
    if re.search(r"通知|新闻|动态|快讯|活动|讲座|日历|真人图书馆|作者面对面|从游悦读|闻道", title): return "新闻"
    return "其他"


def follow_decision(kind: str, title: str) -> tuple[str, str]:
    if kind in {"政策", "招聘", "办事", "FAQ", "法规"}:
        return "yes", f"{kind}列表的核心规则、条件或办理信息通常在详情页，建议后续下钻。"
    if kind == "其他" and re.search(r"资源|数据库|馆藏|期刊|出版支持|入馆须知", title):
        return "yes", "该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。"
    return "no", "该页以新闻、活动或时效性发现为主，默认不批量下钻；仅按高价值服务通知定向处理。"


reasons = {
    "detail_content": "正文与标题匹配，包含可连续阅读的说明、规则、步骤或结构化主体，可直接用于后续知识审核。",
    "list_page": "页面主体是栏目/目录/聚合列表，当前内容可用于发现，但不等同于条目详情正文。",
    "navigation_only": "保存文本以栏目词、菜单、站点框架或短标签为主，未发现可确认的连续主体内容。",
    "content_missing": "标题或详情 URL 表明应有正文，但本地 Markdown 仅有导航、栏目名、模板或加载占位，主体缺失。",
    "template_polluted": "主体内容存在且可识别，但页头、栏目导航、页尾咨询/馆链等模板占比过高。",
    "thin_content": "页面仅提供简短但与标题匹配的实质说明，未发现应有长正文却缺失的证据。",
    "mixed_or_uncertain": "文本兼有说明与模板/索引特征，本地数据不足以稳定确认完整性。",
}

for r in rows:
    cls = classify(r)
    r["content_quality_class"] = cls
    r["diagnostic_reason"] = reasons[cls]
    if cls == "content_missing" and r["loading_marker"]:
        r["diagnostic_reason"] += " 页面还明确保留“读取内容中/请等待”等动态加载占位。"
    if cls == "list_page":
        kind = list_type(r["title"])
        follow, why = follow_decision(kind, r["title"])
        r["list_page_type"] = kind
        r["should_follow_links"] = follow
        r["follow_link_reason"] = why
    else:
        r["list_page_type"] = ""
        r["should_follow_links"] = "no"
        if cls == "content_missing":
            r["follow_link_reason"] = "不是列表页；应修复正文提取后重抓当前 URL。"
        else:
            r["follow_link_reason"] = "不属于待下钻列表。"

(OUT / "final_records.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

classes = ["detail_content", "list_page", "navigation_only", "content_missing", "template_polluted", "thin_content", "mixed_or_uncertain"]
actions = ["approve", "review", "reject"]
class_counts = Counter(r["content_quality_class"] for r in rows)
cross = {a: Counter(r["content_quality_class"] for r in rows if r["existing_action"] == a) for a in actions}
extraction_failure = {a: cross[a]["content_missing"] + cross[a]["navigation_only"] for a in actions}
quality_affected = {a: sum(cross[a][x] for x in ("content_missing", "navigation_only", "template_polluted", "list_page")) for a in actions}
usable = class_counts["detail_content"] + class_counts["thin_content"]
list_rows = [r for r in rows if r["content_quality_class"] == "list_page"]
list_type_counts = defaultdict(Counter)
for r in list_rows:
    list_type_counts[r["list_page_type"]][r["should_follow_links"]] += 1

domain_rows = []
for domain in sorted({r["source_domain"] for r in rows}):
    rr = [r for r in rows if r["source_domain"] == domain]
    cc = Counter(r["content_quality_class"] for r in rr)
    domain_rows.append({
        "domain": domain, "total": len(rr),
        "detail_content": cc["detail_content"], "list_page": cc["list_page"],
        "content_missing": cc["content_missing"], "navigation_only": cc["navigation_only"],
        "template_polluted": cc["template_polluted"],
        "failure_count": cc["content_missing"] + cc["navigation_only"],
    })
domain_rows.sort(key=lambda x: (-x["failure_count"], -x["total"], x["domain"]))

def top_rows(cls: str, n: int, key=None):
    rr = [r for r in rows if r["content_quality_class"] == cls]
    if key: rr.sort(key=key)
    return rr[:n]

severe = top_rows("content_missing", 10, key=lambda r: (0 if detail_url(r["url"]) else 1, 0 if r["loading_marker"] else 1, r["id"]))
lists = sorted(list_rows, key=lambda r: (0 if r["should_follow_links"] == "yes" else 1, r["list_page_type"], r["id"]))[:10]
polluted = top_rows("template_polluted", 10, key=lambda r: (-r["navigation_like_ratio"], r["id"]))
normal = top_rows("detail_content", 10, key=lambda r: (-r["main_paragraph_count"], -r["total_text_length"], r["id"]))

summary = {
    "total": len(rows), "classes": {c: class_counts[c] for c in classes}, "usable": usable,
    "usable_ratio": usable / len(rows), "cross": {a: dict(cross[a]) for a in actions},
    "extraction_failure": extraction_failure, "quality_affected": quality_affected,
    "approve_abnormal": quality_affected["approve"],
    "approve_low_value_list": sum(1 for r in list_rows if r["existing_action"] == "approve" and r["should_follow_links"] == "no"),
    "reject_missing": extraction_failure["reject"],
    "list_total": len(list_rows),
    "list_follow_yes": sum(r["should_follow_links"] == "yes" for r in list_rows),
    "list_follow_no": sum(r["should_follow_links"] == "no" for r in list_rows),
    "list_types": {k: dict(v) for k, v in sorted(list_type_counts.items())},
    "domains": domain_rows,
    "sample_ids": {
        "severe": [r["id"] for r in severe], "list": [r["id"] for r in lists],
        "polluted": [r["id"] for r in polluted], "normal": [r["id"] for r in normal],
    },
}
(OUT / "final_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def pct(n: int, d: int = 300) -> str:
    return f"{n/d:.1%}"


def sample_table(items: list[dict], mode: str) -> str:
    out = ["| ID | 标题 | action | 说明 |", "|---|---|---|---|"]
    for r in items:
        if mode == "severe":
            note = "详情页正文缺失；" + ("含动态加载占位" if r["loading_marker"] else "仅保留导航/栏目框架")
        elif mode == "list":
            note = f"{r['list_page_type']}列表；下钻={r['should_follow_links']}：{r['follow_link_reason']}"
        elif mode == "polluted":
            note = f"导航样式行占比 {r['navigation_like_ratio']:.1%}；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。"
        else:
            note = f"正文段落 {r['main_paragraph_count']}，文本 {r['total_text_length']} 字；标题与主体匹配。"
        out.append(f"| {r['id']} | {r['title'].replace('|','/')} | {r['existing_action']} | {note.replace('|','/')} |")
    return "\n".join(out)


report = f"""# Public V1 正文抽取质量诊断报告

诊断对象：`public_expansion_v1/run_6` 的 300 条 cleaned Markdown。诊断仅使用本地现有 Markdown、审核结果与代码；未请求网页、未重抓、未调用审核 API、未修改原始数据。

## 结论摘要

最终结论：`CONTENT_EXTRACTION_CRITICAL`

- 可直接用于知识库审核的主体内容：{usable}/300（{pct(usable)}）。口径为 `detail_content + thin_content`，不把 `list_page` 视为完整正文。
- 明确抽取失败（`content_missing + navigation_only`）：{class_counts['content_missing'] + class_counts['navigation_only']}/300（{pct(class_counts['content_missing'] + class_counts['navigation_only'])}）。
- Prompt V2 的 approve 中，{quality_affected['approve']}/153（{pct(quality_affected['approve'],153)}）落入缺失、纯导航、模板污染或列表页；现有 approve 不能直接沿用。
- reject 中 {extraction_failure['reject']}/115（{pct(extraction_failure['reject'],115)}）属于正文缺失或纯导航，存在因输入残缺被误 reject 的风险。
- 应暂停 Public Expansion V2，先修正文提取，再对受影响数据重抓并重新 Prompt V2 审核。

## A. 七类分布

| 分类 | 数量 | 比例 |
|---|---:|---:|
""" + "\n".join(f"| `{c}` | {class_counts[c]} | {pct(class_counts[c])} |" for c in classes) + f"""

## B. 真正可用正文比例

`detail_content` {class_counts['detail_content']} 条加 `thin_content` {class_counts['thin_content']} 条，共 {usable} 条（{pct(usable)}）。`template_polluted` 虽能辨认正文，但不计入“可直接使用”，应先清理模板；`list_page` 只具索引价值。

## C. 与 Prompt V2 交叉分析

| action | 总数 | detail | list | navigation | missing | polluted | thin | uncertain | 明确抽取失败 | 广义质量受影响 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
""" + "\n".join(
    f"| {a} | {sum(cross[a].values())} | {cross[a]['detail_content']} | {cross[a]['list_page']} | {cross[a]['navigation_only']} | {cross[a]['content_missing']} | {cross[a]['template_polluted']} | {cross[a]['thin_content']} | {cross[a]['mixed_or_uncertain']} | {extraction_failure[a]} | {quality_affected[a]} |"
    for a in actions
) + f"""

- approve 污染：`navigation_only` {cross['approve']['navigation_only']}、`content_missing` {cross['approve']['content_missing']}、`template_polluted` {cross['approve']['template_polluted']}、`list_page` {cross['approve']['list_page']}；其中低价值且不建议下钻的 list approve 为 {summary['approve_low_value_list']} 条。
- review：明确抽取失败 {extraction_failure['review']}/32（{pct(extraction_failure['review'],32)}），review 大量由正文质量问题驱动。
- reject 误伤风险：`content_missing + navigation_only` 共 {extraction_failure['reject']} 条。

## D. list_page 下钻价值

- 总数：{len(list_rows)}；`should_follow_links=yes`：{summary['list_follow_yes']}；`no`：{summary['list_follow_no']}。

| 类型 | 合计 | yes | no |
|---|---:|---:|---:|
""" + "\n".join(f"| {k} | {sum(v.values())} | {v['yes']} | {v['no']} |" for k,v in sorted(list_type_counts.items())) + f"""

## E. 来源站点

本批数据实际仅包含 3 个 domain，因此不能虚构 Top 10/15；以下列出全部站点，并按明确抽取失败数排序。

| domain | total | detail | list | missing | navigation | polluted | 明确失败 |
|---|---:|---:|---:|---:|---:|---:|---:|
""" + "\n".join(
    f"| {d['domain']} | {d['total']} | {d['detail_content']} | {d['list_page']} | {d['content_missing']} | {d['navigation_only']} | {d['template_polluted']} | {d['failure_count']} |"
    for d in domain_rows
) + f"""

最严重的是 `lib.tsinghua.edu.cn`：样本占比极高，且大量详情页只保存统一导航、咨询页尾与“读取内容中，请等待…”占位。`www.itc.tsinghua.edu.cn` 的已知新闻详情页则只留下学校/中心导航。`peace.tsinghua.edu.cn` 主要问题是栏目页与短标签页被当作候选正文。

## F. 重点人工复核样本

### 10 个最严重正文抽取失败案例

{sample_table(severe, 'severe')}

### 10 个 list_page 案例

{sample_table(lists, 'list')}

### 10 个 template_polluted 案例

{sample_table(polluted, 'polluted')}

### 10 个正常 detail_content 对照

{sample_table(normal, 'normal')}

## G. 技术根因诊断

1. **动态正文未被抓取（主因）**：大量图书馆详情页在服务器返回的本地 Markdown 中只有“读取内容中，请等待…”，说明正文可能由 JavaScript/异步接口加载；当前 `requests` 抓取静态 HTML，未获得真实详情正文。
2. **Trafilatura 回退条件反向放大模板**：`parser.py` 在 Trafilatura 结果低于清理后全文 35% 时回退到整个 cleaned DOM。对导航很长、正文为空或异步加载的页面，这会把全站菜单/页尾当成正文。
3. **DOM 清理选择器覆盖不全**：只删除通用 `nav/header/footer` 类名；图书馆站的菜单、面包屑、咨询模块和馆链使用站点自定义结构，未被剔除。
4. **详情页 selector fallback 太窄且使用时机不足**：`article, main, .content, .article, .detail, .news_content, #content` 只在 Trafilatura 完全失败时尝试；Trafilatura 返回模板片段或加载占位时不会进入站点 selector 分支。
5. **缺少 title-content 一致性与抽取后质量闸门**：当前仅以 `plain >= 220`、字符种类等判断有效。长导航轻易越过阈值，没有检测正文段落、导航占比、加载占位或详情 URL 的正文缺失。
6. **列表页虽被用于链接发现，但候选本身仍入库**：爬虫会 follow 列表链接，却没有在保存候选时将 `list_page` 与详情页分层；因此目录、栏目和站点地图进入 Prompt V2。
7. **站点结构差异**：ITC、图书馆、保卫部 DOM 差异明显，单一通用抽取链难以稳定覆盖；需要 domain/template 级 selector 与去模板规则。

## H. 修复建议

### P0

1. 暂停 Public Expansion V2；在正文质量闸门通过前不继续扩库。
2. 修正文提取器：对加载占位、详情 URL 无正文、超高导航占比直接判失败，不允许回退到整页 body 后作为有效候选。
3. 对 `lib.tsinghua.edu.cn`、`www.itc.tsinghua.edu.cn` 至少建立站点 selector fallback，并在 Trafilatura 返回低质片段时也执行候选容器比选。
4. 对动态正文明确选择可审计方案：读取已有页面内嵌数据/本地可见接口结构，或在后续获准重抓时使用浏览器渲染；本轮不执行重抓。
5. 修复后重抓所有 `content_missing`/`navigation_only`，并对所有受影响的 Prompt V2 记录重新审核；approve 也必须重审。

### P1

1. 自动识别 `list_page`，保留发现价值但不作为完整知识正文送审；依据 `should_follow_links` 下钻政策、法规、招聘、办事、FAQ 和高价值资源目录。
2. 建立抽取评分：正文段落数、短行率、导航样式占比、链接文本占比、加载占位、标题覆盖度、详情 URL 先验；保留失败原因。
3. 将页头/页尾/咨询区/馆链做站点级剥离，避免 `template_polluted` 稀释 Prompt 输入。

### P2

1. 建立每个 domain 的小型回归样本集（正常详情、动态详情、列表、短页各若干），每次修改后自动比较。
2. 记录提取路径（Trafilatura、selector、rendered、fallback）与正文容器选择证据，便于监控站点模板变更。
3. 对 `thin_content` 与 `mixed_or_uncertain` 设置定期人工抽检，不用单一长度阈值裁决。

## 明确回答

1. 是否暂停 Public Expansion V2：**是**。
2. 是否先修正文提取器：**是**。
3. 是否做不同站点 selector fallback：**是，至少优先覆盖图书馆与 ITC**。
4. 是否自动识别 list_page 并下钻：**是，但按 `should_follow_links` 分流，不应无差别抓取新闻列表**。
5. 修复后是否重抓并重审现有 300 条：**应重抓明确失败条目；对缺失、导航、污染和列表所影响的 Prompt V2 结果重新审核。为保证批次一致性，建议最终对 300 条统一重跑质量闸门与 Prompt V2。**

## 最终结论

`CONTENT_EXTRACTION_CRITICAL`

当前大量数据没有获得真实主体正文，Prompt V2 结果的可信度受到明显影响。应暂停扩库，先修复正文提取与质量闸门，再重抓并重新审核受影响数据。
"""
(OUT / "content_quality_report.md").write_text(report, encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
