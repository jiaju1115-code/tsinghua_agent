"""Bounded three-case Runtime V1 validation after Prompt Freeze V1.1 wiring."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_v1 import RuntimeV1


OUTPUT = ROOT / "experiments" / "runtime_v1_integration" / "results" / "runtime_v1_prompt_v1_1_integration_results.json"
CASES = [
    ("supported_ready_oriented", "清华大学在奖学金评选当年如何表彰获奖者？"),
    ("partial", "清华大学在奖学金评选当年如何表彰获奖者？"),
    ("refusal", "访客进入清华校园前，通常需要准备或核实哪些预约信息？"),
]


def main() -> None:
    runtime = RuntimeV1()
    results = []
    for name, query in CASES:
        result = runtime.answer_query(query, request_id=f"prompt-v1-1-{name}")
        trace = result["diagnostics"]["orchestrator"]
        answer = result["diagnostics"]["answer_runtime"] or {}
        results.append({
            "case": name,
            "status": result["status"],
            "retrieval_status": trace["retrieval_status"],
            "evidence_status": trace["evidence_status"],
            "citation_status": trace["citation_status"],
            "answer_status": trace["answer_status"],
            "answer_error": answer.get("error"),
            "model_called": answer.get("diagnostics", {}).get("model_called"),
            "prompt_freeze": result["diagnostics"]["answer_prompt_freeze"],
            "refused": result["refusal"]["refused"],
        })
    payload = {"runtime_version": "RUNTIME_V1", "answer_prompt_freeze_version": "ANSWER_V1_PROMPT_FREEZE_V1.1", "results": results}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    if any(row["answer_error"] and "raw hash" in row["answer_error"] for row in results):
        raise SystemExit("legacy raw-hash false mismatch remains")


if __name__ == "__main__":
    main()
