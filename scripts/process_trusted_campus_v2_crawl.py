"""Turn isolated crawl output into an automatically quality-gated V2 manifest.

Raw crawl files are evidence inventory, not serving knowledge.  This processor
deduplicates them, infers the required trust metadata and rejects obvious news,
profile and navigation material before the remaining records enter strict
automated trust review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
V2_ROOT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2"
PUBLIC_ROOT = V2_ROOT / "public_crawl_v1"
PORTAL_ROOT = V2_ROOT / "portal_crawl_v1"
OUTPUT_MANIFEST = V2_ROOT / "crawl_candidate_manifest.jsonl"
OUTPUT_REPORT = V2_ROOT / "crawl_quality_report.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2.metadata import (
    authority_level,
    infer_audience,
    infer_content_type,
    infer_department,
    infer_topics,
    normalize_source_date,
    policy_key,
)


LOW_VALUE_TITLE = re.compile(
    r"(?:荣誉奖励|党建园地|医院动态|中心简介|机构设置|联系我们|首页轮播|"
    r"采访手记|人物专访|专题学习|新闻联播|媒体清华|校友风采|学术报告|成果速递)"
)
GENERIC_TITLE = re.compile(r"^(?:服务|通知公告|特别关注|借阅导引|特色馆藏|首页|更多)$")
AFFAIRS_MARKERS = re.compile(
    r"(?:申请|办理|流程|步骤|条件|材料|截止|入口|规定|办法|条例|细则|须知|"
    r"学籍|选课|培养|转系|毕业|离校|奖学金|助学金|资助|宿舍|食堂|校车|"
    r"校园卡|校园网|借阅|开馆|就医|挂号|科研|实验室|伦理|知识产权|交换|"
    r"签证|出国|国际学生|就业|招聘|三方协议|档案|户口|新生|报到|迎新)"
)
ACTION_MARKERS = re.compile(r"(?:申请|办理|流程|步骤|条件|材料|截止|入口|须知|常见问题|FAQ|提交|审核|领取|预约|报到)", re.I)
SERVICE_FACTS = re.compile(r"(?:开放时间|运行时间|办理时间|咨询电话|联系电话|地址|地点|费用|收费|工作日|节假日|服务入口|在线系统)")
DATE_RE = re.compile(r"(?<!\d)(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})日?")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parsed.scheme.lower() or "https", parsed.netloc.lower(), path, parsed.query, ""))


def body_from_markdown(path: Path) -> str:
    if not path.is_file():
        return ""
    value = path.read_text(encoding="utf-8-sig", errors="replace")
    if value.startswith("---"):
        parts = value.split("---", 2)
        if len(parts) == 3:
            value = parts[2]
    value = re.split(r"\n---\n\n## 来源信息", value, maxsplit=1)[0]
    return value.strip()


def first_date(*values: Any) -> str | None:
    for value in values:
        normalized = normalize_source_date(value)
        if normalized:
            return normalized
    return None


def labeled_date(text: str, labels: str) -> str | None:
    match = re.search(rf"(?:{labels})\s*[：:]?\s*{DATE_RE.pattern}", text[:5000])
    return first_date(match.group(0)) if match else None


def source_access(row: dict[str, Any]) -> str:
    host = (urlsplit(row.get("final_url") or row.get("source_url") or row.get("url") or "").hostname or "").lower()
    authenticated_hosts = {"info.tsinghua.edu.cn", "webvpn.tsinghua.edu.cn", "id.tsinghua.edu.cn"}
    if row.get("source_mode") == "authenticated_portal" and (host in authenticated_hosts or host.endswith(".info.tsinghua.edu.cn")):
        return "campus_authenticated"
    return "public"


def assess(title: str, body: str, published: str | None, content_type: str, topics: list[str]) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    visible = re.sub(r"\s+", " ", body)
    if len(visible) < 200:
        reasons.append("CONTENT_TOO_SHORT")
    if LOW_VALUE_TITLE.search(title):
        reasons.append("LOW_VALUE_NEWS_OR_PROFILE")
    sample = f"{title}\n{visible[:5000]}"
    subject_relevant = bool(AFFAIRS_MARKERS.search(sample))
    action_signal = bool(ACTION_MARKERS.search(sample))
    service_reference = subject_relevant and bool(SERVICE_FACTS.search(sample))
    actionable = content_type in {"policy", "procedure_guide", "faq"} or action_signal or service_reference
    if GENERIC_TITLE.search(title) and not actionable:
        reasons.append("GENERIC_NON_ACTIONABLE_TITLE")
    if not subject_relevant:
        reasons.append("NO_CAMPUS_AFFAIRS_SIGNAL")
    elif not actionable:
        reasons.append("NO_ACTIONABLE_OR_SERVICE_FACTS")
    score = 0.25
    score += 0.25 if content_type in {"policy", "procedure_guide", "faq"} else 0.08
    score += 0.20 if len(visible) >= 500 else 0.10 if len(visible) >= 200 else 0.0
    score += 0.15 if published else 0.0
    score += 0.15 if topics and topics != ["学生事务"] else 0.05
    status = "auto_review_candidate" if not reasons and score >= 0.58 else "rejected_quality"
    return status, round(score, 4), reasons


def row_to_candidate(row: dict[str, Any], crawl_root: Path, source_version: str) -> dict[str, Any]:
    relative = row.get("markdown_path", "")
    content_path = crawl_root / relative
    body = body_from_markdown(content_path)
    title = row.get("title", "").strip()
    url = row.get("final_url") or row.get("source_url") or row.get("url") or ""
    published = first_date(row.get("published_at"), title, body[:2500])
    effective = labeled_date(body, r"自|施行日期|实施日期|执行日期|生效日期")
    expiry = labeled_date(body, r"有效期至|有效截至|废止日期")
    content_type = infer_content_type(title, body)
    topics = infer_topics(row.get("category_hint", ""), title, body)
    admission, quality_score, reasons = assess(title, body, published, content_type, topics)
    access = source_access(row)
    raw_id = row.get("id") or hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    department = row.get("department") or infer_department(url, title)
    return {
        "source_id": f"CRAWL_{raw_id}",
        "title": title,
        "source": url,
        "department": department,
        "publish_date": published,
        "effective_date": effective,
        "expiry_date": expiry,
        "audience": infer_audience(title, body),
        "authority_level": authority_level(url, "restricted" if access != "public" else "public"),
        "topic": topics[0],
        "topics": topics,
        "category": row.get("category_hint", ""),
        "content_type": content_type,
        "time_status": "unknown" if not effective and not expiry else "dated",
        "access_level": access,
        "admission_status": admission,
        "review_status": "pending_automated_review" if admission == "auto_review_candidate" else "auto_quality_rejected",
        "policy_key": policy_key(title),
        "source_version": source_version,
        "candidate_content_file": str(content_path.relative_to(ROOT)).replace("\\", "/"),
        "content_hash": row.get("content_hash") or hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "content_length": len(body),
        "crawled_at": row.get("crawled_at"),
        "quality_score": quality_score,
        "quality_reasons": reasons,
        "candidate_reason": "isolated official crawl; strict automated trust review required before serving",
    }


def build() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources = (
        [(row, PUBLIC_ROOT, "TRUSTED_CAMPUS_V2_PUBLIC_CRAWL_V1") for row in load_jsonl(PUBLIC_ROOT / "knowledge" / "index.jsonl")]
        + [(row, PORTAL_ROOT, "TRUSTED_CAMPUS_V2_PORTAL_CRAWL_V1") for row in load_jsonl(PORTAL_ROOT / "knowledge" / "portal_index.jsonl")]
    )
    kept: list[dict[str, Any]] = []
    duplicate_rows = 0
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    for raw, crawl_root, version in sources:
        candidate = row_to_candidate(raw, crawl_root, version)
        url_key = canonical_url(candidate["source"])
        hash_key = candidate["content_hash"]
        if url_key in seen_urls or (hash_key and hash_key in seen_hashes):
            duplicate_rows += 1
            continue
        seen_urls.add(url_key)
        if hash_key:
            seen_hashes.add(hash_key)
        kept.append(candidate)
    status_counts = Counter(row["admission_status"] for row in kept)
    topic_counts = Counter(topic for row in kept if row["admission_status"] == "auto_review_candidate" for topic in row["topics"])
    report = {
        "version": "TRUSTED_CAMPUS_V2_CRAWL_QUALITY_REPORT_V1",
        "candidate_only": True,
        "raw_index_rows": len(sources),
        "unique_rows": len(kept),
        "duplicate_rows": duplicate_rows,
        "status_counts": dict(sorted(status_counts.items())),
        "review_queue_by_topic": dict(sorted(topic_counts.items())),
        "dated_review_candidates": sum(bool(row["publish_date"] or row["effective_date"] or row["expiry_date"]) for row in kept if row["admission_status"] == "auto_review_candidate"),
        "authenticated_review_candidates": sum(row["access_level"] != "public" for row in kept if row["admission_status"] == "auto_review_candidate"),
    }
    return kept, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="replace only generated V2 crawl review artifacts")
    args = parser.parse_args()
    if not args.force and (OUTPUT_MANIFEST.exists() or OUTPUT_REPORT.exists()):
        raise SystemExit("refusing to overwrite generated crawl review artifacts; pass --force")
    rows, report = build()
    V2_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    OUTPUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
