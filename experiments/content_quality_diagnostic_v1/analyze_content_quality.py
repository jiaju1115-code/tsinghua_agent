from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(r"D:\python_projects\tsinghua_ai")
RUN = ROOT / "data_second" / "public_expansion_v1" / "run_6"
OUT = ROOT / "data_second" / "content_quality_diagnostic_v1"
OUT.mkdir(parents=True, exist_ok=True)

AUDIT = {row["id"]: row for row in json.loads((RUN / "_all.json").read_text(encoding="utf-8"))}

NAV_WORDS = {
    "首页", "借阅", "资源", "空间", "学习支持", "科研支持", "概况", "联系我们", "网站地图",
    "学校概况", "教育教学", "科学研究", "招生就业", "人才招聘", "合作交流", "校园生活",
    "通知公告", "新闻动态", "中心简介", "机构设置", "服务", "更多", "上一页", "下一页",
    "智能问答", "相关链接", "友情链接", "返回顶部", "打印", "关闭", "分享",
}
LIST_TITLE_WORDS = re.compile(
    r"(?:通知公告|新闻动态|动态新闻|招聘信息|政策文件|法律法规|规章制度|常见问题|FAQ|目录|列表|"
    r"热门排序|默认排序|服务通知|失物招领|推荐活动|讲座|数据库导航|馆藏资源|成果|视频素材)$",
    re.I,
)
DETAIL_URL = re.compile(r"/(?:info|article|news|content|detail)/[^?#]*\d+[^/?#]*\.(?:htm|html)$", re.I)
DATE_LINE = re.compile(r"^(?:20\d{2}[-/.年])?\d{1,2}[-/.月]\d{1,2}日?$|^20\d{2}[-/.年]\d{1,2}(?:[-/.月]\d{1,2}日?)?$")
PUNCT = re.compile(r"[。！？；：.!?;]")


def split_doc(text: str) -> tuple[dict[str, str], str]:
    parts = text.split("---", 2)
    front: dict[str, str] = {}
    if len(parts) == 3:
        for line in parts[1].splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            front[key.strip()] = value.strip().strip("'\"")
        body = parts[2]
    else:
        body = text
    body = re.split(r"\n---\s*\n\s*## 来源信息", body, maxsplit=1)[0]
    return front, body.strip()


def visible(line: str) -> str:
    line = re.sub(r"!\[[^]]*]\([^)]*\)", "", line)
    line = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", line)
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"^[\s#>*:+\-|\d.()（）]+", "", line)
    return re.sub(r"\s+", " ", line).strip()


def looks_nav(raw: str, vis: str) -> bool:
    if not vis:
        return False
    if vis in NAV_WORDS:
        return True
    if len(vis) <= 12 and (raw.lstrip().startswith(("- [", ":   [", "[")) or "](" in raw):
        return True
    if len(vis) <= 8 and not PUNCT.search(vis) and not re.search(r"\d{4}|电话|邮箱|时间|地点", vis):
        return True
    if re.search(r"首页.*(?:上页|下页|尾页)|第\s*/?\s*\d+\s*页|跳转", vis):
        return True
    return False


def page_metrics(body: str) -> dict:
    raw_lines = [x.strip() for x in body.splitlines() if x.strip()]
    vis_lines = [visible(x) for x in raw_lines]
    pairs = [(r, v) for r, v in zip(raw_lines, vis_lines) if v]
    lines = [v for _, v in pairs]
    text = "\n".join(lines)
    total = sum(len(x) for x in lines)
    short = sum(len(x) <= 12 for x in lines)
    nav = sum(looks_nav(r, v) for r, v in pairs)
    main = sum(len(v) >= 40 and (PUNCT.search(v) or len(v) >= 70) and not looks_nav(r, v) for r, v in pairs)
    longp = sum(len(v) >= 100 and not looks_nav(r, v) for r, v in pairs)
    list_items = sum(r.lstrip().startswith(("- ", "* ", "+ ", ":   ")) for r, _ in pairs)
    link_chars = sum(len(m.group(1)) for m in re.finditer(r"\[([^]]+)]\([^)]*\)", body))
    date_lines = sum(bool(DATE_LINE.fullmatch(v)) for v in lines)
    loading = bool(re.search(r"读取内容中|请等待|加载中|浏览器.*过低", text))
    template_hits = sum(
        bool(re.search(pat, text, re.I))
        for pat in (
            r"智能问答", r"咨询电话", r"服务时间", r"ref-desk@", r"清华图书馆$",
            r"Copyright|版权所有", r"友情链接", r"网站地图", r"返回顶部",
        )
    )
    return {
        "total_text_length": total,
        "line_count": len(lines),
        "short_line_ratio": round(short / len(lines), 4) if lines else 0,
        "navigation_like_line_count": nav,
        "navigation_like_ratio": round(nav / len(lines), 4) if lines else 0,
        "main_paragraph_count": main,
        "long_paragraph_count": longp,
        "list_item_count": list_items,
        "link_text_ratio": round(link_chars / total, 4) if total else 0,
        "date_line_count": date_lines,
        "loading_marker": loading,
        "template_marker_count": template_hits,
        "visible_text": text,
        "lines": lines,
    }


def list_kind(title: str, text: str) -> str:
    sample = title + " " + text[:2500]
    for kind, pat in (
        ("政策", r"政策|文件目录"), ("招聘", r"招聘|岗位|应聘"), ("办事", r"办事|服务事项|办理"),
        ("FAQ", r"FAQ|常见问题|问答"), ("法规", r"法律|法规"), ("新闻", r"新闻|动态|通知公告|讲座|活动"),
    ):
        if re.search(pat, sample, re.I):
            return kind
    return "其他"


def provisional(row: dict, m: dict) -> tuple[str, str, str, str]:
    title, url, text = row["title"], row["url"], m["visible_text"]
    title_core = re.sub(r"[-—|_].*$", "", title).strip()
    title_specific = len(title_core) >= 12 and not LIST_TITLE_WORDS.search(title_core)
    detail_url = bool(DETAIL_URL.search(url))
    pagination = bool(re.search(r"首页.*(?:上页|下页|尾页)|第\s*/?\s*\d+\s*页|\[下页]", text))
    link_dense = m["list_item_count"] >= 8 and m["link_text_ratio"] >= 0.18
    likely_list = bool(LIST_TITLE_WORDS.search(title_core)) or pagination or (link_dense and m["main_paragraph_count"] <= 2)
    near_no_body = m["main_paragraph_count"] == 0 and (
        m["navigation_like_ratio"] >= 0.35 or m["loading_marker"] or m["link_text_ratio"] >= 0.35
    )
    template_heavy = m["template_marker_count"] >= 2 and (
        m["navigation_like_ratio"] >= 0.18 or m["link_text_ratio"] >= 0.22
    )

    if likely_list and not (detail_url and title_specific and m["loading_marker"]):
        kind = list_kind(title, text)
        follow = "yes" if kind in {"政策", "招聘", "办事", "FAQ", "法规"} else "no"
        reason = f"页面呈现多条{kind}索引/分页或链接集合，未下钻为单一详情正文。"
        follow_reason = (
            f"{kind}条目的核心知识通常位于详情页，建议后续下钻。"
            if follow == "yes" else f"该{kind}聚合页以发现/时效信息为主，默认不批量下钻。"
        )
        return "list_page", reason, follow, follow_reason
    if near_no_body:
        if detail_url or title_specific:
            return "content_missing", "标题/URL指向具体详情，但保存内容以导航、链接或加载占位为主，未见对应连续正文。", "no", "不是列表页；应在修复提取器后重抓当前详情页。"
        return "navigation_only", "保存内容几乎全部为站点导航、栏目菜单、面包屑或页尾，未识别到主体。", "no", "不是可下钻列表，应修复正文容器识别。"
    if template_heavy and m["main_paragraph_count"] >= 1:
        return "template_polluted", "可识别主体正文，但同时保留大量全站导航、咨询区或页尾模板，模板占比偏高。", "no", "当前为详情/说明页，不属于列表下钻任务。"
    if m["total_text_length"] < 260 and m["main_paragraph_count"] <= 2:
        return "thin_content", "正文较短但包含与标题相符的实质说明/联系方式，暂未发现明确缺失证据。", "no", "页面本身为短说明，不需下钻。"
    if m["main_paragraph_count"] >= 2 or m["long_paragraph_count"] >= 1 or m["total_text_length"] >= 550:
        return "detail_content", "存在与标题相符的连续说明、规则、步骤或完整段落，主体可直接识别。", "no", "已获得主体内容。"
    return "mixed_or_uncertain", "现有文本兼有短说明与索引/模板特征，仅凭本地 Markdown 无法可靠确认完整性。", "no", "需人工复核，不自动下钻。"


records = []
for path in sorted((RUN / "cleaned").glob("*.md")):
    text = path.read_text(encoding="utf-8", errors="replace")
    front, body = split_doc(text)
    doc_id = front.get("id") or path.name.split("_", 1)[0]
    existing = AUDIT[doc_id]
    row = {
        "id": doc_id,
        "title": front.get("title") or existing.get("title", ""),
        "url": front.get("source_url") or existing.get("url", ""),
        "source_domain": front.get("domain") or existing.get("source_domain", "") or (urlsplit(existing.get("url", "")).hostname or ""),
        "existing_action": existing.get("action", ""),
        "existing_category": existing.get("category", ""),
        "existing_content_type": existing.get("content_type", ""),
        "source_file": str(path),
    }
    m = page_metrics(body)
    cls, reason, follow, follow_reason = provisional(row, m)
    row.update({k: v for k, v in m.items() if k not in {"visible_text", "lines"}})
    row.update({
        "content_quality_class": cls,
        "should_follow_links": follow,
        "follow_link_reason": follow_reason,
        "diagnostic_reason": reason,
        "list_page_type": list_kind(row["title"], m["visible_text"]) if cls == "list_page" else "",
        "preview": " | ".join(m["lines"][:14])[:1200],
        "tail_preview": " | ".join(m["lines"][-8:])[:800],
    })
    records.append(row)

(OUT / "diagnostic_draft.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

summary = {
    "count": len(records),
    "classes": Counter(r["content_quality_class"] for r in records),
    "actions": Counter(r["existing_action"] for r in records),
    "cross": {a: Counter(r["content_quality_class"] for r in records if r["existing_action"] == a) for a in ("approve", "review", "reject")},
    "domains": {},
}
for domain in sorted({r["source_domain"] for r in records}):
    rows = [r for r in records if r["source_domain"] == domain]
    summary["domains"][domain] = {"total": len(rows), **Counter(r["content_quality_class"] for r in rows)}
(OUT / "draft_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

review_groups = defaultdict(list)
for r in records:
    review_groups[r["content_quality_class"]].append(r)
with (OUT / "review_packets.txt").open("w", encoding="utf-8") as f:
    for cls in ("content_missing", "navigation_only", "template_polluted", "mixed_or_uncertain", "list_page", "thin_content", "detail_content"):
        f.write(f"\n\n######## {cls} ({len(review_groups[cls])}) ########\n")
        for r in review_groups[cls]:
            f.write(
                f"\n[{r['id']}] {r['existing_action']} | {r['source_domain']} | {r['title']}\n"
                f"URL: {r['url']}\n"
                f"METRICS: len={r['total_text_length']} lines={r['line_count']} short={r['short_line_ratio']} "
                f"nav={r['navigation_like_ratio']} main={r['main_paragraph_count']} long={r['long_paragraph_count']} "
                f"list={r['list_item_count']} link={r['link_text_ratio']} loading={r['loading_marker']}\n"
                f"PREVIEW: {r['preview']}\nTAIL: {r['tail_preview']}\n"
            )

print(json.dumps(summary, ensure_ascii=False, indent=2))
