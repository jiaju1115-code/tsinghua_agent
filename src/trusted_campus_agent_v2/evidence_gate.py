from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from .metadata import parse_iso_date
from .query_planner import QueryPlan


@dataclass(frozen=True)
class EvidenceResult:
    status: str
    supported_subqueries: tuple[int, ...]
    unsupported_subqueries: tuple[int, ...]
    supporting_hits: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    historical_versions: tuple[dict[str, Any], ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "supported_subqueries": list(self.supported_subqueries),
            "unsupported_subqueries": list(self.unsupported_subqueries),
            "supporting_hits": list(self.supporting_hits),
            "conflicts": list(self.conflicts),
            "historical_versions": list(self.historical_versions),
            "reason_codes": list(self.reason_codes),
        }


class EvidenceGateV2:
    STATUSES = ("SUPPORTED", "PARTIAL", "CONFLICT", "NOT_SUPPORTED")

    def __init__(self, min_score: float = 0.38, max_supporting_hits: int = 5) -> None:
        self.min_score = min_score
        self.max_supporting_hits = max_supporting_hits

    @staticmethod
    def _fact_signature(text: str) -> tuple[str, ...]:
        deadlines = re.findall(r"(?:20\d{2}年)?\d{1,2}月\d{1,2}日(?:\s*\d{1,2}[:：]\d{2})?", text)
        return tuple(sorted(set(deadlines)))

    def _find_conflicts(self, hits: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        historical = []
        historical_ids: set[str] = set()
        for hit in hits:
            meta = hit.get("metadata", {})
            key = meta.get("policy_key")
            if key:
                grouped[key].append(hit)
            if hit.get("temporal_status") == "expired":
                historical.append({"source_id": hit["source_id"], "title": hit["title"], "url": hit["url"]})
                historical_ids.add(hit["source_id"])
        conflicts = []
        for key, rows in grouped.items():
            active = [row for row in rows if row.get("temporal_status") not in {"expired", "upcoming"}]
            source_dates: dict[str, date | None] = {}
            for row in active:
                meta = row.get("metadata", {})
                source_dates[row["source_id"]] = parse_iso_date(meta.get("effective_date")) or parse_iso_date(meta.get("publish_date"))
            dated = [value for value in source_dates.values() if value is not None]
            if len(set(source_dates)) > 1 and len(set(dated)) > 1:
                newest = max(dated)
                superseded = {source_id for source_id, value in source_dates.items() if value is not None and value < newest}
                for row in active:
                    if row["source_id"] in superseded and row["source_id"] not in historical_ids:
                        historical.append({"source_id": row["source_id"], "title": row["title"], "url": row["url"], "reason": "superseded_by_newer_effective_or_published_version"})
                        historical_ids.add(row["source_id"])
                active = [row for row in active if row["source_id"] not in historical_ids]
            signatures = {self._fact_signature(row.get("text", "")) for row in active}
            signatures.discard(())
            if len(signatures) > 1 and len({row["source_id"] for row in active}) > 1:
                conflicts.append({
                    "policy_key": key,
                    "sources": [{"source_id": row["source_id"], "title": row["title"], "url": row["url"]} for row in active],
                    "reason": "multiple currently applicable sources expose different date/deadline facts",
                })
        unique_historical = list({row["source_id"]: row for row in historical}.values())
        return conflicts, unique_historical, historical_ids

    @staticmethod
    def _aspect_supported(subquery: str, texts: list[str]) -> bool:
        joined = "\n".join(texts)
        if any(marker in subquery for marker in ("截止", "什么时候", "时间")):
            deadline = re.search(
                r"(?:截止|截至).{0,40}(?:20\d{2}年)?\d{1,2}月\d{1,2}日"
                r"|(?:20\d{2}年)?\d{1,2}月\d{1,2}日(?:\s*\d{1,2}[:：]\d{2})?"
                r"|\d{1,2}[:：]\d{2}",
                joined,
            )
            if deadline is None:
                return False
        requirements = []
        for markers, evidence_markers in (
            (("条件", "资格", "对象"), ("条件", "资格", "要求", "应当", "适用于", "须符合")),
            (("材料",), ("材料", "申请表", "证明", "附件", "上传", "提交")),
            (("步骤", "流程", "办理"), ("步骤", "流程", "办理", "登录", "申请", "审核", "审批")),
            (("入口", "网址", "系统"), ("入口", "网址", "系统", "http://", "https://")),
        ):
            if any(marker in subquery for marker in markers):
                requirements.append(evidence_markers)
        return all(any(marker in joined for marker in evidence_markers) for evidence_markers in requirements)

    def evaluate(self, plan: QueryPlan, retrieval: dict[str, Any], as_of: date | None = None) -> EvidenceResult:
        del as_of  # Temporal status is attached by the retriever using the same request date.
        eligible = [row for row in retrieval.get("results", []) if row.get("score", 0.0) >= self.min_score]
        eligible = [row for row in eligible if row.get("metadata", {}).get("authority_level") != "unverified"]
        conflicts, historical, historical_ids = self._find_conflicts(eligible)
        support_pool = eligible[: self.max_supporting_hits]
        hits = [row for row in support_pool if row.get("temporal_status") not in {"expired", "upcoming"} and row.get("source_id") not in historical_ids]
        candidate_indices = {index for hit in hits for index in hit.get("subquery_indices", [])}
        supported = []
        for index in sorted(candidate_indices):
            texts = [hit.get("text", "") for hit in hits if index in hit.get("subquery_indices", [])]
            if self._aspect_supported(plan.subqueries[index], texts):
                supported.append(index)
        unsupported = [index for index in range(len(plan.subqueries)) if index not in supported]
        reasons = []
        if conflicts:
            status = "CONFLICT"
            reasons.append("UNRESOLVED_CURRENT_SOURCE_CONFLICT")
        elif not hits:
            status = "NOT_SUPPORTED"
            reasons.append("NO_AUTHORITATIVE_EVIDENCE_ABOVE_THRESHOLD")
        elif unsupported or retrieval.get("degraded"):
            status = "PARTIAL"
            if unsupported:
                reasons.append("SUBQUERY_COVERAGE_INCOMPLETE")
            if retrieval.get("degraded"):
                reasons.append("RETRIEVAL_DEGRADED")
        else:
            status = "SUPPORTED"
            reasons.append("ALL_SUBQUERIES_AUTHORITATIVELY_SUPPORTED")
        if historical:
            reasons.append("HISTORICAL_VERSION_PRESENT")
        return EvidenceResult(
            status=status,
            supported_subqueries=tuple(supported), unsupported_subqueries=tuple(unsupported),
            supporting_hits=tuple(hits), conflicts=tuple(conflicts), historical_versions=tuple(historical),
            reason_codes=tuple(sorted(reasons)),
        )
