from __future__ import annotations

import re
from typing import Any

from .evidence_gate import EvidenceResult
from .query_planner import QueryPlan


def _sentences(text: str) -> list[str]:
    text = re.sub(r"(?<![。！？；：])\n(?=[\u3400-\u9fffA-Za-z0-9])", "", text)
    text = re.sub(r"(?<!^)(?=(?:学生证|校园卡).{0,10}(?:挂失|补办|解挂)[：:])", "\n", text)
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
        from .retrieval import tokenize

        query_terms = set(tokenize(plan.rewritten_query))
        facts = []
        seen = set()
        for hit in evidence.supporting_hits:
            candidates = [value for value in _sentences(hit.get("text", "")) if not value.lstrip().startswith("#")]
            canonical_candidates = [
                value for value in candidates
                if not plan.canonical_terms or any(term in value for term in plan.canonical_terms if term != "校园卡补办")
            ]
            if canonical_candidates:
                candidates = canonical_candidates
            ranked = sorted(
                candidates,
                key=lambda sentence: (
                    -len(query_terms & set(tokenize(sentence))) / max(1, len(set(tokenize(sentence))) ** 0.5),
                    len(sentence),
                ),
            )
            sentence = ranked[0] if ranked and query_terms & set(tokenize(ranked[0])) else None
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
    def _action_plan(plan: QueryPlan, evidence: EvidenceResult) -> dict[str, list[str]]:
        sentences = [sentence for hit in evidence.supporting_hits for sentence in _sentences(hit.get("text", ""))]
        subject_terms = [term for term in plan.canonical_terms if term not in {"校园卡补办"}]
        if "校园卡" in subject_terms:
            subject_terms.extend(("学生证", "卡补办", "卡挂失", "卡解挂"))
            relevant = [
                sentence for sentence in sentences
                if any(term in sentence for term in subject_terms)
                and any(action in sentence for action in ("挂失", "补办", "解挂", "充值", "新卡"))
            ]
        else:
            relevant = [sentence for sentence in sentences if any(term in sentence for term in subject_terms)] if subject_terms else sentences
        if relevant:
            sentences = relevant
        conditions = [s for s in sentences if any(k in s for k in ("条件", "资格", "应当", "须符合", "适用于"))]
        materials = [s for s in sentences if any(k in s for k in ("材料", "申请表", "证明", "上传", "提交"))]
        steps = [s for s in sentences if any(k in s for k in ("登录", "申请", "办理", "审核", "审批", "领取", "挂失", "补办", "解挂", "自助机"))]
        deadlines = [s for s in sentences if re.search(r"(?:截止|截至|\d{1,2}月\d{1,2}日|\d{1,2}[:：]\d{2})", s)]
        entries = []
        for hit in evidence.supporting_hits:
            entries.append(f"{hit['title']}：{hit['url']}")
        for sentence in sentences:
            entries.extend(re.findall(r"https?://[^\s）)\]，,。]+", sentence))
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
            if plan.wants_action_plan:
                answer = (
                    "现有证据还不足以把这项事务的办理条件、材料或当前批次安排说准，"
                    "我不会把其他人群或旧批次的流程套给你。请先补充下方关键信息；"
                    "也可以直接通过“官方查找渠道”进入信息门户或主管部门页面，搜索事项名称并核对最新通知、附件和联系人。"
                )
            else:
                answer = (
                    "现有有效官方证据还不足以确认这个问题，我先不猜。"
                    "请补充下方关键信息，或通过“官方查找渠道”核对主管部门的最新说明。"
                )
        elif evidence.status == "CONFLICT":
            answer = "我发现当前官方来源之间存在冲突，因此不会擅自替你选择版本。下面会列出冲突、需要补充的信息，以及向主管部门确认时应提供的要点。"
        elif evidence.status == "PARTIAL":
            answer = f"目前能确认的是：{facts[0]['text']} 其余部分我还没有找到足够可靠的现行依据，建议按下方渠道核对当前批次。" if facts else "目前只能确认一部分信息；缺少可靠依据的部分我不会替你猜，建议按下方渠道核对当前批次。"
        else:
            answer = f"先说结论：{facts[0]['text']}" if facts else "目前没有提取到可直接说明结论的事实，请结合下方官方来源继续核对。"
        action_plan = self._action_plan(plan, evidence) if plan.wants_action_plan and evidence.status in {"SUPPORTED", "PARTIAL"} else None
        return {
            "answer": answer, "confirmed_facts": facts, "action_plan": action_plan,
            "citations": citations[:8], "conflicts": list(evidence.conflicts),
            "historical_versions": list(evidence.historical_versions),
            "needs_clarification": False, "clarification_questions": [], "search_guidance": [],
        }
