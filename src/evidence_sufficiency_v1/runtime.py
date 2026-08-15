from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from .policy import (
    attribute_values,
    clean_text,
    compact,
    decompose_query,
    evidence_has_attribute,
    evidence_sentences,
    extract_entities,
    overlap_score,
)
from .schema import EXPECTED_CORPUS, EXPECTED_RETRIEVER, POLICY_SIGNALS, VERSION


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "evaluation" / "evidence_sufficiency" / "v1" / "config" / "runtime_v1.json"


def _config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _base(query: Any, case_id: Any, retrieval: Any) -> dict[str, Any]:
    retriever = retrieval.get("retriever_version") if isinstance(retrieval, dict) else None
    corpus = retrieval.get("corpus_version") if isinstance(retrieval, dict) else None
    return {
        "query": query,
        "case_id": case_id,
        "evidence_sufficiency_version": VERSION,
        "retriever_version": retriever,
        "corpus_version": corpus,
        "decision": "INSUFFICIENT",
        "policy_signal": POLICY_SIGNALS["INSUFFICIENT"],
        "confidence": None,
        "required_points": [],
        "supported_points": [],
        "partially_supported_points": [],
        "unsupported_points": [],
        "requested_attributes": [],
        "missing_requested_attributes": [],
        "optional_information": [],
        "supporting_chunk_ids": [],
        "supporting_source_ids": [],
        "reason_codes": [],
        "diagnostics": {
            "semantic_entailment": False,
            "method": "deterministic_lexical_structural_support_proxy",
        },
        "latency_ms": 0.0,
        "error": None,
    }


def _fail(output: dict[str, Any], code: str, message: str, started: float) -> dict[str, Any]:
    output["reason_codes"] = [code, "LEXICAL_PROXY_LIMITATION"]
    output["error"] = message
    output["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return output


def _validate_retrieval(
    retrieval: Any, config: dict[str, Any]
) -> tuple[list[dict[str, Any]] | None, str | None, str | None]:
    if not isinstance(retrieval, dict):
        return None, "INPUT_SCHEMA_INVALID", "retrieval_result must be an object"
    if retrieval.get("retriever_version") != EXPECTED_RETRIEVER or retrieval.get("corpus_version") != EXPECTED_CORPUS:
        return None, "VERSION_MISMATCH", "retriever_version/corpus_version does not match frozen V1"
    if retrieval.get("error"):
        return None, "RETRIEVAL_ERROR", f"retrieval error: {retrieval.get('error')}"
    chunks = retrieval.get("ordered_top5_chunks")
    if not isinstance(chunks, list) or len(chunks) != config["expected_top_k"]:
        return None, "INPUT_SCHEMA_INVALID", "ordered_top5_chunks must contain exactly five chunks"
    required = {"rank", "source_id", "chunk_id", "score", "title", "url", "category", "text"}
    if any(
        not isinstance(chunk, dict)
        or not required.issubset(chunk)
        or not isinstance(chunk.get("text"), str)
        for chunk in chunks
    ):
        return None, "INPUT_SCHEMA_INVALID", "one or more chunks violate the frozen retrieval schema"
    if [chunk["rank"] for chunk in chunks] != [1, 2, 3, 4, 5] or len({chunk["chunk_id"] for chunk in chunks}) != 5:
        return None, "INPUT_SCHEMA_INVALID", "chunk ranks or IDs are invalid"
    return chunks, None, None


def evaluate_evidence(query: str, case_id: str, retrieval_result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate frozen Retriever V1 Top-5 without running retrieval or generation."""
    started = time.perf_counter()
    config = _config()
    output = _base(query, case_id, retrieval_result)
    if not isinstance(query, str) or not query.strip() or not isinstance(case_id, str) or not case_id.strip():
        return _fail(output, "INPUT_SCHEMA_INVALID", "query and case_id must be non-empty strings", started)
    chunks, code, message = _validate_retrieval(retrieval_result, config)
    if code:
        return _fail(output, code, message or code, started)
    assert chunks is not None
    usable = [chunk for chunk in chunks if len(clean_text(chunk["text"])) >= config["min_usable_text_chars"]]
    if not usable:
        return _fail(output, "NO_USABLE_EVIDENCE", "Top-5 contains no usable evidence text", started)
    points, optional = decompose_query(query, config["max_required_points"])
    output["optional_information"] = optional
    if not points:
        return _fail(output, "REQUIRED_POINT_PARSE_FAILED", "minimal core required points could not be parsed", started)

    spans = evidence_sentences(usable)
    document_blob = " ".join(f"{chunk['title']} {chunk['text']}" for chunk in usable)
    document_score = overlap_score(query, document_blob)
    query_entities = extract_entities(query)
    missing_entities = [entity for entity in query_entities if compact(entity) not in compact(document_blob)]
    point_rows: list[dict[str, Any]] = []
    all_requested: list[dict[str, str]] = []
    all_missing_attributes: list[dict[str, str]] = []
    supporting_chunks: set[str] = set()
    supporting_sources: set[str] = set()
    conflict_found = False
    temporal_unclear = False

    for point in points:
        ranked = sorted(
            ((overlap_score(point.text, span["text"]), span) for span in spans),
            key=lambda item: (-item[0], item[1]["chunk_id"], item[1]["span_id"]),
        )
        best = ranked[: config["max_support_spans_per_point"]]
        best_score = best[0][0] if best else 0.0
        attributes = list(point.requested_attributes)
        missing_attributes: list[str] = []
        conflicts: list[dict[str, Any]] = []
        for attribute in attributes:
            all_requested.append({"point_id": point.point_id, "attribute": attribute})
            matching = [
                span
                for score, span in ranked
                if score >= config["partial_point_score"]
                and evidence_has_attribute(attribute, span["text"], span["url"])
            ]
            if not matching:
                missing_attributes.append(attribute)
                all_missing_attributes.append({"point_id": point.point_id, "attribute": attribute})
            values = set().union(*(attribute_values(attribute, span["text"]) for span in matching[:4])) if matching else set()
            if attribute in {"DEADLINE", "TIME", "PRICE", "CONTACT"} and len(values) > 1:
                conflicts.append({"attribute": attribute, "values": sorted(values)})
            if attribute == "CURRENT_STATUS" and not any(
                re.search(r"(?:\u76ee\u524d|\u5f53\u524d|\u73b0\u884c|\u6700\u65b0|2026)", span["text"])
                for span in matching
            ):
                temporal_unclear = True
                if attribute not in missing_attributes:
                    missing_attributes.append(attribute)
                    all_missing_attributes.append({"point_id": point.point_id, "attribute": attribute})

        entity_ok = not missing_entities
        if conflicts:
            status = "CONFLICT"
            conflict_found = True
        elif (
            best_score >= config["supported_point_score"]
            and entity_ok
            and not missing_attributes
            and document_score >= config["document_relevance_score"]
        ):
            status = "SUPPORTED"
        elif best_score >= config["partial_point_score"] and entity_ok:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "NOT_SUPPORTED"
        support_spans = [
            {
                "span_id": span["span_id"],
                "chunk_id": span["chunk_id"],
                "source_id": span["source_id"],
                "score": round(score, 6),
                "text": span["text"][:400],
            }
            for score, span in best
            if score >= config["partial_point_score"]
        ]
        if status in {"SUPPORTED", "PARTIALLY_SUPPORTED"}:
            supporting_chunks.update(item["chunk_id"] for item in support_spans)
            supporting_sources.update(item["source_id"] for item in support_spans)
        point_rows.append(
            {
                "point_id": point.point_id,
                "text": point.text,
                "requested_attributes": attributes,
                "missing_requested_attributes": missing_attributes,
                "status": status,
                "best_support_score": round(best_score, 6),
                "support_spans": support_spans,
                "conflicts": conflicts,
            }
        )

    statuses = [point["status"] for point in point_rows]
    if conflict_found:
        decision = "INSUFFICIENT"
    elif statuses and all(status == "SUPPORTED" for status in statuses):
        decision = "SUFFICIENT"
    elif any(status in {"SUPPORTED", "PARTIALLY_SUPPORTED"} for status in statuses):
        decision = "PARTIAL"
    else:
        decision = "INSUFFICIENT"

    reasons = {"LEXICAL_PROXY_LIMITATION"}
    if decision == "SUFFICIENT":
        reasons.add("CORE_POINTS_SUPPORTED")
    if any(status in {"NOT_SUPPORTED", "CONFLICT"} for status in statuses):
        reasons.add("CORE_POINT_MISSING")
    if any(status == "PARTIALLY_SUPPORTED" for status in statuses):
        reasons.add("EVIDENCE_ONLY_PARTIAL")
    if all(status == "NOT_SUPPORTED" for status in statuses):
        reasons.add(
            "EVIDENCE_IRRELEVANT"
            if document_score < config["document_relevance_score"] or missing_entities
            else "SOURCE_SUPPORT_TOO_WEAK"
        )
    if all_missing_attributes:
        reasons.add("REQUESTED_ATTRIBUTE_MISSING")
    if conflict_found:
        reasons.add("EVIDENCE_CONFLICT")
    if temporal_unclear:
        reasons.add("TEMPORAL_SUPPORT_UNCLEAR")

    output.update(
        {
            "decision": decision,
            "policy_signal": POLICY_SIGNALS[decision],
            "required_points": point_rows,
            "supported_points": [p["point_id"] for p in point_rows if p["status"] == "SUPPORTED"],
            "partially_supported_points": [p["point_id"] for p in point_rows if p["status"] == "PARTIALLY_SUPPORTED"],
            "unsupported_points": [p["point_id"] for p in point_rows if p["status"] in {"NOT_SUPPORTED", "CONFLICT"}],
            "requested_attributes": all_requested,
            "missing_requested_attributes": all_missing_attributes,
            "supporting_chunk_ids": sorted(supporting_chunks),
            "supporting_source_ids": sorted(supporting_sources),
            "reason_codes": sorted(reasons),
            "diagnostics": {
                "semantic_entailment": False,
                "method": config["method"],
                "document_relevance_score": round(document_score, 6),
                "query_entities": list(query_entities),
                "missing_query_entities": missing_entities,
                "thresholds": {
                    "supported": config["supported_point_score"],
                    "partial": config["partial_point_score"],
                    "document_relevance": config["document_relevance_score"],
                },
                "usable_chunk_count": len(usable),
                "input_sha256": hashlib.sha256(
                    json.dumps(
                        {"query": query, "case_id": case_id, "chunks": chunks},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
            },
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    )
    return output
