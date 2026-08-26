from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.runtime_v1 import RuntimeV1


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "evaluation" / "e2e_heldout" / "v1" / "cases" / "e2e_50_cases.jsonl"
HISTORICAL = ROOT / "evaluation" / "e2e_heldout" / "v1" / "results" / "e2e_50_results.jsonl"


def _first_rows(path: Path, count: int) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()][:count]


@pytest.fixture(scope="module")
def runtime() -> RuntimeV1:
    return RuntimeV1()


@pytest.mark.integration
def test_runtime_smoke_preserves_blocked_refusal_and_citation_path(runtime: RuntimeV1) -> None:
    case = _first_rows(CASES, 1)[0]
    result = runtime.answer_query(case["query"], request_id=case["case_id"])
    assert result["runtime_version"] == "RUNTIME_V1"
    assert result["status"] == "COMPLETED"
    assert result["retrieval"]["retriever_version"] == "RAG_RETRIEVAL_V1"
    assert result["evidence"]["decision"] == "INSUFFICIENT"
    assert result["citation"]["support_status"] == "BLOCKED"
    assert result["refusal"]["refused"] is True
    assert "SUPPORT_BLOCKED" in result["refusal"]["reason_codes"]


@pytest.mark.integration
def test_runtime_small_legacy_equivalence_for_stable_fields(runtime: RuntimeV1) -> None:
    cases = _first_rows(CASES, 2)
    expected = {row["case_id"]: row for row in _first_rows(HISTORICAL, 2)}
    for case in cases:
        actual = runtime.answer_query(case["query"], request_id=case["case_id"])
        baseline = expected[case["case_id"]]
        assert [row["chunk_id"] for row in actual["retrieval"]["ordered_top5_chunks"]]
        assert actual["evidence"]["decision"] == baseline["evidence_status"]
        assert actual["citation"]["support_status"] == baseline["citation_status"]
        assert actual["diagnostics"]["orchestrator"]["answer_status"] == baseline["answer_status"]
        assert actual["answer"] == baseline["final_answer"]
