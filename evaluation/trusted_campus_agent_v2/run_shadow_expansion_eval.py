"""Focused retrieval/evidence smoke evaluation for the unpublished V2 expansion."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2.evidence_gate import EvidenceGateV2
from src.trusted_campus_agent_v2.query_planner import CampusQueryPlanner
from src.trusted_campus_agent_v2.retrieval import build_shadow_retriever_v2


CASES = (
    ("2026届毕业生就业手续要怎么在线办理，需要哪些材料？", r"2026届毕业生就业手续|毕业生在线手续办理"),
    ("目前实验室安全准入要完成哪些培训和考试？", r"实验室安全准入实施细则"),
    ("学生申请调整宿舍的材料和办理步骤是什么？", r"宿舍调整申请及办理流程"),
    ("校级本科交换生项目申请条件、材料和流程是什么？", r"校级.*交换|交换生项目"),
    ("研究生转专业需要哪些条件和审批？", r"研究生学籍管理规定"),
)


def main() -> None:
    planner = CampusQueryPlanner()
    retriever = build_shadow_retriever_v2()
    gate = EvidenceGateV2()
    rows = []
    for query, expected in CASES:
        plan = planner.plan(query)
        result = retriever.retrieve(plan, top_k=5, as_of=date(2026, 8, 30))
        evidence = gate.evaluate(plan, result, as_of=date(2026, 8, 30))
        titles = [row["title"] for row in result["results"]]
        rows.append({
            "query": query, "path": plan.path, "expected_title_pattern": expected,
            "hit_at_5": any(re.search(expected, title) for title in titles),
            "evidence_status": evidence.status, "titles": titles,
            "latency_ms": result["latency_ms"], "dense_enabled": result["dense_enabled"],
        })
    payload = {
        "version": "TRUSTED_CAMPUS_V2_SHADOW_EXPANSION_EVAL_V1",
        "case_count": len(rows), "hit_at_5": sum(row["hit_at_5"] for row in rows) / len(rows),
        "supported_or_partial_rate": sum(row["evidence_status"] in {"SUPPORTED", "PARTIAL", "CONFLICT"} for row in rows) / len(rows),
        "rows": rows,
    }
    output = Path(__file__).with_name("shadow_expansion_eval.json")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
