from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.semantic_retrieval_v1_1.candidate import QueryUnderstandingV1_1


class ResponseMode(StrEnum):
    FULL_ANSWER = "FULL_ANSWER"
    PARTIAL_ANSWER = "PARTIAL_ANSWER"
    UNCERTAIN_WITH_GUIDANCE = "UNCERTAIN_WITH_GUIDANCE"
    CLARIFYING_RESPONSE = "CLARIFYING_RESPONSE"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    SAFETY_REFUSAL = "SAFETY_REFUSAL"


_CAMPUS_MARKERS = ("清华", "校园", "院系", "宿舍", "校历", "图书馆", "教务")
_GENERAL_MARKERS = ("学习", "写作", "翻译", "润色", "头脑风暴", "焦虑", "难过", "怎么安排", "英语")
_AMBIGUOUS = ("奖学金", "截止", "报到", "申请", "选课")
_SAFETY_MARKERS = ("制作炸弹", "自杀方法", "杀人", "绕过安保")


def _is_campus_query(query: str) -> bool:
    # V1.1 expands only the routing boundary.  It does not supply facts or alter
    # the frozen retriever/Evidence/Citation chain that follows this decision.
    return any(marker in query for marker in _CAMPUS_MARKERS) or QueryUnderstandingV1_1.resolve(query).route == "CAMPUS_RAG"


def _general_answer(query: str) -> str:
    if "学习" in query or "复习" in query:
        return "可以先把目标拆成今天能完成的一小步：选一个主题，做 25 分钟专注练习，再用 5 分钟记录卡点。你愿意的话，把科目和截止时间告诉我，我可以一起排一个更具体的计划。"
    if "写" in query or "润色" in query or "翻译" in query:
        return "可以。把原文、用途和希望的语气发给我；我可以先给出一个可直接使用的版本，再说明关键修改。"
    if "焦虑" in query or "难过" in query:
        return "听起来这件事让你很不好受。先不用急着一次解决所有问题；如果你愿意，可以说说现在最让你卡住的是哪一部分，我们从一个小步骤开始。"
    return f"可以一起想想。关于“{query.strip()}”，你更希望得到思路、一个具体方案，还是帮你整理成文字？"


def _supported(package: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mappings = package.get("required_point_support", []) if isinstance(package, dict) else []
    units = {row.get("support_unit_id"): row for row in package.get("support_units", []) if isinstance(row, dict)}
    known, unknown = [], []
    for point in mappings:
        if not isinstance(point, dict):
            continue
        ids = point.get("support_unit_ids", [])
        row = units.get(ids[0]) if ids else None
        if point.get("mapping_status") in {"SUPPORTED", "PARTIALLY_SUPPORTED"} and row and row.get("span_text"):
            known.append({"point": point.get("point_text", "该部分"), "text": row["span_text"].strip(), "unit_id": row["support_unit_id"], "source_id": row.get("source_id")})
        else:
            unknown.append({"point": point.get("point_text", "该部分")})
    return known, unknown


def _clarification(query: str, context: list[str]) -> str | None:
    if any(marker in query for marker in _AMBIGUOUS) and not _is_campus_query(query) and not _is_campus_query(" ".join(context)):
        if "奖学金" in query:
            return "你说的是本科生还是研究生的奖学金？"
        if "截止" in query:
            return "你想确认的是哪一项申请或办理事项的截止时间？"
        if "报到" in query:
            return "你想问的是哪个院系或哪个入学项目的报到安排？"
        if "选课" in query:
            return "你想问的是哪一类课程或哪个学期的选课？"
    return None


def plan_response(query: str, support_package: dict[str, Any] | None = None, *, conversation: list[str] | None = None) -> dict[str, Any]:
    """Map immutable evidence output to a user-facing response without creating facts.

    Factual text is copied only from support units.  General conversation never enters
    the campus evidence path; callers may still route mixed questions through evidence.
    """
    query = query.strip()
    context = conversation or []
    if any(marker in query for marker in _SAFETY_MARKERS):
        return {"response_mode": ResponseMode.SAFETY_REFUSAL, "answer_text": "我不能协助会造成伤害的做法。如果你正处在紧急危险中，请立即联系当地紧急服务或身边可信的人。", "supported_facts": [], "unsupported_points": [], "citations": []}
    clarification = _clarification(query, context)
    if clarification:
        return {"response_mode": ResponseMode.CLARIFYING_RESPONSE, "answer_text": clarification, "supported_facts": [], "unsupported_points": [], "citations": []}
    campus = _is_campus_query(query)
    if not campus:
        return {"response_mode": ResponseMode.GENERAL_CONVERSATION, "answer_text": _general_answer(query), "supported_facts": [], "unsupported_points": [], "citations": []}

    package = support_package or {}
    known, unknown = _supported(package)
    citations = [{"support_unit_id": item["unit_id"], "source_id": item["source_id"]} for item in known]
    status = package.get("support_status")
    if status == "READY" and known and not unknown:
        return {"response_mode": ResponseMode.FULL_ANSWER, "answer_text": "".join(item["text"] for item in known), "supported_facts": known, "unsupported_points": [], "citations": citations}
    if known:
        missing = "、".join(str(item["point"]) for item in unknown) or "其余细节"
        text = "目前能确认的是：" + "；".join(item["text"] for item in known) + f"。至于{missing}，现有材料没有明确说明，我不想直接猜；建议核对当年的官方通知或相关指南。"
        return {"response_mode": ResponseMode.PARTIAL_ANSWER, "answer_text": text, "supported_facts": known, "unsupported_points": unknown, "citations": citations}
    missing = "、".join(str(item["point"]) for item in unknown) or "关键安排"
    text = f"关于“{query}”，我目前没有查到足够可靠的校园资料，尤其缺少{missing}，所以不想直接给你猜答案。若你问的是当年的具体安排，建议优先核对最新官方通知；你也可以补充院系或项目，我可以继续帮你缩小范围。"
    return {"response_mode": ResponseMode.UNCERTAIN_WITH_GUIDANCE, "answer_text": text, "supported_facts": [], "unsupported_points": unknown, "citations": []}


@dataclass
class NaturalResponseSession:
    """Small conversation-state seam; it prevents re-asking already supplied details."""

    turns: list[str] = field(default_factory=list)

    def preview(self, query: str, support_package: dict[str, Any] | None = None) -> dict[str, Any]:
        return plan_response(query, support_package, conversation=self.turns)

    def respond(self, query: str, support_package: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.preview(query, support_package)
        self.turns.append(query)
        return result
