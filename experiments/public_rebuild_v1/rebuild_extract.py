from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, UnicodeDammit


ROOT = Path(r"D:\python_projects\tsinghua_ai")
SECOND = ROOT / "data_second"
RUN6 = SECOND / "public_expansion_v1" / "run_6"
DIAGNOSTIC = SECOND / "content_quality_diagnostic_v1"
OUT = SECOND / "public_rebuild_v1"
sys.path.insert(0, str(ROOT / "data_first"))

from crawler.parser import detect_page, parse_html  # noqa: E402


TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "spm", "from"}
ALLOWED_HOSTS = {"lib.tsinghua.edu.cn", "www.itc.tsinghua.edu.cn", "peace.tsinghua.edu.cn"}
LIST_NAV = re.compile(r"^(首页|上页|下页|上一页|下一页|尾页|返回|更多|more|网站首页|部门首页|打印|关闭)$", re.I)
BAD_LINK = re.compile(r"(?:javascript:|mailto:|tel:|#|/index\.htm$|/index\.html$)", re.I)
DETAIL_PATTERN = re.compile(r"/(?:info|article|content|detail)/[^?#]+|/\d{2,}/\d+\.s?html?$|/\d+\.s?html?$", re.I)
HIGH_VALUE = re.compile(r"办事|政策|法规|规章|制度|FAQ|问答|服务|须知|指南|流程|招聘|就业|资源|数据库|借阅|开放科学|出版支持|勤工助学", re.I)
NEWS_ONLY = re.compile(r"新闻|动态|活动回顾|会议|讲座|论坛|风采|党建", re.I)
HOST_LOCKS: dict[str, threading.Lock] = defaultdict(threading.Lock)
HOST_LAST: dict[str, float] = defaultdict(float)


def now() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def normalize(url: str, base: str = "") -> str:
    try:
        absolute = urljoin(base, url.strip())
        p = urlsplit(absolute)
        if p.scheme.lower() not in {"http", "https"} or not p.hostname:
            return ""
        host = p.hostname.lower()
        port = f":{p.port}" if p.port and not ((p.scheme == "http" and p.port == 80) or (p.scheme == "https" and p.port == 443)) else ""
        path = re.sub(r"/{2,}", "/", p.path or "/")
        query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING))
        return urlunsplit((p.scheme.lower(), host + port, path, query, ""))
    except Exception:
        return ""


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=dict), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_title(title: str) -> str:
    value = re.sub(r'[\\/:*?"<>|\r\n]+', "_", title).strip(" ._") or "untitled"
    return value[:80]


def html_decode(data: bytes) -> str:
    return UnicodeDammit(data, is_html=True).unicode_markup or data.decode("utf-8", errors="replace")


def fetch_one(item: dict, raw_dir: Path) -> dict:
    ident, url = item["id"], item["url"]
    path = raw_dir / f"{ident}.html"
    meta = raw_dir / f"{ident}.fetch.json"
    host = (urlsplit(url).hostname or "").lower()
    with HOST_LOCKS[host]:
        delay = 0.35 - (time.monotonic() - HOST_LAST[host])
        if delay > 0:
            time.sleep(delay)
        HOST_LAST[host] = time.monotonic()
    cmd = [
        "curl.exe", "-k", "-L", "--http1.1", "--compressed", "--connect-timeout", "15", "--max-time", "60",
        "--retry", "1", "--retry-delay", "1", "-A", "Mozilla/5.0 (compatible; TsinghuaKnowledgeBot/1.0)",
        "-o", str(path), "-sS", "-w", "%{http_code}\t%{url_effective}\t%{content_type}", url,
    ]
    stamp = now()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=75)
        parts = p.stdout.strip().split("\t")
        status = int(parts[0]) if parts and parts[0].isdigit() else 0
        final_url = parts[1] if len(parts) > 1 else url
        content_type = parts[2] if len(parts) > 2 else ""
        ok = p.returncode == 0 and 200 <= status < 400 and path.exists() and path.stat().st_size >= 200
        out = {"ok": ok, "http_status": status, "final_url": final_url, "content_type": content_type,
               "bytes": path.stat().st_size if path.exists() else 0, "error": p.stderr.strip()[:1000], "crawl_time": stamp}
    except Exception as exc:
        out = {"ok": False, "http_status": 0, "final_url": url, "content_type": "", "bytes": 0,
               "error": str(exc)[:1000], "crawl_time": stamp}
    write_json(meta, out)
    return {**item, **out, "raw_path": str(path)}


def classify_page(item: dict, raw_dir: Path, cleaned_dir: Path, *, parent_list_id: str = "") -> tuple[dict, object | None]:
    if not item.get("ok"):
        return ({**item, "parent_list_id": parent_list_id, "content_quality_class": "content_missing",
                 "extraction_method": "request_failed", "selector_used": "", "quality_gate_pass": False,
                 "total_text_length": 0, "cleaned_text_length": 0, "navigation_like_ratio": 0.0,
                 "main_paragraph_count": 0, "template_removed": False,
                 "diagnostic_reason": item.get("error") or f"HTTP {item.get('http_status', 0)}", "source_file": ""}, None)
    raw_path = Path(item["raw_path"])
    html = html_decode(raw_path.read_bytes())
    final_url = normalize(item.get("final_url") or item["url"]) or item["url"]
    page_kind = detect_page(html, final_url)
    soup = BeautifulSoup(html, "lxml")
    for node in soup.select("script,style,noscript"):
        node.decompose()
    total_len = len(re.sub(r"\s+", " ", soup.get_text(" ", strip=True)))
    if page_kind:
        return ({**item, "url": final_url, "parent_list_id": parent_list_id,
                 "content_quality_class": "content_missing", "extraction_method": page_kind,
                 "selector_used": "", "quality_gate_pass": False, "total_text_length": total_len,
                 "cleaned_text_length": 0, "navigation_like_ratio": 0.0, "main_paragraph_count": 0,
                 "template_removed": False, "diagnostic_reason": page_kind, "source_file": ""}, None)
    page = parse_html(html, final_url, TRACKING)
    q = page.quality
    cls = q.content_quality_class
    if cls == "extraction_failed":
        cls = "content_missing"
    eligible = cls in {"detail_content", "thin_content"} and bool(q.passed)
    title = item.get("title") or (page.soup.title.get_text(" ", strip=True) if page.soup.title else final_url)
    clean_path = cleaned_dir / f"{item['id']}_{safe_title(title)}.md"
    if page.markdown:
        clean_path.parent.mkdir(parents=True, exist_ok=True)
        clean_path.write_text(page.markdown, encoding="utf-8")
        source_file = str(clean_path.relative_to(OUT)).replace("\\", "/")
    else:
        source_file = ""
    row = {**item, "title": title, "url": final_url, "source_domain": (urlsplit(final_url).hostname or "").lower(),
           "parent_list_id": parent_list_id, "content_quality_class": cls,
           "extraction_method": page.extraction_method, "selector_used": page.selector_used,
           "quality_gate_pass": eligible, "total_text_length": total_len,
           "cleaned_text_length": q.total_text_length, "navigation_like_ratio": round(q.navigation_like_ratio, 4),
           "main_paragraph_count": q.main_paragraph_count, "template_removed": bool(page.template_removed),
           "diagnostic_reason": q.reason, "source_file": source_file,
           "content_hash": hashlib.sha256(re.sub(r"\s+", "", page.plain_text).encode("utf-8")).hexdigest() if page.plain_text else ""}
    return row, page


def should_follow(row: dict, prior_yes: set[str]) -> tuple[str, str, int]:
    if row["content_quality_class"] != "list_page":
        return "no", "新结果不是 list_page，不执行下钻。", 99
    text = f"{row.get('title', '')} {row.get('diagnostic_reason', '')}"
    if NEWS_ONLY.search(text) and not re.search(r"通知|服务|学生事务|办事", text):
        return "no", "普通新闻/活动列表，按规则不批量下钻。", 99
    if row["id"] in prior_yes:
        reason = "历史诊断为高价值列表，且本轮仍识别为 list_page；执行一次性直接详情下钻。"
    elif HIGH_VALUE.search(text):
        reason = "本轮识别为政策、办事、服务、FAQ、招聘或资源型高价值列表。"
    else:
        return "no", "未发现足够明确的高价值服务/政策/资源列表信号。", 99
    if re.search(r"办事|指南|流程|须知", text): priority = 1
    elif re.search(r"政策|法规|规章|制度", text): priority = 2
    elif re.search(r"FAQ|问答", text, re.I): priority = 3
    elif re.search(r"服务|资源|数据库|借阅|入馆", text): priority = 4
    elif re.search(r"学生|勤工", text): priority = 5
    elif re.search(r"招聘|就业", text): priority = 6
    else: priority = 7
    return "yes", reason, priority


def direct_links(row: dict, page) -> list[dict]:
    host = row["source_domain"]
    candidates: dict[str, dict] = {}
    for a in page.soup.find_all("a", href=True):
        raw = a.get("href", "").strip()
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        url = normalize(raw, row["url"])
        if not url or BAD_LINK.search(raw) or LIST_NAV.match(title) or (urlsplit(url).hostname or "").lower() != host:
            continue
        if url == normalize(row["url"]) or len(title) < 2:
            continue
        path = urlsplit(url).path.lower()
        if not re.search(r"\.s?html?$", path) and not re.search(r"/info/|/article/|/content/|/detail/|nry", url, re.I):
            continue
        score = 0
        if DETAIL_PATTERN.search(url): score += 6
        if re.search(r"/\d{3,}/\d+\.s?html?$", path): score += 4
        if 4 <= len(title) <= 80: score += 2
        if HIGH_VALUE.search(title): score += 2
        if a.find_parent("li"): score += 2
        ancestry = " ".join(" ".join(x.get("class", [])) for x in a.parents if getattr(x, "get", None))
        if re.search(r"list|news|item|content|article|result|zy|service", ancestry, re.I): score += 2
        if NEWS_ONLY.search(title) and not HIGH_VALUE.search(title): score -= 2
        if score < 5:
            continue
        old = candidates.get(url)
        cand = {"parent_list_id": row["id"], "parent_title": row["title"], "title": title[:300],
                "url": url, "source_domain": host, "link_score": score, "parent_priority": row["follow_priority"]}
        if old is None or score > old["link_score"]:
            candidates[url] = cand
    return sorted(candidates.values(), key=lambda x: (-x["link_score"], x["title"], x["url"]))


def historical_urls() -> set[str]:
    found: set[str] = set()
    roots = [ROOT / "data_first", ROOT / "data_second"]
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or OUT in path.parents or path.stat().st_size > 8_000_000:
                continue
            try:
                if path.suffix.lower() == ".csv":
                    for row in read_csv(path):
                        for key in ("url", "source_url", "final_url", "canonical", "canonical_url"):
                            value = normalize(row.get(key, ""))
                            if value: found.add(value)
                elif path.suffix.lower() == ".jsonl":
                    with path.open(encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            try: row = json.loads(line)
                            except Exception: continue
                            for key in ("url", "source_url", "final_url", "canonical", "canonical_url"):
                                value = normalize(str(row.get(key, "")))
                                if value: found.add(value)
            except Exception:
                continue
    return found


def main() -> None:
    for rel in ("source_manifest", "raw/base", "raw/follow", "extracted/base", "extracted/follow", "list_pages/content",
                "follow_pages", "audit/raw_api", "human_check", "diagnostics", "reports", "intermediate"):
        (OUT / rel).mkdir(parents=True, exist_ok=True)

    candidates = read_csv(RUN6 / "reports" / "candidates.csv")
    old_diag = json.loads((DIAGNOSTIC / "final_records.json").read_text(encoding="utf-8"))
    old_audit = {r["id"]: r for r in read_csv(RUN6 / "audit" / "audit_results.csv")}
    diag_by_id = {r["id"]: r for r in old_diag}
    if len(candidates) != 300 or len(diag_by_id) != 300 or {r["id"] for r in candidates} != set(diag_by_id):
        raise SystemExit("固定清单或旧诊断未能 300/300 对齐")
    manifest = []
    for c in sorted(candidates, key=lambda x: x["id"]):
        d, a = diag_by_id[c["id"]], old_audit[c["id"]]
        manifest.append({"old_id": c["id"], "id": c["id"], "title": c["title"], "url": c["url"],
                         "source_domain": c["source_domain"], "old_action": a["action"],
                         "old_category": a["category"], "old_content_type": a["content_type"],
                         "old_content_quality_class": d["content_quality_class"]})
    write_json(OUT / "intermediate" / "manifest.json", manifest)

    print("[重抓] 固定 300 条开始", flush=True)
    fetched = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_one, r, OUT / "raw" / "base"): r for r in manifest}
        for i, fut in enumerate(as_completed(futures), 1):
            fetched.append(fut.result())
            if i % 20 == 0 or i == 300:
                print(f"[重抓] {i}/300 请求成功={sum(bool(x['ok']) for x in fetched)}", flush=True)
    fetched.sort(key=lambda x: x["id"])
    base_rows, pages = [], {}
    for item in fetched:
        row, page = classify_page(item, OUT / "raw" / "base", OUT / "extracted" / "base")
        base_rows.append(row)
        if page is not None: pages[row["id"]] = page
    prior_yes = {r["id"] for r in old_diag if r.get("should_follow_links") == "yes"}
    for row in base_rows:
        follow, reason, priority = should_follow(row, prior_yes)
        row["should_follow_links"], row["follow_link_reason"], row["follow_priority"] = follow, reason, priority
    write_jsonl(OUT / "intermediate" / "base_quality.jsonl", base_rows)
    print("[质量] " + json.dumps(Counter(r["content_quality_class"] for r in base_rows), ensure_ascii=False), flush=True)

    history = historical_urls()
    base_urls = {normalize(r["url"]) for r in base_rows}
    discovered = []
    for row in base_rows:
        if row["should_follow_links"] == "yes" and row["id"] in pages:
            links = direct_links(row, pages[row["id"]])
            row["discovered_direct_links"] = len(links)
            discovered.extend(links)
        else:
            row["discovered_direct_links"] = 0
    # Global exact URL de-duplication and fixed 100-page cap, honoring requested priority order.
    dedup, seen = [], set()
    for link in sorted(discovered, key=lambda x: (x["parent_priority"], -x["link_score"], x["parent_list_id"], x["url"])):
        u = normalize(link["url"])
        if not u or u in seen or u in base_urls or u in history:
            continue
        seen.add(u); dedup.append(link)
        if len(dedup) >= 100: break
    for i, link in enumerate(dedup, 1):
        link["id"] = f"PUBFOLLOW{i:06d}"
    print(f"[下钻] 应跟进列表={sum(r['should_follow_links']=='yes' for r in base_rows)} 发现链接={len(discovered)} 历史去重后选取={len(dedup)}", flush=True)
    write_jsonl(OUT / "intermediate" / "base_quality.jsonl", base_rows)
    write_jsonl(OUT / "intermediate" / "follow_discovered.jsonl", discovered)
    write_jsonl(OUT / "intermediate" / "follow_selected.jsonl", dedup)

    followed = []
    if dedup:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fetch_one, r, OUT / "raw" / "follow"): r for r in dedup}
            done = []
            for i, fut in enumerate(as_completed(futures), 1):
                done.append(fut.result())
                if i % 20 == 0 or i == len(dedup):
                    print(f"[下钻抓取] {i}/{len(dedup)} 请求成功={sum(bool(x['ok']) for x in done)}", flush=True)
        done.sort(key=lambda x: x["id"])
        existing_hashes = {r.get("content_hash") for r in base_rows if r.get("content_hash")}
        existing_titles = {re.sub(r"\W+", "", r.get("title", "")).lower() for r in base_rows}
        for item in done:
            row, _ = classify_page(item, OUT / "raw" / "follow", OUT / "extracted" / "follow", parent_list_id=item["parent_list_id"])
            title_key = re.sub(r"\W+", "", row.get("title", "")).lower()
            duplicate_reason = ""
            if row.get("content_hash") and row["content_hash"] in existing_hashes: duplicate_reason = "content_hash_duplicate"
            elif title_key and title_key in existing_titles: duplicate_reason = "exact_normalized_title_duplicate"
            row["dedupe_status"] = "duplicate" if duplicate_reason else "unique"
            row["dedupe_reason"] = duplicate_reason
            if duplicate_reason: row["quality_gate_pass"] = False
            else:
                if row.get("content_hash"): existing_hashes.add(row["content_hash"])
                if title_key: existing_titles.add(title_key)
            followed.append(row)
    write_jsonl(OUT / "intermediate" / "follow_quality.jsonl", followed)
    eligible = [r for r in base_rows + followed if r.get("quality_gate_pass") is True]
    write_jsonl(OUT / "intermediate" / "audit_candidates.jsonl", eligible)
    summary = {"fixed_urls": 300, "fetch_success": sum(r["ok"] for r in base_rows),
               "fetch_failed": sum(not r["ok"] for r in base_rows), "quality_classes": dict(Counter(r["content_quality_class"] for r in base_rows)),
               "quality_gate_pass": sum(r["quality_gate_pass"] for r in base_rows), "list_pages": sum(r["content_quality_class"] == "list_page" for r in base_rows),
               "list_follow_yes": sum(r["should_follow_links"] == "yes" for r in base_rows), "follow_discovered": len(discovered),
               "follow_selected_after_dedupe": len(dedup), "follow_fetch_success": sum(r.get("ok", False) for r in followed),
               "follow_quality_gate_pass": sum(r.get("quality_gate_pass", False) for r in followed), "audit_candidates": len(eligible)}
    write_json(OUT / "intermediate" / "extraction_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
