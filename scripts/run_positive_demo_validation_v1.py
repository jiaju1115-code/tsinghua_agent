"""Run positive-path probes through Runtime V1 and emit provenance/traces."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_v1 import RuntimeV1


DATA = ROOT / "experiments/positive_demo_validation_v1/data/positive_demo_question_set_v1.jsonl"
OUT = ROOT / "experiments/positive_demo_validation_v1"


def main() -> None:
    questions = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
    runtime = RuntimeV1()
    rows = []
    for question in questions:
        result = runtime.answer_query(question["query"], request_id=question["demo_id"])
        trace = result["diagnostics"]["orchestrator"]
        answer = result["diagnostics"]["answer_runtime"] or {}
        retrieval = result.get("retrieval") or {}
        evidence = result.get("evidence") or {}
        citation = result.get("citation") or {}
        rows.append({
            **question,
            "retrieval": {"status": trace.get("retrieval_status"), "top5_chunk_ids": retrieval.get("chunk_ids", []), "source_ids": retrieval.get("source_ids", [])},
            "evidence": {"status": trace.get("evidence_status"), "decision": evidence.get("decision"), "reason_codes": evidence.get("reason_codes", []), "required_points": evidence.get("required_points", []), "supporting_chunk_ids": evidence.get("supporting_chunk_ids", [])},
            "citation": {"status": trace.get("citation_status"), "support_status": citation.get("support_status"), "reason_codes": citation.get("reason_codes", []), "support_units": citation.get("support_units", []), "excluded_candidates": citation.get("excluded_candidates", [])},
            "answer": {"status": trace.get("answer_status"), "answer_text": result.get("answer", ""), "model_called": answer.get("diagnostics", {}).get("model_called"), "constraint_version": answer.get("diagnostics", {}).get("answer_generation_constraint"), "reason_codes": answer.get("reason_codes", []), "error": answer.get("error")},
            "final_runtime_status": result.get("status"),
            "latency": {"total_ms": trace.get("total_latency_ms"), "layers_ms": trace.get("layer_latencies_ms")},
        })
    positive = [row for row in rows if row["expected_behavior"] == "SHOULD_ANSWER"]
    full = [row for row in positive if row["evidence"]["decision"] == "SUFFICIENT" and row["citation"]["support_status"] == "READY" and row["answer"]["status"] == "FULL_ANSWER"]
    answered = [row for row in positive if row["answer"]["status"] in {"FULL_ANSWER", "PARTIAL_ANSWER"}]
    unexpected_refusal = [row for row in positive if row["answer"]["status"] == "REFUSAL"]
    infrastructure = [row for row in positive if row["final_runtime_status"] == "RUNTIME_ERROR" or row["answer"]["status"] == "ERROR"]
    summary = {
        "validation_version": "POSITIVE_DEMO_VALIDATION_V1",
        "total_positive_cases": len(positive), "should_answer_count": len(positive), "actual_answer_count": len(answered),
        "full_support_count": len(full), "unexpected_refusal_count": len(unexpected_refusal), "runtime_error_count": len(infrastructure),
        "positive_answer_rate": len(answered) / len(positive) if positive else 0.0,
        "full_support_rate": len(full) / len(positive) if positive else 0.0,
        "citation_presence_rate": sum(bool(row["citation"].get("support_units")) for row in answered) / len(answered) if answered else 0.0,
        "runtime_completion_rate": sum(row["final_runtime_status"] == "COMPLETED" for row in positive) / len(positive) if positive else 0.0,
    "paraphrase_robustness": {"pairs": 3, "answered_pairs": sum(row["answer"]["status"] in {"FULL_ANSWER", "PARTIAL_ANSWER"} for row in positive if row.get("paraphrase_of"))},
    }
    OUT.joinpath("results").mkdir(parents=True, exist_ok=True)
    OUT.joinpath("reports").mkdir(parents=True, exist_ok=True)
    OUT.joinpath("results/positive_demo_results_v1.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    OUT.joinpath("results/positive_demo_summary_v1.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT.joinpath("results/positive_case_provenance_v1.json").write_text(json.dumps([{k: row[k] for k in ("demo_id", "query", "source_case", "source_type", "coverage_evidence", "retrieval", "evidence", "citation", "answer")} for row in rows], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
