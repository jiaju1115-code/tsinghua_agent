from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

class SearchMode(StrEnum):
    CAMPUS_PUBLIC = "CAMPUS_PUBLIC"
    ACADEMIC_RETRIEVAL = "ACADEMIC_RETRIEVAL"
    GENERAL_WEB = "GENERAL_WEB"
    NO_WEB_NEEDED = "NO_WEB_NEEDED"
    UNCERTAIN = "UNCERTAIN"

@dataclass(frozen=True)
class Route:
    mode: SearchMode
    reason: str

CAMPUS = ("清华", "清华大学", "校园卡", "图书馆", "选课", "奖学金", "助学金", "校车", "校历", "教务", "出入校", "宿舍")
ACADEMIC = ("积分", "矩阵", "泊松分布", "牛顿第二定律", "边际成本", "ols", "时间复杂度", "概率", "线性代数", "微分", "导数", "算法", "数据结构", "傅里叶", "经济学")
FRESH = ("最新", "今天", "目前", "最近", "新闻", "当前", "2025", "2026")
SIMPLE = re.compile(r"^\s*\d+(?:\.\d+)?\s*[+\-*/]\s*\d+(?:\.\d+)?\s*(?:等于多少|=)?\s*\?？?\s*$")

def route_query(query: str) -> Route:
    q = query.lower().strip()
    if SIMPLE.match(q) or q in {"1+1等于多少", "1+1=?"}:
        return Route(SearchMode.NO_WEB_NEEDED, "basic arithmetic is stable and needs no external evidence")
    if any(word in q for word in CAMPUS):
        return Route(SearchMode.CAMPUS_PUBLIC, "matched campus-public keyword")
    if any(word in q for word in ACADEMIC) or re.search(r"[∫∑√λμσ]|\b(?:var|cov|pdf|cdf)\b", q):
        return Route(SearchMode.ACADEMIC_RETRIEVAL, "matched academic concept or mathematical notation")
    if any(word in q for word in FRESH):
        return Route(SearchMode.GENERAL_WEB, "matched freshness/current-events keyword")
    if len(q) < 4:
        return Route(SearchMode.UNCERTAIN, "query is too short for dependable rule routing")
    return Route(SearchMode.GENERAL_WEB, "default public-web route for a non-stable informational query")
