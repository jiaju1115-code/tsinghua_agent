from __future__ import annotations

import copy
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from src.answer_generation_v1 import generate_answer
from src.answer_generation_v1.schema import OUTPUT_FIELDS as ANSWER_OUTPUT_FIELDS
from src.citation_support_v1 import build_support_package
from src.citation_support_v1.schema import OUTPUT_FIELDS as CITATION_OUTPUT_FIELDS
from src.evidence_sufficiency_v1 import evaluate_evidence
from src.evidence_sufficiency_v1.schema import OUTPUT_FIELDS as EVIDENCE_OUTPUT_FIELDS
from src.retrieval_v1 import DenseRetrieverV1

from .schema import (
    ANSWER_STATUSES,
    CITATION_STATUSES,
    EXPECTED_ANSWER,
    EXPECTED_CITATION,
    EXPECTED_CORPUS,
    EXPECTED_EVIDENCE,
    EXPECTED_RETRIEVER,
    OUTPUT_FIELDS,
    REASON_CODES,
    RETRIEVAL_CHUNK_FIELDS,
    RETRIEVAL_FIELDS,
    TRACE_FIELDS,
    VERSION,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "evaluation" / "e2e_orchestrator" / "runtime_v1" / "config" / "orchestrator_v1.json"


def _read_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _safe_message(value: Any) -> str:
    text = str(value or "upstream runtime reported an error")
    text = re.sub(r"[A-Za-z]:\\[^\r\n\t\"']+", "[PATH_REDACTED]", text)
    text = re.sub(r"(?i)(api[_ -]?key|authorization|token|secret)\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
    return text[:240]


def _base(query: Any, case_id: Any) -> dict[str, Any]:
    return {
        "query": query,
        "case_id": case_id,
        "orchestrator_version": VERSION,
        "orchestrator_status": "E2E_ERROR",
        "retrieval_status": "NOT_RUN",
        "evidence_status": "NOT_RUN",
        "citation_status": "NOT_RUN",
        "answer_status": "NOT_RUN",
        "final_answer": "",
        "answered_required_point_ids": [],
        "unanswered_required_point_ids": [],
        "used_support_unit_ids": [],
        "used_source_ids": [],
        "claims": [],
        "provenance": [],
        "trace_summary": [],
        "layer_latencies_ms": {"retrieval": None, "evidence": None, "citation": None, "answer": None},
        "orchestration_overhead_ms": 0.0,
        "total_latency_ms": 0.0,
        "reason_codes": [],
        "error": None,
    }


def _trace(
    stage: str,
    status: str,
    version: str | None,
    latency: Any,
    reason_codes: Any = None,
    error_code: str | None = None,
    counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    row = {
        "stage": stage,
        "status": status,
        "version": version,
        "reason_codes": sorted({str(code) for code in (reason_codes or [])}),
        "error_code": error_code,
        "latency_ms": latency if isinstance(latency, (int, float)) else None,
        "counts": counts or {},
    }
    assert set(row) == TRACE_FIELDS
    return row


class UnifiedE2EOrchestratorV1:
    """Strict, state-propagating coordinator for the four frozen V1 runtimes."""

    def __init__(
        self,
        retriever: Any | None = None,
        evidence_runtime: Callable[..., dict[str, Any]] = evaluate_evidence,
        citation_runtime: Callable[..., dict[str, Any]] = build_support_package,
        answer_runtime: Callable[..., dict[str, Any]] = generate_answer,
        model_adapter: Any | None = None,
    ) -> None:
        self.config = _read_config()
        if self.config.get("orchestrator_version") != VERSION or set(self.config.get("reason_codes", [])) != REASON_CODES:
            raise RuntimeError("orchestrator config/version contract mismatch")
        self._retriever = retriever
        self.evidence_runtime = evidence_runtime
        self.citation_runtime = citation_runtime
        self.answer_runtime = answer_runtime
        self.model_adapter = model_adapter
        self._seen_case_ids: set[str] = set()

    def _get_retriever(self) -> Any:
        if self._retriever is None:
            self._retriever = DenseRetrieverV1()
        return self._retriever

    def _finish(self, output: dict[str, Any], started: float) -> dict[str, Any]:
        output["reason_codes"] = sorted(set(output["reason_codes"]))
        total = round((time.perf_counter() - started) * 1000, 3)
        measured = sum(
            float(value) for value in output["layer_latencies_ms"].values() if isinstance(value, (int, float))
        )
        output["total_latency_ms"] = total
        output["orchestration_overhead_ms"] = round(max(0.0, total - measured), 3)
        assert set(output) == OUTPUT_FIELDS
        return output

    def _fail(
        self,
        output: dict[str, Any],
        started: float,
        layer: str,
        code: str,
        message: Any,
    ) -> dict[str, Any]:
        output["orchestrator_status"] = "E2E_ERROR"
        output["reason_codes"].extend([code, "UPSTREAM_FAIL_CLOSED"])
        output["error"] = {"layer": layer, "code": code, "message": _safe_message(message)}
        return self._finish(output, started)

    @staticmethod
    def _validate_retrieval(query: str, case_id: str, value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, dict) or set(value) != RETRIEVAL_FIELDS:
            return "INPUT_SCHEMA_INVALID", "Retriever output does not have the exact frozen field set"
        if value.get("retriever_version") != EXPECTED_RETRIEVER or value.get("corpus_version") != EXPECTED_CORPUS:
            return "VERSION_MISMATCH", "Retriever/corpus version differs from the frozen chain"
        if value.get("query") != query or value.get("case_id") != case_id:
            return "QUERY_CASE_MISMATCH", "Retriever query/case_id differs from the request"
        chunks = value.get("ordered_top5_chunks")
        if (
            not isinstance(chunks, list)
            or len(chunks) != 5
            or any(not isinstance(row, dict) or set(row) != RETRIEVAL_CHUNK_FIELDS for row in chunks)
            or [row.get("rank") for row in chunks] != [1, 2, 3, 4, 5]
            or len({row.get("chunk_id") for row in chunks}) != 5
        ):
            return "INPUT_SCHEMA_INVALID", "Retriever Top-5 rows violate the frozen contract"
        if value.get("error"):
            return "RETRIEVAL_ERROR", value["error"]
        return None, None

    @staticmethod
    def _validate_evidence(query: str, case_id: str, value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, dict) or set(value) != EVIDENCE_OUTPUT_FIELDS:
            return "INPUT_SCHEMA_INVALID", "Evidence output does not have the exact frozen field set"
        if (
            value.get("evidence_sufficiency_version") != EXPECTED_EVIDENCE
            or value.get("retriever_version") != EXPECTED_RETRIEVER
            or value.get("corpus_version") != EXPECTED_CORPUS
        ):
            return "VERSION_MISMATCH", "Evidence version chain differs from the frozen contract"
        if value.get("query") != query or value.get("case_id") != case_id:
            return "QUERY_CASE_MISMATCH", "Evidence query/case_id differs from the request"
        if value.get("decision") not in {"SUFFICIENT", "PARTIAL", "INSUFFICIENT"}:
            return "INPUT_SCHEMA_INVALID", "Evidence decision is outside the frozen vocabulary"
        if value.get("error"):
            return "EVIDENCE_ERROR", value["error"]
        return None, None

    @staticmethod
    def _validate_citation(query: str, case_id: str, value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, dict) or set(value) != CITATION_OUTPUT_FIELDS:
            return "INPUT_SCHEMA_INVALID", "Citation output does not have the exact frozen field set"
        if (
            value.get("citation_support_version") != EXPECTED_CITATION
            or value.get("evidence_sufficiency_version") != EXPECTED_EVIDENCE
            or value.get("retriever_version") != EXPECTED_RETRIEVER
            or value.get("corpus_version") != EXPECTED_CORPUS
        ):
            return "VERSION_MISMATCH", "Citation version chain differs from the frozen contract"
        if value.get("query") != query or value.get("case_id") != case_id:
            return "QUERY_CASE_MISMATCH", "Citation query/case_id differs from the request"
        if value.get("support_status") not in CITATION_STATUSES[:3]:
            return "INPUT_SCHEMA_INVALID", "Citation support_status is outside the frozen vocabulary"
        if value.get("error"):
            return "CITATION_ERROR", value["error"]
        return None, None

    @staticmethod
    def _validate_answer(query: str, case_id: str, value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, dict) or set(value) != ANSWER_OUTPUT_FIELDS:
            return "INPUT_SCHEMA_INVALID", "Answer output does not have the exact frozen field set"
        if (
            value.get("answer_generation_version") != EXPECTED_ANSWER
            or value.get("citation_support_version") != EXPECTED_CITATION
            or value.get("evidence_sufficiency_version") != EXPECTED_EVIDENCE
            or value.get("retriever_version") != EXPECTED_RETRIEVER
            or value.get("corpus_version") != EXPECTED_CORPUS
        ):
            return "VERSION_MISMATCH", "Answer version chain differs from the frozen contract"
        if value.get("query") != query or value.get("case_id") != case_id:
            return "QUERY_CASE_MISMATCH", "Answer query/case_id differs from the request"
        if value.get("answer_status") not in ANSWER_STATUSES[:3]:
            return "INPUT_SCHEMA_INVALID", "Answer status is outside the frozen vocabulary"
        if value.get("error") and "PROMPT_INJECTION_GUARD" not in value.get("reason_codes", []):
            return "ANSWER_ERROR", value["error"]
        return None, None

    @staticmethod
    def _provenance(
        retrieval: dict[str, Any], citation: dict[str, Any], answer: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], bool, bool]:
        chunks = {row["chunk_id"]: row for row in retrieval["ordered_top5_chunks"]}
        units = {row["support_unit_id"]: row for row in citation["support_units"]}
        mappings = {row["point_id"]: row for row in citation["required_point_support"]}
        result: list[dict[str, Any]] = []
        gap = False
        restricted = False
        for claim in answer["claim_records"]:
            if claim.get("claim_type") != "FACTUAL":
                continue
            support_rows = []
            documents = []
            point_ids = claim.get("required_point_ids")
            support_ids = claim.get("support_unit_ids")
            source_ids = claim.get("source_ids")
            if not isinstance(point_ids, list) or not point_ids or not isinstance(support_ids, list) or not support_ids:
                gap = True
                continue
            for support_id in support_ids:
                unit = units.get(support_id)
                if unit is None:
                    gap = True
                    continue
                chunk = chunks.get(unit.get("chunk_id"))
                if chunk is None or chunk.get("source_id") != unit.get("source_id"):
                    gap = True
                    continue
                if not set(point_ids).issubset(set(unit.get("required_point_ids", []))):
                    gap = True
                if any(point not in mappings or support_id not in mappings[point].get("support_unit_ids", []) for point in point_ids):
                    gap = True
                if unit.get("source_id") not in source_ids:
                    gap = True
                is_restricted = unit.get("source_class") == "restricted"
                restricted = restricted or is_restricted
                support_rows.append({
                    "support_unit_id": support_id,
                    "source_id": unit["source_id"],
                    "chunk_id": unit["chunk_id"],
                    "evidence_span_ids": list(unit.get("evidence_span_ids", [])),
                })
                documents.append({
                    "source_id": unit["source_id"],
                    "title": None if is_restricted else chunk.get("title"),
                    "url": None if is_restricted else chunk.get("url"),
                    "category": None if is_restricted else chunk.get("category"),
                    "source_class": unit.get("source_class"),
                })
            result.append({
                "claim_id": claim.get("claim_id"),
                "required_point_ids": list(point_ids),
                "support_links": support_rows,
                "documents": sorted(
                    {json.dumps(row, ensure_ascii=False, sort_keys=True): row for row in documents}.values(),
                    key=lambda row: row["source_id"],
                ),
            })
        return result, gap, restricted

    def run_e2e(self, query: str, case_id: str) -> dict[str, Any]:
        started = time.perf_counter()
        output = _base(query, case_id)
        if not isinstance(query, str) or not query.strip() or not isinstance(case_id, str) or not case_id.strip():
            return self._fail(output, started, "orchestrator", "INPUT_SCHEMA_INVALID", "query and case_id must be non-empty strings")
        if case_id in self._seen_case_ids:
            return self._fail(output, started, "orchestrator", "DUPLICATE_CASE_ID", "case_id was already used in this orchestrator session")
        self._seen_case_ids.add(case_id)

        try:
            retrieval = self._get_retriever().retrieve(query, case_id)
        except Exception as exc:
            output["retrieval_status"] = "ERROR"
            output["trace_summary"].append(_trace("retrieval", "ERROR", EXPECTED_RETRIEVER, None, error_code="RETRIEVAL_ERROR"))
            return self._fail(output, started, "retrieval", "RETRIEVAL_ERROR", f"{type(exc).__name__}: {exc}")
        output["layer_latencies_ms"]["retrieval"] = retrieval.get("latency_ms") if isinstance(retrieval, dict) else None
        code, message = self._validate_retrieval(query, case_id, retrieval)
        if code:
            output["retrieval_status"] = "ERROR"
            output["trace_summary"].append(_trace("retrieval", "ERROR", retrieval.get("retriever_version") if isinstance(retrieval, dict) else None, output["layer_latencies_ms"]["retrieval"], error_code=code))
            return self._fail(output, started, "retrieval", code, message)
        output["retrieval_status"] = "SUCCESS"
        output["trace_summary"].append(_trace("retrieval", "SUCCESS", retrieval["retriever_version"], retrieval["latency_ms"], counts={"chunks": 5, "sources": len(set(retrieval["source_ids"]))}))

        try:
            evidence = self.evidence_runtime(query, case_id, copy.deepcopy(retrieval))
        except Exception as exc:
            output["evidence_status"] = "ERROR"
            output["trace_summary"].append(_trace("evidence", "ERROR", EXPECTED_EVIDENCE, None, error_code="EVIDENCE_ERROR"))
            return self._fail(output, started, "evidence", "EVIDENCE_ERROR", f"{type(exc).__name__}: {exc}")
        output["layer_latencies_ms"]["evidence"] = evidence.get("latency_ms") if isinstance(evidence, dict) else None
        code, message = self._validate_evidence(query, case_id, evidence)
        if code:
            output["evidence_status"] = "ERROR"
            output["trace_summary"].append(_trace("evidence", "ERROR", evidence.get("evidence_sufficiency_version") if isinstance(evidence, dict) else None, output["layer_latencies_ms"]["evidence"], evidence.get("reason_codes", []) if isinstance(evidence, dict) else [], code))
            return self._fail(output, started, "evidence", code, message)
        output["evidence_status"] = evidence["decision"]
        output["trace_summary"].append(_trace("evidence", evidence["decision"], evidence["evidence_sufficiency_version"], evidence["latency_ms"], evidence["reason_codes"], counts={"required_points": len(evidence["required_points"]), "supported": len(evidence["supported_points"]), "partial": len(evidence["partially_supported_points"]), "unsupported": len(evidence["unsupported_points"])}))

        try:
            citation = self.citation_runtime(query, case_id, copy.deepcopy(retrieval), copy.deepcopy(evidence))
        except Exception as exc:
            output["citation_status"] = "ERROR"
            output["trace_summary"].append(_trace("citation", "ERROR", EXPECTED_CITATION, None, error_code="CITATION_ERROR"))
            return self._fail(output, started, "citation", "CITATION_ERROR", f"{type(exc).__name__}: {exc}")
        output["layer_latencies_ms"]["citation"] = citation.get("latency_ms") if isinstance(citation, dict) else None
        code, message = self._validate_citation(query, case_id, citation)
        if code:
            output["citation_status"] = "ERROR"
            output["trace_summary"].append(_trace("citation", "ERROR", citation.get("citation_support_version") if isinstance(citation, dict) else None, output["layer_latencies_ms"]["citation"], citation.get("reason_codes", []) if isinstance(citation, dict) else [], code))
            return self._fail(output, started, "citation", code, message)
        output["citation_status"] = citation["support_status"]
        output["trace_summary"].append(_trace("citation", citation["support_status"], citation["citation_support_version"], citation["latency_ms"], citation["reason_codes"], counts={"support_units": len(citation["support_units"]), "sources": len(citation["usable_source_ids"]), "mapped_points": sum(row["mapping_status"] != "UNSUPPORTED" for row in citation["required_point_support"])}))

        try:
            answer = self.answer_runtime(query, case_id, copy.deepcopy(citation), self.model_adapter)
        except Exception as exc:
            output["answer_status"] = "ERROR"
            output["trace_summary"].append(_trace("answer", "ERROR", EXPECTED_ANSWER, None, error_code="ANSWER_ERROR"))
            return self._fail(output, started, "answer", "ANSWER_ERROR", f"{type(exc).__name__}: {exc}")
        output["layer_latencies_ms"]["answer"] = answer.get("latency_ms") if isinstance(answer, dict) else None
        code, message = self._validate_answer(query, case_id, answer)
        if code:
            output["answer_status"] = "ERROR"
            output["trace_summary"].append(_trace("answer", "ERROR", answer.get("answer_generation_version") if isinstance(answer, dict) else None, output["layer_latencies_ms"]["answer"], answer.get("reason_codes", []) if isinstance(answer, dict) else [], code))
            return self._fail(output, started, "answer", code, message)

        injection_refusal = answer["answer_status"] == "REFUSAL" and "PROMPT_INJECTION_GUARD" in answer["reason_codes"]
        expected = {"READY": "FULL_ANSWER", "PARTIAL": "PARTIAL_ANSWER", "BLOCKED": "REFUSAL"}[citation["support_status"]]
        if answer["answer_status"] != expected and not injection_refusal:
            output["answer_status"] = "ERROR"
            output["trace_summary"].append(_trace("answer", "ERROR", answer["answer_generation_version"], answer["latency_ms"], answer["reason_codes"], "FROZEN_CONTRACT_CONFLICT"))
            return self._fail(output, started, "answer", "FROZEN_CONTRACT_CONFLICT", "Citation and Answer statuses violate frozen propagation semantics")
        if citation["support_status"] == "BLOCKED" and answer.get("diagnostics", {}).get("model_called") is not False:
            output["answer_status"] = "ERROR"
            output["trace_summary"].append(_trace("answer", "ERROR", answer["answer_generation_version"], answer["latency_ms"], answer["reason_codes"], "FROZEN_CONTRACT_CONFLICT"))
            return self._fail(output, started, "answer", "FROZEN_CONTRACT_CONFLICT", "BLOCKED path did not preserve Answer no-model-call behavior")

        provenance, gap, restricted = self._provenance(retrieval, citation, answer)
        if gap:
            output["answer_status"] = "ERROR"
            output["trace_summary"].append(_trace("answer", "ERROR", answer["answer_generation_version"], answer["latency_ms"], answer["reason_codes"], "PROVENANCE_LINK_UNAVAILABLE"))
            return self._fail(output, started, "provenance", "PROVENANCE_LINK_UNAVAILABLE", "A factual claim cannot be linked through point/support/source/chunk/document")

        output.update({
            "orchestrator_status": "COMPLETED",
            "answer_status": answer["answer_status"],
            "final_answer": answer["answer_text"],
            "answered_required_point_ids": answer["answered_required_point_ids"],
            "unanswered_required_point_ids": answer["unanswered_required_point_ids"],
            "used_support_unit_ids": answer["used_support_unit_ids"],
            "used_source_ids": answer["used_source_ids"],
            "claims": answer["claim_records"],
            "provenance": provenance,
            "error": None,
        })
        output["trace_summary"].append(_trace("answer", answer["answer_status"], answer["answer_generation_version"], answer["latency_ms"], answer["reason_codes"], counts={"claims": len(answer["claim_records"]), "used_support_units": len(answer["used_support_unit_ids"]), "used_sources": len(answer["used_source_ids"])}))
        propagation = {"READY": "READY_PROPAGATED", "PARTIAL": "PARTIAL_PROPAGATED", "BLOCKED": "BLOCKED_PROPAGATED"}[citation["support_status"]]
        output["reason_codes"].extend(["PIPELINE_COMPLETED", propagation])
        if injection_refusal:
            output["reason_codes"].append("INJECTION_BOUNDARY_PRESERVED")
        if restricted:
            output["reason_codes"].append("RESTRICTED_METADATA_SANITIZED")
        return self._finish(output, started)


def run_e2e(
    query: str,
    case_id: str,
    retriever: Any | None = None,
    model_adapter: Any | None = None,
) -> dict[str, Any]:
    """Public one-shot API. Use UnifiedE2EOrchestratorV1 for a duplicate-aware session."""
    return UnifiedE2EOrchestratorV1(retriever=retriever, model_adapter=model_adapter).run_e2e(query, case_id)
