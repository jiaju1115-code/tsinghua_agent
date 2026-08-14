from __future__ import annotations
from .source_quality import AUTHORITY_SCORES

def rank_sources(records: list[dict], mode: str, query: str) -> list[dict]:
    terms = set(query.lower().split())
    campus_bias = .45 if mode == "CAMPUS_PUBLIC" else (.25 if mode == "ACADEMIC_RETRIEVAL" else .20)
    for r in records:
        haystack = (r.get("title", "") + " " + r.get("content", "")).lower()
        relevance = sum(term in haystack for term in terms) / max(len(terms), 1)
        authority = AUTHORITY_SCORES.get(r.get("source_authority_level", "UNKNOWN"), .2)
        r["rank_score"] = round((campus_bias * authority) + ((1-campus_bias) * relevance) + .05 * float(r.get("score") or 0), 4)
    return sorted(records, key=lambda item: item["rank_score"], reverse=True)
