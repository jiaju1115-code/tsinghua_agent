from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
V1_ROOT = ROOT / "data" / "03_knowledge_base" / "v1"
DEFAULT_CATALOG = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2" / "metadata_catalog.jsonl"
SHADOW_ROOT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2" / "shadow_bundle_v1"

REQUIRED_METADATA = (
    "source", "department", "publish_date", "effective_date", "expiry_date",
    "audience", "authority_level", "topic",
)

CATEGORY_TOPIC = {
    "教务与学籍": "教务", "教学与培养": "教务", "学生事务": "学生事务",
    "奖助与资助": "学生事务", "住宿服务": "校园生活", "餐饮服务": "校园生活",
    "交通服务": "校园生活", "医疗健康": "校园生活", "网络与信息化": "校园生活",
    "图书馆服务": "校园生活", "体育与场馆": "校园生活",
    "科研参与与资源导航": "科研实践", "科研通知": "科研实践",
    "国际事务与签证": "国际交流", "就业与职业发展": "就业",
}

DEPARTMENT_HINTS = {
    "academic.tsinghua.edu.cn": "教务处",
    "yjsy.tsinghua.edu.cn": "研究生院",
    "xsg.tsinghua.edu.cn": "学生部",
    "xssq.tsinghua.edu.cn": "学生社区管理服务中心",
    "career.tsinghua.edu.cn": "学生职业发展指导中心",
    "is.tsinghua.edu.cn": "国际学生学者中心",
    "international.tsinghua.edu.cn": "国际合作与交流处",
    "lib.tsinghua.edu.cn": "图书馆",
    "www.lib.tsinghua.edu.cn": "图书馆",
    "www.itc.tsinghua.edu.cn": "信息化技术中心",
    "xyy.tsinghua.edu.cn": "校医院",
    "peace.tsinghua.edu.cn": "保卫处",
    "rd.tsinghua.edu.cn": "科研院",
    "kyy.tsinghua.edu.cn": "科研院",
    "yz.tsinghua.edu.cn": "研究生招生办公室",
    "join-tsinghua.edu.cn": "本科招生办公室",
    "info.tsinghua.edu.cn": "信息化技术中心",
    "its.tsinghua.edu.cn": "信息化技术中心",
}


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def parse_iso_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _title_date(title: str) -> str | None:
    match = re.search(r"(?<!\d)(20\d{2})[.年/-](\d{1,2})[.月/-](\d{1,2})", title)
    if not match:
        return None
    try:
        return date(*(int(part) for part in match.groups())).isoformat()
    except ValueError:
        return None


def infer_department(url: str, title: str = "") -> str:
    host = urlparse(url).hostname or ""
    for domain, department in DEPARTMENT_HINTS.items():
        if host == domain or host.endswith(f".{domain}"):
            return department
    hints = (
        ("教务", "教务处"), ("研究生院", "研究生院"), ("学生社区", "学生社区管理服务中心"),
        ("校医院", "校医院"), ("图书馆", "图书馆"), ("科研", "科研院"),
        ("就业", "学生职业发展指导中心"), ("国际", "国际合作与交流处"),
    )
    return next((value for marker, value in hints if marker in title), "清华大学相关部门")


def infer_topics(category: str, title: str, text: str = "") -> list[str]:
    marker_groups = {
        "教务": ("教务", "学籍", "选课", "培养方案", "转系", "转专业", "辅修", "课程", "考试", "成绩", "学位"),
        "学生事务": ("学生事务", "学生手册", "奖学金", "助学金", "资助", "勤工助学", "学生工作", "评优", "社团"),
        "校园生活": ("宿舍", "住宿", "食堂", "餐饮", "校园卡", "校车", "交通", "图书馆", "借阅", "校医院", "就医", "校园网", "vpn", "体育馆", "场馆"),
        "科研实践": ("科研", "科研实践", "实验室", "项目申报", "学术研究", "伦理审查", "知识产权", "srt"),
        "国际交流": ("国际交流", "交换", "访学", "签证", "出国", "留学", "国际学生", "港澳台"),
        "就业": ("就业", "招聘", "生涯", "职业发展", "三方协议", "就业手续", "毕业去向", "档案", "户口"),
        "新生": ("新生", "入学报到", "迎新", "预报到"),
        "毕业": ("毕业", "离校", "学位证", "毕业证", "毕业生"),
    }
    ordered: list[str] = []

    def add_matches(value: str) -> None:
        lowered = value.lower()
        for topic, markers in marker_groups.items():
            if topic not in ordered and any(marker in lowered for marker in markers):
                ordered.append(topic)

    # A specific title is the best signal for the primary topic. Category is
    # next; body text only expands the multi-topic list and must not take over
    # the primary label because long handbooks often mention every domain.
    add_matches(title)
    mapped = CATEGORY_TOPIC.get(category)
    if mapped and mapped not in ordered:
        ordered.append(mapped)
    add_matches(text[:3000])
    return ordered or ["学生事务"]


def infer_content_type(title: str, text: str = "") -> str:
    joined = f"{title}\n{text[:3000]}"
    if re.search(r"(?:办法|规定|条例|细则|制度|章程|管理规则)", joined):
        return "policy"
    if re.search(r"(?:办理|办事|申请|流程|步骤|指南|须知|材料|入口|常见问题|FAQ)", joined, re.I):
        return "procedure_guide"
    if re.search(r"(?:通知|公告|公示)", title):
        return "notice"
    if re.search(r"(?:问答|常见问题|FAQ)", joined, re.I):
        return "faq"
    return "reference"


def normalize_source_date(value: Any) -> str | None:
    if not value:
        return None
    match = re.search(r"(?<!\d)(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})日?", str(value))
    if not match:
        return None
    try:
        return date(*(int(part) for part in match.groups())).isoformat()
    except ValueError:
        return None


def infer_audience(title: str, text: str = "") -> list[str]:
    joined = f"{title}\n{text[:1200]}"
    audience = []
    for marker, label in (
        ("本科生", "本科生"), ("研究生", "研究生"), ("博士生", "博士生"),
        ("国际学生", "国际学生"), ("新生", "新生"), ("毕业生", "毕业生"),
        ("教师", "教职工"), ("教职工", "教职工"),
    ):
        if marker in joined:
            audience.append(label)
    return sorted(set(audience)) or ["全校学生"]


def authority_level(url: str, source_type: str = "public") -> str:
    host = (urlparse(url).hostname or "").lower()
    if source_type == "restricted":
        return "official_internal"
    if host == "tsinghua.edu.cn" or host.endswith(".tsinghua.edu.cn"):
        return "official"
    if host.endswith(".edu.cn") or host.endswith(".gov.cn"):
        return "authoritative_external"
    return "unverified"


def policy_key(title: str) -> str:
    value = re.sub(r"20\d{2}[.年/-]\d{1,2}(?:[.月/-]\d{1,2})?", "", title)
    value = re.sub(r"（.*?(修订|版本).*?）|\[.*?\]", "", value)
    value = re.sub(r"[_\s-]*清[\u4e00-\u9fff]{0,8}发〔20\d{2}〕\d+号", "", value)
    value = re.sub(r"[-—_]\s*清华大学.*$", "", value)
    value = value.replace("《", "").replace("》", "")
    return re.sub(r"\W+", "", value).lower()[:80]


def metadata_from_v1(row: dict[str, Any], text: str = "") -> dict[str, Any]:
    published = _title_date(row.get("title", ""))
    effective = row.get("valid_from") or published
    expiry = row.get("valid_until") or None
    topics = infer_topics(row.get("category", ""), row.get("title", ""), text)
    return {
        "source_id": row["canonical_source_id"],
        "title": row.get("title", ""),
        "source": row.get("url", ""),
        "department": infer_department(row.get("url", ""), row.get("title", "")),
        "publish_date": published,
        "effective_date": effective,
        "expiry_date": expiry,
        "audience": infer_audience(row.get("title", ""), text),
        "authority_level": authority_level(row.get("url", ""), row.get("source_type", "public")),
        "topic": topics[0],
        "topics": topics,
        "category": row.get("category", ""),
        "content_type": row.get("content_type", ""),
        "time_status": row.get("time_status", "unknown"),
        "access_level": "restricted" if row.get("source_type") == "restricted" else "public",
        "admission_status": "serving",
        "review_status": row.get("review_status", "approved_frozen_v1"),
        "policy_key": policy_key(row.get("title", "")),
        "source_version": "KNOWLEDGE_BASE_V1",
    }


def load_catalog(path: Path | str = DEFAULT_CATALOG) -> dict[str, dict[str, Any]]:
    return {row["source_id"]: row for row in jsonl(Path(path))}


def load_v1_catalog() -> dict[str, dict[str, Any]]:
    """Derive V2 metadata from the immutable V1 manifest without writing V1."""
    manifest = jsonl(V1_ROOT / "manifests" / "source_manifest.jsonl")
    return {
        row["canonical_source_id"]: metadata_from_v1(row)
        for row in manifest
        if row.get("canonical_source_id")
    }


def temporal_status(metadata: dict[str, Any], as_of: date) -> str:
    effective = parse_iso_date(metadata.get("effective_date"))
    expiry = parse_iso_date(metadata.get("expiry_date"))
    if expiry and expiry < as_of:
        return "expired"
    if effective and effective > as_of:
        return "upcoming"
    if not effective and not expiry:
        return "unknown"
    return "active"


def metadata_completeness(rows: Iterable[dict[str, Any]]) -> float:
    rows = list(rows)
    if not rows:
        return 0.0
    present = sum(row.get(field) not in (None, "", []) for row in rows for field in REQUIRED_METADATA)
    return present / (len(rows) * len(REQUIRED_METADATA))
