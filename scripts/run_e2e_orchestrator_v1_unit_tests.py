from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.answer_generation_v1.schema import OUTPUT_FIELDS as ANSWER_FIELDS
from src.citation_support_v1.schema import OUTPUT_FIELDS as CITATION_FIELDS
from src.e2e_orchestrator_v1 import UnifiedE2EOrchestratorV1
from src.e2e_orchestrator_v1.schema import OUTPUT_FIELDS
from src.evidence_sufficiency_v1.schema import OUTPUT_FIELDS as EVIDENCE_FIELDS


OUTPUT = ROOT / "evaluation" / "e2e_orchestrator" / "runtime_v1" / "validation" / "unit_test_results.json"
QUERY = "What policy applies?"
CASE = "E2E-UNIT-001"


def retrieval(query: str = QUERY, case_id: str = CASE) -> dict[str, Any]:
    chunks = [
        {"rank": rank, "source_id": f"SRC-{rank}", "chunk_id": f"CH-{rank}", "score": 1.0 / rank,
         "title": f"Document {rank}", "url": f"https://example.edu/{rank}", "category": "policy",
         "text": "The frozen policy applies to enrolled students and remains the exact support text."}
        for rank in range(1, 6)
    ]
    return {"query": query, "case_id": case_id, "retriever_version": "RAG_RETRIEVAL_V1",
            "corpus_version": "KNOWLEDGE_BASE_V1", "ordered_top5_chunks": chunks,
            "source_ids": [row["source_id"] for row in chunks], "chunk_ids": [row["chunk_id"] for row in chunks],
            "scores": [row["score"] for row in chunks], "latency_ms": 1.0, "error": None}


def evidence(decision: str = "SUFFICIENT", query: str = QUERY, case_id: str = CASE) -> dict[str, Any]:
    point_status = {"SUFFICIENT": "SUPPORTED", "PARTIAL": "PARTIALLY_SUPPORTED", "INSUFFICIENT": "NOT_SUPPORTED"}[decision]
    supported = point_status == "SUPPORTED"
    partial = point_status == "PARTIALLY_SUPPORTED"
    span = {"span_id": "CH-1#S1", "chunk_id": "CH-1", "source_id": "SRC-1", "score": 1.0,
            "text": "The frozen policy applies to enrolled students and remains the exact support text."}
    value = {"query": query, "case_id": case_id, "evidence_sufficiency_version": "EVIDENCE_SUFFICIENCY_V1",
             "retriever_version": "RAG_RETRIEVAL_V1", "corpus_version": "KNOWLEDGE_BASE_V1", "decision": decision,
             "policy_signal": {"SUFFICIENT": "ALLOW_FULL_ANSWER", "PARTIAL": "ALLOW_PARTIAL_ANSWER", "INSUFFICIENT": "REQUIRE_REFUSAL"}[decision],
             "confidence": None, "required_points": [{"point_id": "P1", "text": QUERY, "requested_attributes": [],
             "missing_requested_attributes": [], "status": point_status, "best_support_score": 1.0 if supported else 0.3 if partial else 0.0,
             "support_spans": [span] if (supported or partial) else [], "conflicts": []}],
             "supported_points": ["P1"] if supported else [], "partially_supported_points": ["P1"] if partial else [],
             "unsupported_points": ["P1"] if decision == "INSUFFICIENT" else [], "requested_attributes": [],
             "missing_requested_attributes": [], "optional_information": [], "supporting_chunk_ids": ["CH-1"] if decision != "INSUFFICIENT" else [],
             "supporting_source_ids": ["SRC-1"] if decision != "INSUFFICIENT" else [], "reason_codes": [f"FIXTURE_{decision}"],
             "diagnostics": {"semantic_entailment": False}, "latency_ms": 2.0, "error": None}
    assert set(value) == EVIDENCE_FIELDS
    return value


def citation(status: str = "READY", query: str = QUERY, case_id: str = CASE, restricted: bool = False) -> dict[str, Any]:
    blocked = status == "BLOCKED"
    unit = {"support_unit_id": "CSU-1", "required_point_ids": ["P1"], "source_id": "SRC-1", "chunk_id": "CH-1",
            "source_title": "Document 1", "source_url": "https://example.edu/1", "source_class": "restricted" if restricted else "public",
            "category": "policy", "span_text": "The frozen policy applies to enrolled students and remains the exact support text.",
            "span_start": 0, "span_end": 82, "original_span_texts": [], "normalized_span_text": "support", "normalization_reasons": [],
            "support_role": "PRIMARY", "retriever_rank": 1, "evidence_span_ids": ["CH-1#S1"], "match_occurrence_count": 1}
    mapping_status = "UNSUPPORTED" if blocked else "SUPPORTED" if status == "READY" else "PARTIALLY_SUPPORTED"
    value = {"query": query, "case_id": case_id, "citation_support_version": "CITATION_SUPPORT_V1",
             "evidence_sufficiency_version": "EVIDENCE_SUFFICIENCY_V1", "retriever_version": "RAG_RETRIEVAL_V1",
             "corpus_version": "KNOWLEDGE_BASE_V1", "evidence_decision": {"READY": "SUFFICIENT", "PARTIAL": "PARTIAL", "BLOCKED": "INSUFFICIENT"}[status],
             "policy_signal": {"READY": "ALLOW_FULL_ANSWER", "PARTIAL": "ALLOW_PARTIAL_ANSWER", "BLOCKED": "REQUIRE_REFUSAL"}[status],
             "support_status": status, "required_point_support": [{"point_id": "P1", "point_text": QUERY,
             "evidence_point_status": "NOT_SUPPORTED" if blocked else "SUPPORTED", "mapping_status": mapping_status,
             "support_unit_ids": [] if blocked else ["CSU-1"], "source_ids": [] if blocked else ["SRC-1"], "integrity_issue": "EVIDENCE_DECISION_BLOCKED" if blocked else None}],
             "support_units": [] if blocked else [unit], "citation_candidates": [], "excluded_candidates": [], "source_groups": [],
             "usable_chunk_ids": [] if blocked else ["CH-1"], "usable_source_ids": [] if blocked else ["SRC-1"],
             "reason_codes": [f"FIXTURE_{status}"], "diagnostics": {"semantic_entailment": False}, "latency_ms": 3.0, "error": None}
    assert set(value) == CITATION_FIELDS
    return value


def answer(status: str = "FULL_ANSWER", query: str = QUERY, case_id: str = CASE, injection: bool = False) -> dict[str, Any]:
    factual = status != "REFUSAL"
    claim = {"claim_id": "AC-1", "claim_text": "The frozen policy applies to enrolled students." if factual else "I cannot answer from the available support.",
             "claim_type": "FACTUAL" if factual else "REFUSAL", "required_point_ids": ["P1"] if factual else [],
             "support_unit_ids": ["CSU-1"] if factual else [], "source_ids": ["SRC-1"] if factual else []}
    support_status = {"FULL_ANSWER": "READY", "PARTIAL_ANSWER": "PARTIAL", "REFUSAL": "READY" if injection else "BLOCKED"}[status]
    value = {"query": query, "case_id": case_id, "answer_generation_version": "ANSWER_GENERATION_V1",
             "citation_support_version": "CITATION_SUPPORT_V1", "evidence_sufficiency_version": "EVIDENCE_SUFFICIENCY_V1",
             "retriever_version": "RAG_RETRIEVAL_V1", "corpus_version": "KNOWLEDGE_BASE_V1", "support_status": support_status,
             "answer_status": status, "answer_text": claim["claim_text"], "answered_required_point_ids": ["P1"] if factual else [],
             "unanswered_required_point_ids": [] if status == "FULL_ANSWER" else ["P1"], "used_support_unit_ids": ["CSU-1"] if factual else [],
             "used_source_ids": ["SRC-1"] if factual else [], "claim_records": [claim],
             "reason_codes": ["PROMPT_INJECTION_GUARD", "MODEL_NOT_CALLED"] if injection else [f"FIXTURE_{status}"],
             "diagnostics": {"semantic_unsupported_claim_detection": False, "model_called": factual}, "latency_ms": 4.0,
             "error": "blocked instruction pattern" if injection else None}
    assert set(value) == ANSWER_FIELDS
    return value


class FakeRetriever:
    def __init__(self, value: Any = None, failure: Exception | None = None, calls: dict[str, int] | None = None) -> None:
        self.value, self.failure, self.calls = value if value is not None else retrieval(), failure, calls if calls is not None else {}

    def retrieve(self, query: str, case_id: str) -> dict[str, Any]:
        self.calls["retrieval"] = self.calls.get("retrieval", 0) + 1
        if self.failure:
            raise self.failure
        return copy.deepcopy(self.value)


def orchestrator(ret: Any = None, ev: Any = None, cit: Any = None, ans: Any = None, calls: dict[str, int] | None = None) -> UnifiedE2EOrchestratorV1:
    counts = calls if calls is not None else {}
    def wrap(name: str, value: Any) -> Callable[..., dict[str, Any]]:
        def function(*_: Any) -> dict[str, Any]:
            counts[name] = counts.get(name, 0) + 1
            if isinstance(value, Exception):
                raise value
            return copy.deepcopy(value)
        return function
    return UnifiedE2EOrchestratorV1(
        retriever=FakeRetriever(ret if ret is not None else retrieval(), calls=counts),
        evidence_runtime=wrap("evidence", ev if ev is not None else evidence()),
        citation_runtime=wrap("citation", cit if cit is not None else citation()),
        answer_runtime=wrap("answer", ans if ans is not None else answer()),
    )


def check_error(result: dict[str, Any], layer: str, code: str) -> None:
    assert result["orchestrator_status"] == "E2E_ERROR"
    assert result["error"]["layer"] == layer and result["error"]["code"] == code


def scenarios() -> list[tuple[str, Callable[[], None]]]:
    rows: list[tuple[str, Callable[[], None]]] = []
    def add(name: str, function: Callable[[], None]) -> None: rows.append((name, function))

    def full() -> None:
        result = orchestrator().run_e2e(QUERY, CASE); assert result["answer_status"] == "FULL_ANSWER" and result["provenance"]
    def partial() -> None:
        result = orchestrator(ev=evidence("PARTIAL"), cit=citation("PARTIAL"), ans=answer("PARTIAL_ANSWER")).run_e2e(QUERY, CASE); assert result["answer_status"] == "PARTIAL_ANSWER"
    def blocked() -> None:
        result = orchestrator(ev=evidence("INSUFFICIENT"), cit=citation("BLOCKED"), ans=answer("REFUSAL")).run_e2e(QUERY, CASE); assert result["answer_status"] == "REFUSAL" and result["trace_summary"][-1]["status"] == "REFUSAL"
    add("ready_full_answer", full); add("partial_partial_answer", partial); add("blocked_refusal_no_model", blocked)

    add("empty_query", lambda: check_error(orchestrator().run_e2e("", CASE), "orchestrator", "INPUT_SCHEMA_INVALID"))
    add("empty_case_id", lambda: check_error(orchestrator().run_e2e(QUERY, ""), "orchestrator", "INPUT_SCHEMA_INVALID"))
    def duplicate() -> None:
        runtime = orchestrator(); runtime.run_e2e(QUERY, CASE); check_error(runtime.run_e2e(QUERY, CASE), "orchestrator", "DUPLICATE_CASE_ID")
    add("duplicate_case_id", duplicate)
    def retrieval_exception() -> None:
        runtime = orchestrator(); runtime._retriever.failure = RuntimeError("boom"); check_error(runtime.run_e2e(QUERY, CASE), "retrieval", "RETRIEVAL_ERROR")
    add("retrieval_exception", retrieval_exception)
    for name, mutate, code in (
        ("retrieval_missing_field", lambda x: x.pop("scores"), "INPUT_SCHEMA_INVALID"),
        ("retrieval_extra_field", lambda x: x.update(extra=True), "INPUT_SCHEMA_INVALID"),
        ("retrieval_error", lambda x: x.update(error="failed"), "RETRIEVAL_ERROR"),
        ("retrieval_version_mismatch", lambda x: x.update(retriever_version="V0"), "VERSION_MISMATCH"),
        ("retrieval_query_mismatch", lambda x: x.update(query="other"), "QUERY_CASE_MISMATCH"),
        ("retrieval_not_top5", lambda x: x["ordered_top5_chunks"].pop(), "INPUT_SCHEMA_INVALID"),
    ):
        def scenario(mutate: Callable[[dict[str, Any]], Any] = mutate, code: str = code) -> None:
            value = retrieval(); mutate(value); check_error(orchestrator(ret=value).run_e2e(QUERY, CASE), "retrieval", code)
        add(name, scenario)
    add("evidence_exception", lambda: check_error(orchestrator(ev=RuntimeError("boom")).run_e2e(QUERY, CASE), "evidence", "EVIDENCE_ERROR"))
    for name, mutate, code in (
        ("evidence_missing_field", lambda x: x.pop("confidence"), "INPUT_SCHEMA_INVALID"),
        ("evidence_error", lambda x: x.update(error="failed"), "EVIDENCE_ERROR"),
        ("evidence_version_mismatch", lambda x: x.update(evidence_sufficiency_version="V0"), "VERSION_MISMATCH"),
        ("evidence_query_mismatch", lambda x: x.update(case_id="other"), "QUERY_CASE_MISMATCH"),
    ):
        def scenario(mutate: Callable[[dict[str, Any]], Any] = mutate, code: str = code) -> None:
            value = evidence(); mutate(value); check_error(orchestrator(ev=value).run_e2e(QUERY, CASE), "evidence", code)
        add(name, scenario)
    add("citation_exception", lambda: check_error(orchestrator(cit=RuntimeError("boom")).run_e2e(QUERY, CASE), "citation", "CITATION_ERROR"))
    for name, mutate, code in (
        ("citation_missing_field", lambda x: x.pop("source_groups"), "INPUT_SCHEMA_INVALID"),
        ("citation_error", lambda x: x.update(error="failed"), "CITATION_ERROR"),
        ("citation_version_mismatch", lambda x: x.update(citation_support_version="V0"), "VERSION_MISMATCH"),
        ("citation_query_mismatch", lambda x: x.update(query="other"), "QUERY_CASE_MISMATCH"),
    ):
        def scenario(mutate: Callable[[dict[str, Any]], Any] = mutate, code: str = code) -> None:
            value = citation(); mutate(value); check_error(orchestrator(cit=value).run_e2e(QUERY, CASE), "citation", code)
        add(name, scenario)
    add("answer_exception", lambda: check_error(orchestrator(ans=RuntimeError("boom")).run_e2e(QUERY, CASE), "answer", "ANSWER_ERROR"))
    for name, mutate, code in (
        ("answer_missing_field", lambda x: x.pop("claims") if "claims" in x else x.pop("claim_records"), "INPUT_SCHEMA_INVALID"),
        ("answer_error", lambda x: x.update(error="failed"), "ANSWER_ERROR"),
        ("answer_version_mismatch", lambda x: x.update(answer_generation_version="V0"), "VERSION_MISMATCH"),
        ("answer_query_mismatch", lambda x: x.update(query="other"), "QUERY_CASE_MISMATCH"),
    ):
        def scenario(mutate: Callable[[dict[str, Any]], Any] = mutate, code: str = code) -> None:
            value = answer(); mutate(value); check_error(orchestrator(ans=value).run_e2e(QUERY, CASE), "answer", code)
        add(name, scenario)
    add("status_conflict", lambda: check_error(orchestrator(ans=answer("PARTIAL_ANSWER")).run_e2e(QUERY, CASE), "answer", "FROZEN_CONTRACT_CONFLICT"))
    def blocked_model_called() -> None:
        value = answer("REFUSAL"); value["diagnostics"]["model_called"] = True
        check_error(orchestrator(ev=evidence("INSUFFICIENT"), cit=citation("BLOCKED"), ans=value).run_e2e(QUERY, CASE), "answer", "FROZEN_CONTRACT_CONFLICT")
    add("blocked_model_called_conflict", blocked_model_called)
    def provenance_gap() -> None:
        value = answer(); value["claim_records"][0]["support_unit_ids"] = ["UNKNOWN"]
        check_error(orchestrator(ans=value).run_e2e(QUERY, CASE), "provenance", "PROVENANCE_LINK_UNAVAILABLE")
    add("provenance_gap", provenance_gap)
    def injection() -> None:
        result = orchestrator(ans=answer("REFUSAL", injection=True)).run_e2e(QUERY, CASE)
        assert result["orchestrator_status"] == "COMPLETED" and "INJECTION_BOUNDARY_PRESERVED" in result["reason_codes"]
    add("frozen_injection_refusal_preserved", injection)
    def restricted() -> None:
        result = orchestrator(cit=citation(restricted=True)).run_e2e(QUERY, CASE)
        assert result["provenance"][0]["documents"][0]["url"] is None and "RESTRICTED_METADATA_SANITIZED" in result["reason_codes"]
    add("restricted_metadata_sanitized", restricted)
    def exact_schema() -> None: assert set(orchestrator().run_e2e(QUERY, CASE)) == OUTPUT_FIELDS
    add("output_schema_exact", exact_schema)
    def no_skipped_downstream() -> None:
        counts: dict[str, int] = {}; value = retrieval(); value["error"] = "fail"
        result = orchestrator(ret=value, calls=counts).run_e2e(QUERY, CASE)
        assert result["evidence_status"] == "NOT_RUN" and counts == {"retrieval": 1}
    add("upstream_error_stops_downstream", no_skipped_downstream)
    def no_retry() -> None:
        counts: dict[str, int] = {}; orchestrator(calls=counts).run_e2e(QUERY, CASE)
        assert counts == {"retrieval": 1, "evidence": 1, "citation": 1, "answer": 1}
    add("each_layer_called_once_no_retry", no_retry)
    def compact_trace() -> None:
        trace = orchestrator().run_e2e(QUERY, CASE)["trace_summary"]
        blob = json.dumps(trace).lower(); assert len(trace) == 4 and not any(token in blob for token in ("prompt", "messages", "span_text", "ordered_top5_chunks"))
    add("trace_is_compact", compact_trace)
    return rows


def main() -> int:
    results = []
    for name, scenario in scenarios():
        try:
            scenario(); results.append({"scenario": name, "status": "PASS", "error": None})
        except Exception as exc:
            results.append({"scenario": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    payload = {"suite": "UNIFIED_E2E_ORCHESTRATOR_V1_UNIT", "total": len(results),
               "passed": sum(row["status"] == "PASS" for row in results),
               "failed": sum(row["status"] == "FAIL" for row in results), "results": results}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("total", "passed", "failed")}))
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
