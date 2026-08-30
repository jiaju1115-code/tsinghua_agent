"""Resume-safe public crawl for the isolated Trusted Campus V2 candidate."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "01_public_baseline"
RUN_ROOT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2" / "public_crawl_v1"
SEEDS = ROOT / "configs" / "trusted_campus_agent_v2" / "public_crawl_seeds.txt"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
if str(BASELINE) not in sys.path:
    sys.path.insert(0, str(BASELINE))

from crawler import discovery as crawler_discovery
from crawler import runner as crawler_runner
from crawler.parser import detect_page as baseline_detect_page


# V2 serves eight campus-affairs scenarios.  The reused baseline crawler was
# intentionally biased toward everyday campus services, so replace only this
# process' queue scorer; the baseline package and frozen knowledge base remain
# untouched.
V2_HIGH_VALUE = (
    "教务", "学籍", "选课", "培养", "转系", "转专业", "辅修", "学位", "毕业", "离校",
    "学生事务", "奖学金", "助学金", "资助", "住宿", "宿舍", "办事", "流程", "指南", "办法",
    "新生", "报到", "迎新", "入学", "校园卡", "网络", "图书馆", "校医院", "食堂", "校车",
    "科研", "科研实践", "本科生研究", "实验室安全", "项目申报", "伦理审查", "知识产权",
    "国际", "交换", "访学", "签证", "出国", "留学", "国际学生",
    "就业", "招聘", "生涯", "职业发展", "三方协议", "就业手续", "档案", "户口",
    "规定", "条例", "细则", "申请", "材料", "截止", "常见问题", "faq",
)
V2_LOW_VALUE = (
    "荣誉奖励", "党建园地", "人物采访", "校友新闻", "会议新闻", "学术报告",
    "科研成果", "媒体清华", "图片新闻", "首页轮播", "院系动态",
)
V2_SERVICE_HOSTS = (
    "academic.tsinghua.edu.cn", "yjsy.tsinghua.edu.cn", "xsg.tsinghua.edu.cn",
    "career.tsinghua.edu.cn", "is.tsinghua.edu.cn", "join-tsinghua.edu.cn",
    "international.tsinghua.edu.cn", "rd.tsinghua.edu.cn", "kyy.tsinghua.edu.cn",
)
V2_PATH_HINTS = (
    "/yjsy/", "/xsg", "/xssqglfwzx/", "/xsglfww/", "/kygl", "/gjjl",
    "/international/", "/career/", "/employment/", "/graduate/", "/freshman/",
)
V2_SEED_URLS = {
    line.strip().rstrip("/")
    for line in SEEDS.read_text(encoding="utf-8-sig").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
}
PUBLIC_DETAIL_HOSTS = {"career.tsinghua.edu.cn"}


def v2_detect_page(html: str, final_url: str) -> str | None:
    reason = baseline_detect_page(html, final_url)
    host = (urlsplit(final_url).hostname or "").lower()
    is_curated_detail = final_url.rstrip("/") in V2_SEED_URLS and bool(re.search(r"/info/\d+/\d+\.html?$", urlsplit(final_url).path, re.I))
    has_password_form = bool(re.search(r"<input[^>]+type=[\"']?password", html, re.I))
    visible_chars = len(re.sub(r"<[^>]+>", " ", html))
    if reason == "login_required" and host in PUBLIC_DETAIL_HOSTS and is_curated_detail and not has_password_form and visible_chars >= 800:
        return None
    return reason


def retry_curated_false_auth() -> None:
    database = RUN_ROOT / "data" / "crawl_state.db"
    if not database.is_file():
        return
    safe_urls = [url for url in V2_SEED_URLS if (urlsplit(url).hostname or "").lower() in PUBLIC_DETAIL_HOSTS and re.search(r"/info/\d+/\d+\.html?$", urlsplit(url).path, re.I)]
    with sqlite3.connect(database) as connection:
        connection.executemany("UPDATE urls SET status='pending', error=NULL WHERE url=? AND status='auth_required'", ((url,) for url in safe_urls))


def v2_priority_score(url: str, text: str = "") -> int:
    haystack = f"{url} {text}".lower()
    seed_bonus = 120 if url.rstrip("/") in V2_SEED_URLS else 0
    host_bonus = 18 if any(host in haystack for host in V2_SERVICE_HOSTS) else 0
    path_bonus = 18 if any(marker in haystack for marker in V2_PATH_HINTS) else 0
    return (
        seed_bonus
        + host_bonus
        + path_bonus
        + 12 * sum(marker.lower() in haystack for marker in V2_HIGH_VALUE)
        - 18 * sum(marker.lower() in haystack for marker in V2_LOW_VALUE)
    )


crawler_runner.priority_score = v2_priority_score
crawler_discovery.priority_score = v2_priority_score
crawler_runner.detect_page = v2_detect_page
Crawler = crawler_runner.Crawler


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl public official Tsinghua pages into an isolated V2 candidate directory.")
    parser.add_argument("--max-pages", type=int, default=1200)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--delay", type=float, default=1.0, help="minimum seconds between requests to the same host")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    if args.max_pages < 1 or args.max_pages > 5000:
        raise SystemExit("--max-pages must be between 1 and 5000")
    if args.concurrency < 1 or args.concurrency > 4:
        raise SystemExit("--concurrency must be between 1 and 4")
    if args.delay < 0.5:
        raise SystemExit("--delay must be at least 0.5 seconds per host")
    config = {
        "seeds_file": str(SEEDS),
        "max_pages": args.max_pages,
        "max_depth": args.max_depth,
        "concurrency": args.concurrency,
        "request_delay_seconds": args.delay,
        "timeout_seconds": 25,
        "max_retries": 2,
        "test_mode": False,
        "test_max_pages": args.max_pages,
        "user_agent": "TsingAskTrustedCampusV2/1.0 (official-campus-knowledge; respectful; contact via project owner)",
        "allowed_domain": "tsinghua.edu.cn",
        "min_content_chars": 120,
        "max_response_bytes": 10_485_760,
        "retry_failed_on_start": args.retry_failed,
        "tracking_parameters": ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "spm", "from"],
        "public_raw_dir": "knowledge/01_raw_public",
        "sitemap_enabled": True,
        "sitemap_max_urls_per_seed": 300,
        "possible_duplicate_threshold": 0.92,
    }
    for relative in ("data", "logs", "knowledge"):
        (RUN_ROOT / relative).mkdir(parents=True, exist_ok=True)
    retry_curated_false_auth()
    stats = Crawler(config, RUN_ROOT).run()
    summary = {
        "version": "TRUSTED_CAMPUS_V2_PUBLIC_CRAWL_V1",
        "candidate_only": True,
        "frozen_v1_modified": False,
        "finished_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "config": {key: value for key, value in config.items() if key != "user_agent"},
        "stats": asdict(stats),
    }
    (RUN_ROOT / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
