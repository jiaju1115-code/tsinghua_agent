from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALIASES = ROOT / "configs" / "trusted_campus_agent_v2" / "campus_aliases.json"

SCENARIO_TERMS: dict[str, tuple[str, ...]] = {
    "教务": ("选课", "课程", "成绩", "学分", "学籍", "转系", "转专业", "辅修", "双学位", "考试", "免修"),
    "学生事务": ("奖学金", "助学金", "资助", "处分", "社团", "户口", "证明", "学生事务"),
    "校园生活": ("宿舍", "住宿", "食堂", "餐饮", "校车", "交通", "医院", "医疗", "网络", "图书馆", "体育", "校园卡", "一卡通", "校园码"),
    "科研实践": ("科研", "基金", "项目", "实验室", "创新", "实践", "竞赛", "申报"),
    "国际交流": ("交换", "留学", "国际", "签证", "出国", "境外", "联合培养"),
    "就业": ("就业", "求职", "招聘", "三方", "派遣", "档案", "职业", "实习"),
    "新生": ("新生", "入学", "报到", "迎新", "军训", "入校"),
    "毕业": ("毕业", "离校", "学位", "毕业证", "成绩单", "校友", "答辩"),
}

COMPLEX_MARKERS = (
    "怎么办", "如何办理", "申请流程", "需要什么材料", "哪些材料", "截止", "条件是什么",
    "分别", "比较", "冲突", "最新规定", "是否还", "先后", "同时", "以及", "并且", "补办", "挂失",
)
PROCEDURE_MARKERS = ("办理", "申请", "转系", "转专业", "交换", "奖学金", "助学金", "报到", "毕业", "离校", "补办", "挂失", "校园卡")


@dataclass(frozen=True)
class QueryPlan:
    original_query: str
    rewritten_query: str
    subqueries: tuple[str, ...]
    path: str
    complexity_reasons: tuple[str, ...]
    metadata_filters: dict[str, Any]
    canonical_terms: tuple[str, ...]
    wants_action_plan: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["subqueries"] = list(self.subqueries)
        value["complexity_reasons"] = list(self.complexity_reasons)
        value["canonical_terms"] = list(self.canonical_terms)
        return value


class CampusQueryPlanner:
    """Deterministic first-stage planner; an LLM rewrite can be added behind this contract later."""

    def __init__(self, aliases_path: Path | str = DEFAULT_ALIASES) -> None:
        payload = json.loads(Path(aliases_path).read_text(encoding="utf-8"))
        self.aliases: dict[str, list[str]] = payload["aliases"]
        self.alias_to_canonical = {
            alias.lower(): canonical
            for canonical, aliases in self.aliases.items()
            for alias in {canonical, *aliases}
        }

    def _canonical_terms(self, query: str) -> list[str]:
        lowered = query.lower()
        matches = {
            canonical
            for alias, canonical in self.alias_to_canonical.items()
            if alias and alias in lowered
        }
        return sorted(matches)

    @staticmethod
    def _topics(query: str) -> list[str]:
        return [topic for topic, terms in SCENARIO_TERMS.items() if any(term in query for term in terms)]

    @staticmethod
    def _split_explicit_clauses(query: str) -> list[str]:
        clauses = [part.strip(" ？?，,。") for part in re.split(r"[；;]|以及|并且|同时|另外", query)]
        return [part for part in clauses if len(part) >= 3]

    def plan(self, query: str, path_override: str | None = None) -> QueryPlan:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        query = re.sub(r"\s+", " ", query.strip())
        canonical = self._canonical_terms(query)
        rewritten = query
        additions = [term for term in canonical if term not in query]
        if additions:
            rewritten = f"{query}（校园规范术语：{'、'.join(additions)}）"

        reasons: list[str] = []
        matched_markers = [marker for marker in COMPLEX_MARKERS if marker in query]
        if matched_markers:
            reasons.append("complex_intent_marker")
        if len(self._topics(query)) > 1:
            reasons.append("cross_topic")
        if len(query) > 45:
            reasons.append("long_query")
        wants_action = any(marker in query for marker in PROCEDURE_MARKERS)
        if wants_action and any(marker in query for marker in ("如何", "怎么", "流程", "材料", "条件", "截止", "申请", "办理")):
            reasons.append("actionable_procedure")

        requested_path = path_override.upper() if path_override else None
        if requested_path not in {None, "FAST", "FULL"}:
            raise ValueError("path_override must be FAST, FULL, or None")
        path = requested_path or ("FULL" if reasons else "FAST")
        if requested_path:
            reasons.append(f"user_selected_{requested_path.lower()}")
        clauses = self._split_explicit_clauses(query) if path == "FULL" else [rewritten]
        if path == "FULL" and wants_action and len(clauses) == 1:
            subject = canonical[0] if canonical else query
            clauses = [
                f"{subject}的申请条件和适用对象",
                f"{subject}需要的材料和办理步骤",
                f"{subject}的截止时间和官方入口",
            ]
        subqueries = tuple(dict.fromkeys(clauses[:4])) or (rewritten,)
        topics = self._topics(query)
        filters: dict[str, Any] = {
            "topics": topics,
            "current_only": any(term in query for term in ("现在", "目前", "最新", "今年", "还有效", "截止", "截止日期")),
        }
        audience = []
        for marker, value in (("本科", "本科生"), ("研究生", "研究生"), ("博士", "博士生"), ("国际学生", "国际学生"), ("新生", "新生"), ("毕业生", "毕业生")):
            if marker in query:
                audience.append(value)
        if audience:
            filters["audience"] = audience
        return QueryPlan(
            original_query=query,
            rewritten_query=rewritten,
            subqueries=subqueries,
            path=path,
            complexity_reasons=tuple(sorted(set(reasons))),
            metadata_filters=filters,
            canonical_terms=tuple(canonical),
            wants_action_plan=wants_action,
        )
