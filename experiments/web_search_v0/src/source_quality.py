from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

AUTHORITY_SCORES = {"OFFICIAL_THSINGHUA": 1.0, "OFFICIAL_GOV": .92, "ACADEMIC": .82, "OFFICIAL_COMPANY": .78, "REPUTABLE_MEDIA": .70, "GENERAL_WEB": .40, "UNKNOWN": .20}

@dataclass(frozen=True)
class QualityAssessment:
    authority: str
    verdict: str
    reasons: list[str]

def authority_for_url(url: str) -> str:
    domain = urlparse(url).netloc.lower().split(":")[0]
    if domain == "tsinghua.edu.cn" or domain.endswith(".tsinghua.edu.cn"): return "OFFICIAL_THSINGHUA"
    if domain.endswith(".gov.cn") or domain.endswith(".gov"): return "OFFICIAL_GOV"
    if domain.endswith(".edu") or domain.endswith(".edu.cn") or "arxiv.org" in domain: return "ACADEMIC"
    if domain in {"openai.com", "docs.python.org", "developer.mozilla.org", "microsoft.com", "apple.com"}: return "OFFICIAL_COMPANY"
    if domain in {"reuters.com", "apnews.com", "bbc.com", "nature.com"}: return "REPUTABLE_MEDIA"
    if not domain: return "UNKNOWN"
    return "GENERAL_WEB"

def assess_source(url: str, text: str) -> QualityAssessment:
    authority = authority_for_url(url)
    lower = text.lower().strip()
    reasons = []
    if not lower: reasons.append("empty extracted text")
    if len(lower) < 120: reasons.append("body is too short")
    if any(x in lower for x in ("login required", "sign in to", "access denied", "404 not found")): reasons.append("login or error page detected")
    if sum(x in lower for x in ("home", "navigation", "menu", "cookie")) >= 3 and len(lower) < 500: reasons.append("likely navigation-only page")
    if authority == "UNKNOWN": reasons.append("unknown source domain")
    verdict = "REJECT" if any(r in reasons for r in ("empty extracted text", "login or error page detected")) else ("PARTIAL" if reasons else "PASS")
    return QualityAssessment(authority, verdict, reasons)
