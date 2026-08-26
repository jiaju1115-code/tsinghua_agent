"""Run the bounded Runtime V1 smoke/equivalence check (two historical cases)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_v1 import RuntimeV1


CASES = ROOT / "evaluation" / "e2e_heldout" / "v1" / "cases" / "e2e_50_cases.jsonl"
BASELINE = ROOT / "evaluation" / "e2e_heldout" / "v1" / "results" / "e2e_50_results.jsonl"
OUTPUT = ROOT / "experiments" / "runtime_v1_integration" / "results" / "runtime_v1_smoke_equivalence.json"


def rows(path: Path, count: int) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()][:count]


def main() -> None:
    cases = rows(CASES, 2)
    expected = {row["case_id"]: row for row in rows(BASELINE, 2)}
    runtime = RuntimeV1()
    results = []
    for case in cases:
        actual = runtime.answer_query(case["query"], request_id=case["case_id"])
        baseline = expected[case["case_id"]]
        checks = {
            "retriever_top5_present": len(actual["retrieval"]["ordered_top5_chunks"]) == 5,
            "evidence_decision_equal": actual["evidence"]["decision"] == baseline["evidence_status"],
            "citation_status_equal": actual["citation"]["support_status"] == baseline["citation_status"],
            "answer_status_equal": actual["diagnostics"]["orchestrator"]["answer_status"] == baseline["answer_status"],
            "answer_text_equal": actual["answer"] == baseline["final_answer"],
            "refusal_policy_preserved": actual["refusal"]["refused"] is True and "SUPPORT_BLOCKED" in actual["refusal"]["reason_codes"],
        }
        results.append({"case_id": case["case_id"], "checks": checks, "passed": all(checks.values())})
    payload = {
        "runtime_version": "RUNTIME_V1",
        "freeze": "FROZEN_BUNDLE_V1.1",
        "case_count": len(results),
        "all_passed": all(row["passed"] for row in results),
        "results": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    if not payload["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
