from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.citation_support_v1 import build_support_package  # noqa: E402


OUTPUT = ROOT / "evaluation" / "citation_support" / "v1" / "validation" / "unit_test_results.json"


def chunks() -> list[dict[str, Any]]:
    return [
        {"rank": 1, "source_id": "KBV1-PUB-A", "chunk_id": "CH-A1", "score": 0.9, "title": "Policy A", "url": "https://example.edu/a", "category": "policy", "text": "Alpha policy applies to all enrolled students. Deadline is June 1."},
        {"rank": 2, "source_id": "KBV1-PUB-A", "chunk_id": "CH-A2", "score": 0.8, "title": "Policy A", "url": "https://example.edu/a", "category": "policy", "text": "Applicants must submit the signed form, and provide an official transcript."},
        {"rank": 3, "source_id": "KBV1-PUB-B", "chunk_id": "CH-B1", "score": 0.7, "title": "Policy B", "url": "https://example.edu/b", "category": "guide", "text": "The service desk is open Monday through Friday."},
        {"rank": 4, "source_id": "KBV1-RES-X", "chunk_id": "CH-R1", "score": 0.6, "title": "Restricted guide", "url": "https://info.example.edu/r", "category": "internal", "text": "Restricted scholarship guidance requires faculty confirmation.", "auth_token": "DO_NOT_PROPAGATE"},
        {"rank": 5, "source_id": "KBV1-PUB-C", "chunk_id": "CH-C1", "score": 0.5, "title": "Policy C", "url": "https://example.edu/c", "category": "policy", "text": "Contact the registrar for record corrections."},
    ]


def retrieval(query: str = "test query", case_id: str = "CASE-001") -> dict[str, Any]:
    rows = chunks()
    return {
        "query": query,
        "case_id": case_id,
        "retriever_version": "RAG_RETRIEVAL_V1",
        "corpus_version": "KNOWLEDGE_BASE_V1",
        "ordered_top5_chunks": rows,
        "source_ids": [row["source_id"] for row in rows],
        "chunk_ids": [row["chunk_id"] for row in rows],
        "scores": [row["score"] for row in rows],
        "latency_ms": 1.0,
        "error": None,
    }


def span(span_id: str, chunk_id: str, source_id: str, text: Any) -> dict[str, Any]:
    return {"span_id": span_id, "chunk_id": chunk_id, "source_id": source_id, "score": 0.9, "text": text}


def point(point_id: str, status: str, spans: list[dict[str, Any]], text: str = "required fact") -> dict[str, Any]:
    return {
        "point_id": point_id,
        "text": text,
        "requested_attributes": [],
        "missing_requested_attributes": [],
        "status": status,
        "best_support_score": 0.9,
        "support_spans": spans,
        "conflicts": [],
    }


def evidence(decision: str, points: list[dict[str, Any]], query: str = "test query", case_id: str = "CASE-001") -> dict[str, Any]:
    valid_spans = [item for row in points if row["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} for item in row["support_spans"]]
    return {
        "query": query,
        "case_id": case_id,
        "evidence_sufficiency_version": "EVIDENCE_SUFFICIENCY_V1",
        "retriever_version": "RAG_RETRIEVAL_V1",
        "corpus_version": "KNOWLEDGE_BASE_V1",
        "decision": decision,
        "policy_signal": {"SUFFICIENT": "ALLOW_FULL_ANSWER", "PARTIAL": "ALLOW_PARTIAL_ANSWER", "INSUFFICIENT": "REQUIRE_REFUSAL"}[decision],
        "confidence": None,
        "required_points": points,
        "supported_points": [row["point_id"] for row in points if row["status"] == "SUPPORTED"],
        "partially_supported_points": [row["point_id"] for row in points if row["status"] == "PARTIALLY_SUPPORTED"],
        "unsupported_points": [row["point_id"] for row in points if row["status"] in {"NOT_SUPPORTED", "CONFLICT"}],
        "requested_attributes": [],
        "missing_requested_attributes": [],
        "optional_information": [],
        "supporting_chunk_ids": sorted({item["chunk_id"] for item in valid_spans}),
        "supporting_source_ids": sorted({item["source_id"] for item in valid_spans}),
        "reason_codes": [],
        "diagnostics": {},
        "latency_ms": 1.0,
        "error": None,
    }


def run(ev: dict[str, Any], ret: dict[str, Any] | None = None) -> dict[str, Any]:
    ret = ret or retrieval(ev.get("query", "test query"), ev.get("case_id", "CASE-001"))
    return build_support_package(ret["query"], ret["case_id"], ret, ev)


def contains_any(value: Any, needle: str) -> bool:
    return needle in json.dumps(value, ensure_ascii=False, sort_keys=True)


def scenarios() -> list[tuple[str, Callable[[], None]]]:
    tests: list[tuple[str, Callable[[], None]]] = []

    def add(name: str, fn: Callable[[], None]) -> None:
        tests.append((name, fn))

    def sufficient_one_source_one_chunk() -> None:
        out = run(evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "Alpha policy applies to all enrolled students")])]))
        assert out["support_status"] == "READY" and len(out["support_units"]) == 1 and len(out["citation_candidates"]) == 1

    def sufficient_one_source_multiple_chunks() -> None:
        points = [
            point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "Deadline is June 1")]),
            point("P2", "SUPPORTED", [span("S2", "CH-A2", "KBV1-PUB-A", "Applicants must submit the signed form")]),
        ]
        out = run(evidence("SUFFICIENT", points))
        assert out["support_status"] == "READY" and len(out["support_units"]) == 2 and len(out["source_groups"]) == 1

    def sufficient_multiple_sources() -> None:
        points = [
            point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "Deadline is June 1")]),
            point("P2", "SUPPORTED", [span("S2", "CH-B1", "KBV1-PUB-B", "service desk is open Monday through Friday")]),
        ]
        out = run(evidence("SUFFICIENT", points))
        assert out["support_status"] == "READY" and len(out["source_groups"]) == 2

    def partial() -> None:
        points = [
            point("P1", "PARTIALLY_SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "Alpha policy applies to all enrolled students")]),
            point("P2", "NOT_SUPPORTED", []),
        ]
        out = run(evidence("PARTIAL", points))
        assert out["support_status"] == "PARTIAL" and len(out["support_units"]) == 1

    def insufficient() -> None:
        out = run(evidence("INSUFFICIENT", [point("P1", "NOT_SUPPORTED", [])]))
        assert out["support_status"] == "BLOCKED" and not out["support_units"] and "EVIDENCE_DECISION_BLOCKED" in out["reason_codes"]

    def duplicate_supports() -> None:
        s = span("S1", "CH-A1", "KBV1-PUB-A", "Deadline is June 1")
        out = run(evidence("SUFFICIENT", [point("P1", "SUPPORTED", [s, dict(s, span_id="S1-DUP")])]))
        assert out["support_status"] == "READY" and any(row["reason_code"] == "DUPLICATE_SUPPORT" for row in out["excluded_candidates"])
        duplicate_chunk_retrieval = retrieval()
        duplicate_chunk_retrieval["ordered_top5_chunks"][1]["chunk_id"] = duplicate_chunk_retrieval["ordered_top5_chunks"][0]["chunk_id"]
        blocked = run(evidence("SUFFICIENT", [point("P1", "SUPPORTED", [s])]), duplicate_chunk_retrieval)
        assert blocked["support_status"] == "BLOCKED" and "INPUT_SCHEMA_INVALID" in blocked["reason_codes"]

    def invalid_span() -> None:
        out = run(evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", None)])]))
        assert out["support_status"] == "BLOCKED" and any(row["reason_code"] == "SPAN_INVALID" for row in out["excluded_candidates"])

    def span_mismatch() -> None:
        out = run(evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "This text is absent from the chunk")])]))
        assert out["support_status"] == "BLOCKED" and any(row["reason_code"] == "SPAN_NOT_FOUND" for row in out["excluded_candidates"])

    def chunk_outside_top5() -> None:
        out = run(evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-X", "KBV1-PUB-X", "External text that is long enough")])]))
        assert out["support_status"] == "BLOCKED" and "CHUNK_NOT_IN_RETRIEVAL" in out["reason_codes"]

    def source_mismatch() -> None:
        ev = evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-B", "Deadline is June 1")])])
        ev["supporting_source_ids"] = ["KBV1-PUB-B"]
        out = run(ev)
        assert out["support_status"] == "BLOCKED" and any(row["reason_code"] == "SOURCE_ID_MISMATCH" for row in out["excluded_candidates"])

    def version_mismatch() -> None:
        ev = evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "Deadline is June 1")])])
        ev["evidence_sufficiency_version"] = "EVIDENCE_SUFFICIENCY_V0"
        out = run(ev)
        assert out["support_status"] == "BLOCKED" and "VERSION_MISMATCH" in out["reason_codes"]

    def malformed_evidence() -> None:
        ev = evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "Deadline is June 1")])])
        del ev["required_points"]
        out = run(ev)
        assert out["support_status"] == "BLOCKED" and "INPUT_SCHEMA_INVALID" in out["reason_codes"]

    def empty_support() -> None:
        out = run(evidence("PARTIAL", [point("P1", "PARTIALLY_SUPPORTED", [])]))
        assert out["support_status"] == "BLOCKED" and "EMPTY_SUPPORT" in out["reason_codes"]

    def adjacent_span_normalization() -> None:
        spans = [
            span("S1", "CH-A2", "KBV1-PUB-A", "Applicants must submit the signed form"),
            span("S2", "CH-A2", "KBV1-PUB-A", "and provide an official transcript"),
        ]
        out = run(evidence("SUFFICIENT", [point("P1", "SUPPORTED", spans)]))
        assert out["support_status"] == "READY" and len(out["support_units"]) == 1 and "ADJACENT_SUPPORT_MERGED" in out["reason_codes"]

    def determinism() -> None:
        ev = evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-A1", "KBV1-PUB-A", "Deadline is June 1")])])
        a, b = run(copy.deepcopy(ev)), run(copy.deepcopy(ev))
        a.pop("latency_ms"); b.pop("latency_ms")
        assert a == b

    def restricted_metadata_sanitization() -> None:
        ev = evidence("SUFFICIENT", [point("P1", "SUPPORTED", [span("S1", "CH-R1", "KBV1-RES-X", "Restricted scholarship guidance requires faculty confirmation")])])
        out = run(ev)
        assert out["support_status"] == "READY" and "RESTRICTED_METADATA_SANITIZED" in out["reason_codes"]
        assert not contains_any(out, "DO_NOT_PROPAGATE") and out["support_units"][0]["source_class"] == "restricted"

    for item in (
        ("sufficient_one_source_one_chunk", sufficient_one_source_one_chunk),
        ("sufficient_one_source_multiple_chunks", sufficient_one_source_multiple_chunks),
        ("sufficient_multiple_sources", sufficient_multiple_sources),
        ("partial", partial), ("insufficient", insufficient), ("duplicate_supports", duplicate_supports),
        ("invalid_span", invalid_span), ("span_mismatch", span_mismatch), ("chunk_outside_top5", chunk_outside_top5),
        ("source_mismatch", source_mismatch), ("version_mismatch", version_mismatch), ("malformed_evidence", malformed_evidence),
        ("empty_support", empty_support), ("adjacent_span_normalization", adjacent_span_normalization),
        ("determinism", determinism), ("restricted_metadata_sanitization", restricted_metadata_sanitization),
    ):
        add(*item)
    return tests


def main() -> int:
    results = []
    for name, test in scenarios():
        try:
            test()
            results.append({"scenario": name, "status": "PASS", "error": None})
        except Exception as exc:
            results.append({"scenario": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    payload = {
        "suite": "CITATION_SUPPORT_V1_UNIT",
        "total": len(results),
        "passed": sum(row["status"] == "PASS" for row in results),
        "failed": sum(row["status"] == "FAIL" for row in results),
        "results": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
