from __future__ import annotations

import json
from typing import Any

from src.citation_support_v1.schema import (
    CITATION_CANDIDATE_FIELDS,
    OUTPUT_FIELDS as CITATION_OUTPUT_FIELDS,
    POINT_MAPPING_FIELDS,
    SOURCE_GROUP_FIELDS,
    SUPPORT_UNIT_FIELDS,
)

from .schema import (
    EXPECTED_CITATION_SUPPORT,
    EXPECTED_CORPUS,
    EXPECTED_EVIDENCE,
    EXPECTED_RETRIEVER,
)


def validate_support_package(
    query: Any,
    case_id: Any,
    package: Any,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not isinstance(query, str) or not query.strip() or not isinstance(case_id, str) or not case_id.strip():
        return None, "INPUT_SCHEMA_INVALID", "query and case_id must be non-empty strings"
    if not isinstance(package, dict) or set(package) != CITATION_OUTPUT_FIELDS:
        return None, "INPUT_SCHEMA_INVALID", "support_package violates the frozen Citation Support V1 top-level schema"
    if (
        package.get("citation_support_version") != EXPECTED_CITATION_SUPPORT
        or package.get("evidence_sufficiency_version") != EXPECTED_EVIDENCE
        or package.get("retriever_version") != EXPECTED_RETRIEVER
        or package.get("corpus_version") != EXPECTED_CORPUS
    ):
        return None, "VERSION_MISMATCH", "support package versions do not match the frozen runtime chain"
    if package.get("query") != query or package.get("case_id") != case_id:
        return None, "INPUT_SCHEMA_INVALID", "query/case_id differs from the Citation Support package"
    if package.get("error") is not None:
        return None, "UPSTREAM_BLOCKED", "Citation Support package contains an upstream error"
    status = package.get("support_status")
    if status not in {"READY", "PARTIAL", "BLOCKED"}:
        return None, "INPUT_SCHEMA_INVALID", "support_status is invalid"
    if not isinstance(package.get("support_units"), list) or not isinstance(package.get("required_point_support"), list):
        return None, "INPUT_SCHEMA_INVALID", "support units and required-point mappings must be lists"
    if any(not isinstance(row, dict) or set(row) != SUPPORT_UNIT_FIELDS for row in package["support_units"]):
        return None, "INPUT_SCHEMA_INVALID", "a support unit violates the frozen Citation Support schema"
    if any(not isinstance(row, dict) or set(row) != POINT_MAPPING_FIELDS for row in package["required_point_support"]):
        return None, "INPUT_SCHEMA_INVALID", "a required-point mapping violates the frozen Citation Support schema"
    if any(not isinstance(row, dict) or set(row) != CITATION_CANDIDATE_FIELDS for row in package["citation_candidates"]):
        return None, "INPUT_SCHEMA_INVALID", "a citation candidate violates the frozen Citation Support schema"
    if any(not isinstance(row, dict) or set(row) != SOURCE_GROUP_FIELDS for row in package["source_groups"]):
        return None, "INPUT_SCHEMA_INVALID", "a source group violates the frozen Citation Support schema"

    units = package["support_units"]
    mappings = package["required_point_support"]
    unit_ids = [row.get("support_unit_id") for row in units]
    point_ids = [row.get("point_id") for row in mappings]
    if any(not isinstance(value, str) or not value for value in unit_ids + point_ids):
        return None, "INPUT_SCHEMA_INVALID", "support-unit and required-point IDs must be non-empty strings"
    if len(unit_ids) != len(set(unit_ids)) or len(point_ids) != len(set(point_ids)):
        return None, "INPUT_SCHEMA_INVALID", "support-unit and required-point IDs must be unique"
    unit_map = {row["support_unit_id"]: row for row in units}
    point_map = {row["point_id"]: row for row in mappings}
    usable_unit_ids = set(unit_map)
    usable_source_ids = {row["source_id"] for row in units}
    if set(package["usable_chunk_ids"]) != {row["chunk_id"] for row in units}:
        return None, "INVALID_SUPPORT_REFERENCE", "usable_chunk_ids differs from support units"
    if set(package["usable_source_ids"]) != usable_source_ids:
        return None, "INVALID_SOURCE_REFERENCE", "usable_source_ids differs from support units"
    for unit in units:
        if not isinstance(unit["source_id"], str) or not unit["source_id"]:
            return None, "INVALID_SOURCE_REFERENCE", "a support unit has an invalid source ID"
        if not isinstance(unit["required_point_ids"], list) or any(point not in point_map for point in unit["required_point_ids"]):
            return None, "INVALID_SUPPORT_REFERENCE", "a support unit references an unknown required point"
        if not isinstance(unit["span_text"], str) or not unit["span_text"].strip():
            return None, "NO_SUPPORTED_CONTENT", "a support unit has empty span text"
    for mapping in mappings:
        ids = mapping["support_unit_ids"]
        if not isinstance(ids, list) or any(value not in usable_unit_ids for value in ids):
            return None, "INVALID_SUPPORT_REFERENCE", "a required point references an unknown support unit"
        expected_sources = {unit_map[value]["source_id"] for value in ids}
        if set(mapping["source_ids"]) != expected_sources:
            return None, "INVALID_SOURCE_REFERENCE", "required-point sources differ from mapped support units"
        if any(mapping["point_id"] not in unit_map[value]["required_point_ids"] for value in ids):
            return None, "INVALID_SUPPORT_REFERENCE", "required-point/support-unit mapping is not bidirectional"

    decision = package.get("evidence_decision")
    if status == "READY":
        if decision != "SUFFICIENT" or not units or not mappings or any(
            row["mapping_status"] != "SUPPORTED" or not row["support_unit_ids"] for row in mappings
        ):
            return None, "NO_SUPPORTED_CONTENT", "READY package lacks complete validated support"
    elif status == "PARTIAL":
        allowed = [row for row in mappings if row["mapping_status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}]
        if decision != "PARTIAL" or not units or not allowed or any(not row["support_unit_ids"] for row in allowed):
            return None, "NO_SUPPORTED_CONTENT", "PARTIAL package lacks allowed validated support"
        if any(row["mapping_status"] == "UNSUPPORTED" and row["support_unit_ids"] for row in mappings):
            return None, "PARTIAL_SCOPE_VIOLATION", "unsupported PARTIAL point exposes support units"
    else:
        if units or package["citation_candidates"] or package["source_groups"] or package["usable_chunk_ids"] or package["usable_source_ids"]:
            return None, "UPSTREAM_BLOCKED", "BLOCKED package exposes answer-usable support"

    canonical = json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "unit_map": unit_map,
        "point_map": point_map,
        "canonical_package": canonical,
    }, None, None
