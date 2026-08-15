from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .normalization import canonicalize, compact_length, is_only_punctuation, locate_span, mergeable_gap
from .policy import support_gate
from .schema import (
    EVIDENCE_DECISIONS,
    EVIDENCE_POINT_STATUSES,
    EXPECTED_CORPUS,
    EXPECTED_EVIDENCE,
    EXPECTED_POLICY_SIGNALS,
    EXPECTED_RETRIEVER,
    REQUIRED_CHUNK_FIELDS,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_RETRIEVAL_FIELDS,
    VERSION,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "evaluation" / "citation_support" / "v1" / "config" / "citation_support_v1.json"


def _config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}-{digest}"


def _base(query: Any, case_id: Any, retrieval: Any, evidence: Any) -> dict[str, Any]:
    return {
        "query": query,
        "case_id": case_id,
        "citation_support_version": VERSION,
        "evidence_sufficiency_version": evidence.get("evidence_sufficiency_version") if isinstance(evidence, dict) else None,
        "retriever_version": retrieval.get("retriever_version") if isinstance(retrieval, dict) else None,
        "corpus_version": retrieval.get("corpus_version") if isinstance(retrieval, dict) else None,
        "evidence_decision": evidence.get("decision") if isinstance(evidence, dict) else None,
        "policy_signal": evidence.get("policy_signal") if isinstance(evidence, dict) else None,
        "support_status": "BLOCKED",
        "required_point_support": [],
        "support_units": [],
        "citation_candidates": [],
        "excluded_candidates": [],
        "source_groups": [],
        "usable_chunk_ids": [],
        "usable_source_ids": [],
        "reason_codes": [],
        "diagnostics": {
            "semantic_entailment": False,
            "claim_evaluation": False,
            "method": "deterministic_provenance_and_span_integrity",
        },
        "latency_ms": 0.0,
        "error": None,
    }


def _finish(output: dict[str, Any], started: float) -> dict[str, Any]:
    output["reason_codes"] = sorted(set(output["reason_codes"]))
    output["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return output


def _exclude(output: dict[str, Any], reason: str, **details: Any) -> None:
    row = {"reason_code": reason}
    row.update({key: value for key, value in details.items() if value is not None})
    output["excluded_candidates"].append(row)


def _fatal(output: dict[str, Any], started: float, reason: str, message: str) -> dict[str, Any]:
    output["reason_codes"].extend([reason, "SUPPORT_INTEGRITY_BLOCKED"])
    output["error"] = message
    _exclude(output, reason, detail=message)
    return _finish(output, started)


def _validate_inputs(
    query: Any,
    case_id: Any,
    retrieval: Any,
    evidence: Any,
    config: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]] | None, str | None, str | None]:
    if not isinstance(query, str) or not query.strip() or not isinstance(case_id, str) or not case_id.strip():
        return None, "INPUT_SCHEMA_INVALID", "query and case_id must be non-empty strings"
    if not isinstance(retrieval, dict) or not REQUIRED_RETRIEVAL_FIELDS.issubset(retrieval):
        return None, "INPUT_SCHEMA_INVALID", "retrieval_result violates the Retriever V1 contract"
    if not isinstance(evidence, dict) or not REQUIRED_EVIDENCE_FIELDS.issubset(evidence):
        return None, "INPUT_SCHEMA_INVALID", "evidence_result violates the Evidence Sufficiency V1 contract"
    if (
        retrieval.get("retriever_version") != EXPECTED_RETRIEVER
        or retrieval.get("corpus_version") != EXPECTED_CORPUS
        or evidence.get("evidence_sufficiency_version") != EXPECTED_EVIDENCE
        or evidence.get("retriever_version") != EXPECTED_RETRIEVER
        or evidence.get("corpus_version") != EXPECTED_CORPUS
    ):
        return None, "VERSION_MISMATCH", "upstream versions do not match the frozen V1 chain"
    if retrieval.get("query") != query or retrieval.get("case_id") != case_id or evidence.get("query") != query or evidence.get("case_id") != case_id:
        return None, "QUERY_CASE_MISMATCH", "query/case_id differs across the runtime chain"
    if retrieval.get("error") or evidence.get("error"):
        return None, "INPUT_SCHEMA_INVALID", "an upstream result contains an error"
    chunks = retrieval.get("ordered_top5_chunks")
    if not isinstance(chunks, list) or len(chunks) != config["expected_top_k"]:
        return None, "INPUT_SCHEMA_INVALID", "ordered_top5_chunks must contain exactly five rows"
    if any(not isinstance(row, dict) or not REQUIRED_CHUNK_FIELDS.issubset(row) for row in chunks):
        return None, "INPUT_SCHEMA_INVALID", "one or more retrieval chunks violate the frozen schema"
    if [row.get("rank") for row in chunks] != [1, 2, 3, 4, 5] or len({row.get("chunk_id") for row in chunks}) != 5:
        return None, "INPUT_SCHEMA_INVALID", "retrieval ranks or chunk IDs are invalid"
    if any(not isinstance(row.get("text"), str) or not isinstance(row.get("source_id"), str) for row in chunks):
        return None, "INPUT_SCHEMA_INVALID", "retrieval chunk text/source identifiers are invalid"
    if any(not row.get("source_id") or not isinstance(row.get("chunk_id"), str) or not row.get("chunk_id") for row in chunks):
        return None, "INPUT_SCHEMA_INVALID", "retrieval source/chunk identifiers must be non-empty strings"
    if evidence.get("decision") not in EVIDENCE_DECISIONS:
        return None, "INPUT_SCHEMA_INVALID", "Evidence decision is outside the frozen vocabulary"
    if evidence.get("policy_signal") != EXPECTED_POLICY_SIGNALS[evidence["decision"]]:
        return None, "POLICY_SIGNAL_MISMATCH", "Evidence decision and policy signal are inconsistent"
    points = evidence.get("required_points")
    if not isinstance(points, list) or not points:
        return None, "INPUT_SCHEMA_INVALID", "required_points must be a non-empty list"
    point_ids: set[str] = set()
    for point in points:
        if not isinstance(point, dict) or not {"point_id", "text", "status", "support_spans"}.issubset(point):
            return None, "INPUT_SCHEMA_INVALID", "a required point violates the Evidence schema"
        if not isinstance(point["point_id"], str) or not point["point_id"] or point["point_id"] in point_ids:
            return None, "INPUT_SCHEMA_INVALID", "required point IDs must be unique non-empty strings"
        point_ids.add(point["point_id"])
        if point["status"] not in EVIDENCE_POINT_STATUSES or not isinstance(point["support_spans"], list):
            return None, "INPUT_SCHEMA_INVALID", "required point status/support spans are invalid"
        for span in point["support_spans"]:
            if not isinstance(span, dict) or not {"span_id", "chunk_id", "source_id", "text"}.issubset(span):
                return None, "INPUT_SCHEMA_INVALID", "an Evidence support span violates the schema"
    expected_point_sets = {
        "supported_points": {row["point_id"] for row in points if row["status"] == "SUPPORTED"},
        "partially_supported_points": {row["point_id"] for row in points if row["status"] == "PARTIALLY_SUPPORTED"},
        "unsupported_points": {row["point_id"] for row in points if row["status"] in {"NOT_SUPPORTED", "CONFLICT"}},
    }
    for field, expected in expected_point_sets.items():
        value = evidence.get(field)
        if not isinstance(value, list) or len(value) != len(set(value)) or set(value) != expected:
            return None, "INPUT_SCHEMA_INVALID", f"Evidence {field} does not correspond to required-point IDs"
    chunk_map = {row["chunk_id"]: row for row in chunks}
    return chunk_map, None, None


def _source_class(source_id: str, config: dict[str, Any]) -> str:
    return "restricted" if any(source_id.startswith(prefix) for prefix in config["restricted_source_prefixes"]) else "public"


def _build_raw_units(
    output: dict[str, Any],
    evidence: dict[str, Any],
    chunk_map: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    units_by_key: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    integrity_blocked = False
    for point in evidence["required_points"]:
        point_id = point["point_id"]
        supported = point["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
        point_seen: set[tuple[str, int, int, str]] = set()
        for span in point["support_spans"]:
            details = {
                "point_id": point_id,
                "evidence_span_id": span.get("span_id"),
                "chunk_id": span.get("chunk_id"),
                "source_id": span.get("source_id"),
            }
            if not supported:
                _exclude(output, "EVIDENCE_NOT_SUPPORTED", **details)
                continue
            chunk = chunk_map.get(span.get("chunk_id"))
            if chunk is None:
                _exclude(output, "CHUNK_NOT_IN_RETRIEVAL", **details)
                integrity_blocked = True
                continue
            if span.get("source_id") != chunk["source_id"]:
                _exclude(output, "SOURCE_ID_MISMATCH", **details)
                integrity_blocked = True
                continue
            span_text = span.get("text")
            if not isinstance(span_text, str):
                _exclude(output, "SPAN_INVALID", **details)
                continue
            if str(span.get("span_id", "")).endswith("#TITLE") or is_only_punctuation(span_text) or compact_length(span_text) < config["minimum_compact_span_chars"]:
                _exclude(output, "SPAN_TOO_WEAK", **details)
                continue
            match = locate_span(chunk["text"], span_text)
            if match is None:
                _exclude(output, "SPAN_NOT_FOUND", **details)
                continue
            key = (chunk["chunk_id"], match.raw_start, match.raw_end, match.normalized_text)
            if key in point_seen:
                _exclude(output, "DUPLICATE_SUPPORT", **details)
                continue
            point_seen.add(key)
            if key not in units_by_key:
                source_class = _source_class(chunk["source_id"], config)
                units_by_key[key] = {
                    "required_point_ids": [],
                    "source_id": chunk["source_id"],
                    "chunk_id": chunk["chunk_id"],
                    "source_title": chunk["title"],
                    "source_url": chunk["url"],
                    "source_class": source_class,
                    "category": chunk["category"],
                    "span_text": match.raw_text,
                    "span_start": match.raw_start,
                    "span_end": match.raw_end,
                    "original_span_texts": [],
                    "normalized_span_text": match.normalized_text,
                    "normalization_reasons": list(match.normalization_reasons),
                    "support_role": "SUPPLEMENTARY",
                    "retriever_rank": chunk["rank"],
                    "evidence_span_ids": [],
                    "match_occurrence_count": match.occurrence_count,
                }
                if source_class == "restricted":
                    output["reason_codes"].append("RESTRICTED_METADATA_SANITIZED")
            unit = units_by_key[key]
            unit["required_point_ids"].append(point_id)
            unit["evidence_span_ids"].append(span["span_id"])
            unit["original_span_texts"].append(span_text)
    return list(units_by_key.values()), integrity_blocked


def _merge_adjacent(units: list[dict[str, Any]], chunk_map: dict[str, dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    ordered = sorted(units, key=lambda row: (row["retriever_rank"], row["chunk_id"], row["span_start"], row["span_end"]))
    merged: list[dict[str, Any]] = []
    merge_count = 0
    for unit in ordered:
        if merged and merged[-1]["chunk_id"] == unit["chunk_id"]:
            previous = merged[-1]
            raw = chunk_map[unit["chunk_id"]]["text"]
            gap = raw[previous["span_end"]:unit["span_start"]]
            merged_length = unit["span_end"] - previous["span_start"]
            if unit["span_start"] >= previous["span_end"] and mergeable_gap(gap, config["maximum_adjacent_gap_chars"]) and merged_length <= config["maximum_merged_span_chars"]:
                previous["span_end"] = unit["span_end"]
                previous["span_text"] = raw[previous["span_start"]:previous["span_end"]]
                previous["normalized_span_text"] = canonicalize(previous["span_text"])
                previous["required_point_ids"].extend(unit["required_point_ids"])
                previous["evidence_span_ids"].extend(unit["evidence_span_ids"])
                previous["original_span_texts"].extend(unit["original_span_texts"])
                previous["normalization_reasons"].extend(unit["normalization_reasons"])
                previous["normalization_reasons"].append("ADJACENT_SPANS_MERGED")
                previous["match_occurrence_count"] = max(previous["match_occurrence_count"], unit["match_occurrence_count"])
                merge_count += 1
                continue
        merged.append(unit)
    for unit in merged:
        for key in ("required_point_ids", "evidence_span_ids", "original_span_texts", "normalization_reasons"):
            unit[key] = sorted(set(unit[key]))
        unit["support_unit_id"] = _stable_id(
            "CSU", f"{unit['chunk_id']}|{unit['span_start']}|{unit['span_end']}|{unit['normalized_span_text']}"
        )
    return merged, merge_count


def _assign_roles(units: list[dict[str, Any]]) -> None:
    primary_seen: set[str] = set()
    for unit in units:
        if any(point_id not in primary_seen for point_id in unit["required_point_ids"]):
            unit["support_role"] = "PRIMARY"
            primary_seen.update(unit["required_point_ids"])


def _build_point_mapping(evidence: dict[str, Any], units: list[dict[str, Any]], output: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    by_point: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        for point_id in unit["required_point_ids"]:
            by_point[point_id].append(unit)
    mappings: list[dict[str, Any]] = []
    mapped = 0
    for point in evidence["required_points"]:
        point_units = sorted(by_point[point["point_id"]], key=lambda row: (row["retriever_rank"], row["support_unit_id"]))
        if point_units:
            mapped += 1
            mapping_status = "SUPPORTED" if point["status"] == "SUPPORTED" else "PARTIALLY_SUPPORTED"
            issue = None
        else:
            mapping_status = "UNSUPPORTED"
            issue = "REQUIRED_POINT_UNMAPPED" if point["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} else "EVIDENCE_NOT_SUPPORTED"
            if issue == "REQUIRED_POINT_UNMAPPED":
                _exclude(output, issue, point_id=point["point_id"])
        mappings.append({
            "point_id": point["point_id"],
            "point_text": point["text"],
            "evidence_point_status": point["status"],
            "mapping_status": mapping_status,
            "support_unit_ids": [unit["support_unit_id"] for unit in point_units],
            "source_ids": sorted({unit["source_id"] for unit in point_units}),
            "integrity_issue": issue,
        })
    return mappings, mapped


def _aggregate_sources(units: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        grouped[unit["source_id"]].append(unit)
    rows: list[dict[str, Any]] = []
    for source_id, source_units in grouped.items():
        first = min(source_units, key=lambda row: (row["retriever_rank"], row["chunk_id"]))
        point_ids = sorted({point_id for unit in source_units for point_id in unit["required_point_ids"]})
        unit_ids = [unit["support_unit_id"] for unit in sorted(source_units, key=lambda row: (row["retriever_rank"], row["span_start"], row["support_unit_id"]))]
        candidate_id = _stable_id("CSC", source_id + "|" + "|".join(unit_ids))
        rows.append({
            "citation_candidate_id": candidate_id,
            "source_id": source_id,
            "title": first["source_title"],
            "url": first["source_url"],
            "category": first["category"],
            "source_class": first["source_class"],
            "retriever_rank": min(unit["retriever_rank"] for unit in source_units),
            "required_point_ids": point_ids,
            "support_unit_ids": unit_ids,
            "chunk_ids": sorted({unit["chunk_id"] for unit in source_units}),
        })
    rows.sort(key=lambda row: (-len(row["required_point_ids"]), row["retriever_rank"], row["source_id"]))
    source_groups = [
        {
            "source_group_id": _stable_id("CSG", row["source_id"]),
            "source_id": row["source_id"],
            "title": row["title"],
            "url": row["url"],
            "category": row["category"],
            "source_class": row["source_class"],
            "retriever_rank": row["retriever_rank"],
            "required_point_ids": row["required_point_ids"],
            "support_unit_ids": row["support_unit_ids"],
            "chunk_ids": row["chunk_ids"],
        }
        for row in rows
    ]
    return rows, source_groups


def build_support_package(
    query: str,
    case_id: str,
    retrieval_result: dict[str, Any],
    evidence_result: dict[str, Any],
) -> dict[str, Any]:
    """Build citation-ready support provenance without retrieval or generation."""
    started = time.perf_counter()
    config = _config()
    output = _base(query, case_id, retrieval_result, evidence_result)
    chunk_map, code, message = _validate_inputs(query, case_id, retrieval_result, evidence_result, config)
    if code:
        return _fatal(output, started, code, message or code)
    assert chunk_map is not None

    retrieval_chunk_ids = set(chunk_map)
    retrieval_source_ids = {row["source_id"] for row in chunk_map.values()}
    evidence_chunk_ids = evidence_result["supporting_chunk_ids"]
    evidence_source_ids = evidence_result["supporting_source_ids"]
    if not isinstance(evidence_chunk_ids, list) or any(item not in retrieval_chunk_ids for item in evidence_chunk_ids):
        return _fatal(output, started, "CHUNK_NOT_IN_RETRIEVAL", "Evidence supporting_chunk_ids exceeds Retriever Top-5")
    if not isinstance(evidence_source_ids, list) or any(item not in retrieval_source_ids for item in evidence_source_ids):
        return _fatal(output, started, "SOURCE_ID_MISMATCH", "Evidence supporting_source_ids differs from Retriever Top-5")

    units, integrity_blocked = _build_raw_units(output, evidence_result, chunk_map, config)
    units, merge_count = _merge_adjacent(units, chunk_map, config)
    units.sort(key=lambda row: (row["retriever_rank"], row["chunk_id"], row["span_start"], row["support_unit_id"]))
    _assign_roles(units)
    mappings, mapped_count = _build_point_mapping(evidence_result, units, output)

    if evidence_result["decision"] == "INSUFFICIENT":
        for unit in units:
            _exclude(
                output,
                "EVIDENCE_DECISION_BLOCKED",
                support_unit_id=unit["support_unit_id"],
                chunk_id=unit["chunk_id"],
                source_id=unit["source_id"],
            )
        units = []
        mapped_count = 0
        for mapping in mappings:
            mapping["mapping_status"] = "UNSUPPORTED"
            mapping["support_unit_ids"] = []
            mapping["source_ids"] = []
            mapping["integrity_issue"] = "EVIDENCE_DECISION_BLOCKED"

    required_supported = sum(1 for point in evidence_result["required_points"] if point["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"})
    if evidence_result["decision"] == "SUFFICIENT" and mapped_count != len(evidence_result["required_points"]):
        integrity_blocked = True
    if evidence_result["decision"] == "PARTIAL" and mapped_count < required_supported and mapped_count == 0:
        integrity_blocked = True
    status, gate_reasons = support_gate(evidence_result["decision"], mapped_count, len(evidence_result["required_points"]), integrity_blocked)
    candidates, source_groups = _aggregate_sources(units) if status != "BLOCKED" else ([], [])
    if status == "BLOCKED":
        units = []
        for mapping in mappings:
            mapping["mapping_status"] = "UNSUPPORTED"
            mapping["support_unit_ids"] = []
            mapping["source_ids"] = []
            if mapping["integrity_issue"] is None:
                mapping["integrity_issue"] = "SUPPORT_INTEGRITY_BLOCKED"
    output.update({
        "support_status": status,
        "required_point_support": mappings,
        "support_units": units,
        "citation_candidates": candidates,
        "source_groups": source_groups,
        "usable_chunk_ids": sorted({unit["chunk_id"] for unit in units}),
        "usable_source_ids": sorted({unit["source_id"] for unit in units}),
    })
    output["reason_codes"].extend(gate_reasons)
    if merge_count:
        output["reason_codes"].append("ADJACENT_SUPPORT_MERGED")
    if output["excluded_candidates"]:
        output["reason_codes"].append("CANDIDATES_EXCLUDED")
    canonical_input = {
        "query": query,
        "case_id": case_id,
        "retrieval": {"versions": [retrieval_result["retriever_version"], retrieval_result["corpus_version"]], "chunks": retrieval_result["ordered_top5_chunks"]},
        "evidence": {key: evidence_result[key] for key in sorted(REQUIRED_EVIDENCE_FIELDS)},
    }
    output["diagnostics"].update({
        "top5_chunk_count": len(chunk_map),
        "required_point_count": len(evidence_result["required_points"]),
        "mapped_point_count": mapped_count,
        "support_unit_count": len(units),
        "citation_candidate_count": len(candidates),
        "excluded_candidate_count": len(output["excluded_candidates"]),
        "adjacent_merge_count": merge_count,
        "input_sha256": hashlib.sha256(json.dumps(canonical_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
    })
    output["excluded_candidates"].sort(key=lambda row: (row.get("point_id", ""), row.get("chunk_id", ""), row.get("evidence_span_id", ""), row["reason_code"]))
    return _finish(output, started)
