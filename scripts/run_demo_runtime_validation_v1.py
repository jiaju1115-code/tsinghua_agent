"""Run bounded Demo-facing validation through the public Runtime V1 API."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_v1 import RuntimeV1
from src.runtime_v1.demo_cli import format_demo_result


QUESTION_SET = ROOT / "experiments/demo_runtime_validation_v1/data/demo_question_set_v1.jsonl"
OUT = ROOT / "experiments/demo_runtime_validation_v1"


def load_questions() -> list[dict]:
    return [json.loads(line) for line in QUESTION_SET.read_text(encoding="utf-8").splitlines() if line.strip()]


def expected_match(expected: str, answer_status: str) -> bool:
    actual = {"FULL_ANSWER": "SHOULD_ANSWER", "PARTIAL_ANSWER": "SHOULD_PARTIAL", "REFUSAL": "SHOULD_REFUSE"}.get(answer_status)
    return actual == expected


def classify_failure(row: dict) -> str | None:
    if row["status"] == "RUNTIME_ERROR":
        return "RUNTIME_ERROR"
    if not row["expected_behavior_match"]:
        return "EXPECTED_BEHAVIOR_MISMATCH"
    answer = row["answer"]
    if row["answer_status"] in {"FULL_ANSWER", "PARTIAL_ANSWER"} and not row["citation_presence"]:
        return "CITATION_INCOMPLETE"
    if len(answer) > 900:
        return "ANSWER_TOO_VERBOSE"
    if "Traceback" in answer or "Exception" in answer:
        return "ANSWER_UNSUPPORTED"
    return None


def main() -> None:
    questions = load_questions()
    runtime = RuntimeV1()
    rows = []
    for question in questions:
        result = runtime.answer_query(question["query"], request_id=question["demo_id"])
        orchestration = result.get("diagnostics", {}).get("orchestrator", {}) or {}
        answer_runtime = result.get("diagnostics", {}).get("answer_runtime", {}) or {}
        answer_status = answer_runtime.get("answer_status", "ERROR")
        citation = result.get("citation") or {}
        sources = result.get("retrieval") or {}
        citation_presence = bool(citation.get("usable_source_ids")) if answer_status in {"FULL_ANSWER", "PARTIAL_ANSWER"} else None
        presentation = format_demo_result(result)
        row = {
            "demo_id": question["demo_id"],
            "query": question["query"],
            "category": question["category"],
            "scenario": question["scenario"],
            "expected_behavior": question["expected_behavior"],
            "status": result.get("status"),
            "retrieval_status": orchestration.get("retrieval_status"),
            "evidence_status": orchestration.get("evidence_status"),
            "citation_status": orchestration.get("citation_status"),
            "answer_status": answer_status,
            "answer": result.get("answer", ""),
            "citation_presence": citation_presence,
            "expected_behavior_match": expected_match(question["expected_behavior"], answer_status),
            "refusal": result.get("refusal", {}),
            "latency_ms": orchestration.get("total_latency_ms"),
            "layer_latencies_ms": orchestration.get("layer_latencies_ms"),
            "presentation": {"line_count": len(presentation.splitlines()), "contains_traceback": "Traceback" in presentation},
            "source_count": len(sources.get("source_ids", [])),
        }
        row["demo_ready"] = "YES" if result.get("status") == "COMPLETED" and answer_status != "ERROR" else "NO"
        row["answer_useful"] = "YES" if answer_status == "FULL_ANSWER" else "PARTIAL" if answer_status == "PARTIAL_ANSWER" else "NO"
        row["citation_clear"] = "YES" if citation_presence else "N/A" if answer_status == "REFUSAL" else "NO"
        row["behavior_safe"] = "YES" if answer_status == "REFUSAL" or row["expected_behavior_match"] else "NO"
        row["presentation_issue"] = "TOO_LONG" if len(row["answer"]) > 900 else "OTHER" if row["presentation"]["contains_traceback"] else "NONE"
        row["failure_type"] = classify_failure(row)
        rows.append(row)
    counts = Counter(row["scenario"] for row in questions)
    failures = Counter(row["failure_type"] for row in rows if row["failure_type"])
    completed = sum(row["status"] == "COMPLETED" for row in rows)
    matches = sum(row["expected_behavior_match"] for row in rows)
    latencies = [row["latency_ms"] for row in rows if isinstance(row["latency_ms"], (int, float))]
    summary = {
        "validation_version": "DEMO_RUNTIME_VALIDATION_V1",
        "total_questions": len(rows),
        "scenario_counts": dict(counts),
        "runtime_completion_rate": completed / len(rows) if rows else 0.0,
        "expected_behavior_match_rate": matches / len(rows) if rows else 0.0,
        "citation_presence_rate_answered": sum(row["citation_presence"] is True for row in rows) / max(1, sum(row["citation_presence"] is not None for row in rows)),
        "refusal_count": sum(row["answer_status"] == "REFUSAL" for row in rows),
        "latency_ms": {"min": min(latencies) if latencies else None, "median": sorted(latencies)[len(latencies) // 2] if latencies else None, "max": max(latencies) if latencies else None},
        "failure_counts": dict(failures),
    }
    readiness = "DEMO_READY" if not failures and summary["expected_behavior_match_rate"] == 1.0 else "DEMO_READY_WITH_LIMITATIONS" if completed == len(rows) and not any(row["failure_type"] == "RUNTIME_ERROR" for row in rows) else "DEMO_BLOCKED"
    failure_inventory = {"validation_version": summary["validation_version"], "failures": [row for row in rows if row["failure_type"]]}
    readiness_summary = {"readiness": readiness, "reason": "bounded natural-language validation through Runtime V1", "summary": summary}
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    (OUT / "results/demo_runtime_results_v1.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    (OUT / "results/demo_failure_inventory_v1.json").write_text(json.dumps(failure_inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "results/demo_readiness_summary_v1.json").write_text(json.dumps(readiness_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(readiness_summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
