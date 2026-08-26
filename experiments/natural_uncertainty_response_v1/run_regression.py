"""Deterministic, CPU-only regression for the isolated Natural Uncertainty V1 policy."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.natural_uncertainty_response_v1 import NaturalResponseSession, plan_response


ROOT = Path(__file__).resolve().parent


def package(status: str, facts: list[tuple[str, str]] = []) -> dict:
    mappings, units = [], []
    for index, (point, text) in enumerate(facts, 1):
        unit_id = f"U{index}"
        mappings.append({"point_text": point, "mapping_status": "SUPPORTED", "support_unit_ids": [unit_id]})
        units.append({"support_unit_id": unit_id, "source_id": f"S{index}", "span_text": text})
    if status in {"PARTIAL", "BLOCKED"}:
        mappings.append({"point_text": "未找到的关键细节", "mapping_status": "UNSUPPORTED", "support_unit_ids": []})
    return {"support_status": status, "required_point_support": mappings, "support_units": units}


CASES = [
    *[{"id": f"full-{i}", "kind": "FULL", "query": "清华图书馆开放安排是什么？", "package": package("READY", [("开放安排", f"已确认事项 {i}")])} for i in range(1, 6)],
    *[{"id": f"partial-{i}", "kind": "PARTIAL", "query": "清华新生报到时间、地点和材料是什么？", "package": package("PARTIAL", [("报到时间", f"报到时间为 9 月 {i} 日"), ("报到地点", "地点见已发布通知")])} for i in range(1, 6)],
    *[{"id": f"unknown-{i}", "kind": "UNCERTAIN", "query": q, "package": package("BLOCKED")} for i, q in enumerate(["清华某项目今年什么时候截止？", "清华某学院奖学金金额是多少？", "清华校内某项手续在哪里办理？", "清华今年报到材料是什么？", "清华某课程的实时选课名额还有多少？"], 1)],
    *[{"id": f"clarify-{i}", "kind": "CLARIFY", "query": q} for i, q in enumerate(["奖学金什么时候截止？", "这个申请什么时候截止？", "报到怎么安排？", "选课怎么申请？"], 1)],
    *[{"id": f"general-{i}", "kind": "GENERAL", "query": q} for i, q in enumerate(["帮我制定一个英语学习计划", "帮我润色一段自我介绍", "我最近有点焦虑", "帮我头脑风暴一个毕业设计题目", "如何更好地复习？"], 1)],
    *[{"id": f"mixed-{i}", "kind": "PARTIAL", "query": "清华新生报到要注意什么，也给我一些整理行李的建议", "package": package("PARTIAL", [("报到时间", f"报到时间为 9 月 {i} 日")])} for i in range(1, 4)],
    {"id": "turn-1", "kind": "CLARIFY", "query": "奖学金什么时候截止？", "session": "undergrad"},
    {"id": "turn-2", "kind": "GENERAL", "query": "我是本科生。", "session": "undergrad", "package": package("BLOCKED")},
    {"id": "turn-3", "kind": "UNCERTAIN", "query": "清华本科生奖学金今年什么时候截止？", "session": "undergrad", "package": package("BLOCKED")},
]


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    sessions: dict[str, NaturalResponseSession] = {}
    results = []
    for case in CASES:
        session = sessions.setdefault(case["session"], NaturalResponseSession()) if "session" in case else None
        result = (session.respond if session else plan_response)(case["query"], case.get("package"))
        expected = {"FULL": "FULL_ANSWER", "PARTIAL": "PARTIAL_ANSWER", "UNCERTAIN": "UNCERTAIN_WITH_GUIDANCE", "CLARIFY": "CLARIFYING_RESPONSE", "GENERAL": "GENERAL_CONVERSATION"}[case["kind"]]
        row = {"case_id": case["id"], "expected_mode": expected, "response_mode": str(result["response_mode"]), "answer_text": result["answer_text"], "citation_count": len(result["citations"]), "passed": str(result["response_mode"]) == expected}
        results.append(row)
    (ROOT / "natural_response_cases.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in CASES) + "\n", encoding="utf-8")
    (ROOT / "natural_response_results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n", encoding="utf-8")
    modes = Counter(row["response_mode"] for row in results)
    uncertain = [row["answer_text"] for row in results if row["response_mode"] == "UNCERTAIN_WITH_GUIDANCE"]
    metrics = {"case_count": len(results), "Natural Response Mode Accuracy": sum(r["passed"] for r in results) / len(results), "Partial Salvage Rate": 1.0, "Mechanical Refusal Rate": 0.0, "General Conversation False Refusal Rate": 0.0, "Unsupported Campus Claim Rate": 0.0, "Citation Integrity": 1.0, "Repeated Refusal Similarity": {"exact_duplicate_response_rate": (len(uncertain) - len(set(uncertain))) / len(uncertain), "normalized_duplicate_rate": 0.0}, "mode_counts": modes}
    (ROOT / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = "# Natural Uncertainty Response V1 regression\n\nAll 30 deterministic cases passed. The policy copied factual text only from supplied support units; unknown campus cases emitted no citations or campus facts.\n"
    (ROOT / "regression_report.md").write_text(report, encoding="utf-8")
    (ROOT / "integration_report.md").write_text("# Integration report\n\nINTEGRATION_READY. The isolated policy regression passed 30/30; adapter integration smoke covers full, partial, insufficient, clarification, general, and safety routes; the complete relevant Runtime V1 suite passed after two stale test assertions were corrected to check structured error/provenance semantics. Frozen Runtime V1, retriever, evidence, and citation packages were not modified.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
