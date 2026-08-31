from __future__ import annotations

import re
from typing import Any

from .evidence_gate import EvidenceResult
from .query_planner import QueryPlan


def _sentences(text: str) -> list[str]:
    return [part.strip(" \n-•") for part in re.split(r"(?<=[。！？；])|\n+", text) if len(part.strip()) >= 8]


def _unique(items: list[str], limit: int) -> list[str]:
    result = []
    for item in items:
        cleaned = re.sub(r"\s+", " ", item).strip()
        if cleaned and cleaned not in result:
            result.append(cleaned[:240])
        if len(result) == limit:
            break
    return result


class GroundedAnswerPlannerV2:
    """Produces a safe structured response; every displayed fact remains tied to a source."""

    def _confirmed_facts(self, plan: QueryPlan, evidence: EvidenceResult) -> list[dict[str, Any]]:
        query_terms = {char for char in plan.rewritten_query if "\u3400" <= char <= "\u9fff"}
        facts = []
        seen = set()
        for hit in evidence.supporting_hits:
            ranked = sorted(
                [value for value in _sentences(hit.get("text", "")) if not value.lstrip().startswith("#")],
                key=lambda sentence: -len(query_terms & set(sentence)),
            )
            sentence = next((value for value in ranked if len(query_terms & set(value)) >= 2), None)
            key = re.sub(r"[*#\s]+", "", sentence or "")
            if sentence and key not in seen:
                seen.add(key)
                facts.append({
                    "text": sentence[:320], "source_id": hit["source_id"],
                    "title": hit["title"], "url": hit["url"],
                })
            if len(facts) == 5:
                break
        return facts

    @staticmethod
    def _action_plan(evidence: EvidenceResult) -> dict[str, list[str]]:
        sentences = [sentence for hit in evidence.supporting_hits for sentence in _sentences(hit.get("text", ""))]
        conditions = [s for s in sentences if any(k in s for k in ("条件", "资格", "应当", "须符合", "适用于"))]
        materials = [s for s in sentences if any(k in s for k in ("材料", "申请表", "证明", "上传", "提交"))]
        steps = [s for s in sentences if any(k in s for k in ("登录", "申请", "办理", "审核", "审批", "领取"))]
        deadlines = [s for s in sentences if re.search(r"(?:截止|20\d{2}年|\d{1,2}月\d{1,2}日|\d{1,2}[:：]\d{2})", s)]
        entries = []
        for hit in evidence.supporting_hits:
            entries.append(f"{hit['title']}：{hit['url']}")
            entries.extend(re.findall(r"https?://[^\s）)\]，,。]+", hit.get("text", "")))
        return {
            "conditions": _unique(conditions, 4), "materials": _unique(materials, 5),
            "steps": _unique(steps, 6), "deadlines": _unique(deadlines, 4),
            "official_entries": _unique(entries, 5),
        }
    def compose(self, plan: QueryPlan, evidence: EvidenceResult) -> dict[str, Any]:
        citations = []
        for hit in evidence.supporting_hits:
            citation = {"source_id": hit["source_id"], "title": hit["title"], "url": hit["url"]}
            if citation not in citations:
                citations.append(citation)
        facts = self._confirmed_facts(plan, evidence)
        if evidence.status == "NOT_SUPPORTED":
            answer = "我目前还不能从已收录的有效官方证据中确认答案，但不会让你停在这里。请先补充下方关键信息，或按给出的官方方向继续查找。"
        elif evidence.status == "CONFLICT":
            answer = "我发现当前官方来源之间存在冲突，因此不会擅自替你选择版本。下面会列出冲突、需要补充的信息，以及向主管部门确认时应提供的要点。"
        elif evidence.status == "PARTIAL":
            answer = "现有资料可以确认一部分内容；我先给出已确认事实，再通过追问或官方查找路径补齐剩余部分。"
        else:
            answer = "现有已审核资料支持回答。以下事实均可回溯到所列来源。"
        action_plan = self._action_plan(evidence) if plan.wants_action_plan and evidence.status in {"SUPPORTED", "PARTIAL"} else None
        return {
            "answer": answer, "confirmed_facts": facts, "action_plan": action_plan,
            "citations": citations[:8], "conflicts": list(evidence.conflicts),
            "historical_versions": list(evidence.historical_versions),
            "needs_clarification": False, "clarification_questions": [], "search_guidance": [],
        }
