"""Capture the real Runtime V1 partial-support path for the three failing probes."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.answer_generation_v1.model_adapter import default_adapter
from src.runtime_v1 import RuntimeV1


class RecordingAdapter:
    def __init__(self) -> None:
        self.inner = default_adapter()
        self.calls: list[dict] = []

    def generate(self, messages, timeout_seconds):
        result = self.inner.generate(messages, timeout_seconds)
        self.calls.append({
            "messages": copy.deepcopy(messages),
            "envelope": copy.deepcopy(result),
        })
        return result


def main() -> None:
    data = ROOT / "experiments/positive_demo_validation_v1/data/positive_demo_question_set_v1.jsonl"
    wanted = {"POS002", "POS006", "POS008"}
    questions = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines() if line.strip()]
    adapter = RecordingAdapter()
    runtime = RuntimeV1(model_adapter=adapter)
    rows = []
    for question in questions:
        if question["demo_id"] not in wanted:
            continue
        before = len(adapter.calls)
        result = runtime.answer_query(question["query"], request_id=question["demo_id"])
        after = len(adapter.calls)
        answer = result["diagnostics"].get("answer_runtime") or {}
        trace = result["diagnostics"].get("orchestrator") or {}
        call = adapter.calls[before:after]
        rows.append({
            "case_id": question["demo_id"],
            "query": question["query"],
            "retrieval_status": (result.get("retrieval") or {}).get("status"),
            "evidence_status": (result.get("evidence") or {}).get("decision"),
            "citation_status": (result.get("citation") or {}).get("status"),
            "answer_invoked": bool(call),
            "model_called": answer.get("diagnostics", {}).get("model_called"),
            "raw_model_output": call[0]["envelope"].get("content") if call else None,
            "raw_output_sha256": call[0]["envelope"].get("raw_output_sha256") if call else None,
            "parser_result": {
                "answer_status": answer.get("answer_status"),
                "claim_record_count": len(answer.get("claim_records", [])),
            },
            "validation_result": {
                "reason_codes": answer.get("reason_codes", []),
                "error": answer.get("error"),
            },
            "runtime_final_status": result.get("status"),
            "runtime_diagnostics": {
                "orchestrator_status": trace.get("orchestrator_status"),
                "answer_status": trace.get("answer_status"),
                "error": trace.get("error"),
            },
        })
    out = ROOT / "experiments/answer_v1_partial_contract_fix/audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "answer_v1_partial_contract_runtime_trace_v1.json").write_text(
        json.dumps({"version": "ANSWER_V1_PARTIAL_CONTRACT_RUNTIME_TRACE_V1", "cases": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"cases": len(rows), "model_calls": len(adapter.calls)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
