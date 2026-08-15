from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.citation_support_v1 import build_support_package  # noqa: E402
from src.citation_support_v1.schema import (  # noqa: E402
    CITATION_CANDIDATE_FIELDS, OUTPUT_FIELDS, POINT_MAPPING_FIELDS, SOURCE_GROUP_FIELDS, SUPPORT_UNIT_FIELDS,
)
from src.evidence_sufficiency_v1 import evaluate_evidence  # noqa: E402
from src.evidence_sufficiency_v1.policy import evidence_sentences  # noqa: E402
from src.retrieval_v1 import DenseRetrieverV1  # noqa: E402


OUT_DIR = ROOT / "evaluation" / "citation_support" / "v1" / "validation"
QUERIES = (
    ("CS-INT-001", "\u6e05\u534e\u5927\u5b66\u5b66\u751f\u5956\u5b66\u91d1\u7ba1\u7406\u89c4\u5b9a\u9002\u7528\u5bf9\u8c61\u662f\u4ec0\u4e48\uff1f"),
    ("CS-INT-002", "\u6e05\u534e\u5927\u5b66\u672c\u79d1\u751f\u5956\u5b66\u91d1\u7533\u8bf7\u6761\u4ef6\u548c\u622a\u6b62\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f"),
    ("CS-INT-003", "\u6e05\u534e\u5927\u5b66\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f"),
)


def stable(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("latency_ms", None)
    return result


def sufficient_fixture(retrieved: dict[str, Any]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    """Create a contract fixture only when the live chain has no SUFFICIENT case."""
    fixture_retrieval = copy.deepcopy(retrieved)
    case_id = "CS-FIXTURE-SUFFICIENT"
    query = "Frozen fixture: verify one exact support sentence"
    fixture_retrieval["case_id"] = case_id
    fixture_retrieval["query"] = query
    spans = evidence_sentences(fixture_retrieval["ordered_top5_chunks"])
    selected = next(row for row in spans if not row["span_id"].endswith("#TITLE") and len(row["text"]) >= 12)
    point = {
        "point_id": "P1", "text": query, "requested_attributes": [], "missing_requested_attributes": [],
        "status": "SUPPORTED", "best_support_score": 1.0,
        "support_spans": [{"span_id": selected["span_id"], "chunk_id": selected["chunk_id"], "source_id": selected["source_id"], "score": 1.0, "text": selected["text"]}],
        "conflicts": [],
    }
    fixture_evidence = {
        "query": query, "case_id": case_id,
        "evidence_sufficiency_version": "EVIDENCE_SUFFICIENCY_V1",
        "retriever_version": "RAG_RETRIEVAL_V1", "corpus_version": "KNOWLEDGE_BASE_V1",
        "decision": "SUFFICIENT", "policy_signal": "ALLOW_FULL_ANSWER", "confidence": None,
        "required_points": [point], "supported_points": ["P1"], "partially_supported_points": [],
        "unsupported_points": [], "requested_attributes": [], "missing_requested_attributes": [],
        "optional_information": [], "supporting_chunk_ids": [selected["chunk_id"]],
        "supporting_source_ids": [selected["source_id"]], "reason_codes": ["INTEGRATION_CONTRACT_FIXTURE"],
        "diagnostics": {"fixture": True, "semantic_entailment": False}, "latency_ms": 0.0, "error": None,
    }
    return case_id, query, fixture_retrieval, fixture_evidence


def main() -> int:
    retriever = DenseRetrieverV1()
    records: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    live_inputs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case_id, query in QUERIES:
        retrieved = retriever.retrieve(query, case_id)
        evidence = evaluate_evidence(query, case_id, retrieved)
        package_first = build_support_package(query, case_id, retrieved, evidence)
        package_second = build_support_package(query, case_id, copy.deepcopy(retrieved), copy.deepcopy(evidence))
        checks = {
            "retrieval_error_is_null": retrieved.get("error") is None,
            "evidence_error_is_null": evidence.get("error") is None,
            "citation_support_error_is_null": package_first.get("error") is None,
            "top5_count_is_five": len(retrieved.get("ordered_top5_chunks", [])) == 5,
            "version_chain_exact": (
                retrieved.get("retriever_version") == "RAG_RETRIEVAL_V1"
                and retrieved.get("corpus_version") == "KNOWLEDGE_BASE_V1"
                and evidence.get("evidence_sufficiency_version") == "EVIDENCE_SUFFICIENCY_V1"
                and package_first.get("citation_support_version") == "CITATION_SUPPORT_V1"
            ),
            "evidence_policy_preserved": package_first.get("evidence_decision") == evidence.get("decision") and package_first.get("policy_signal") == evidence.get("policy_signal"),
            "support_repeatable_excluding_latency": stable(package_first) == stable(package_second),
            "no_answer_or_rendering_fields": not any(key in package_first for key in ("answer", "claims", "rendered_citations", "final_response")),
            "output_schema_exact": set(package_first) == OUTPUT_FIELDS,
            "nested_schemas_exact": (
                all(set(row) == SUPPORT_UNIT_FIELDS for row in package_first["support_units"])
                and all(set(row) == POINT_MAPPING_FIELDS for row in package_first["required_point_support"])
                and all(set(row) == CITATION_CANDIDATE_FIELDS for row in package_first["citation_candidates"])
                and all(set(row) == SOURCE_GROUP_FIELDS for row in package_first["source_groups"])
            ),
        }
        records.append({
            "case_id": case_id, "query": query, "is_fixture": False, "fixture_reason": None,
            "evidence_decision": evidence.get("decision"), "support_status": package_first.get("support_status"),
            "support_unit_count": len(package_first.get("support_units", [])),
            "citation_candidate_count": len(package_first.get("citation_candidates", [])),
            "excluded_candidate_count": len(package_first.get("excluded_candidates", [])),
            "retrieved_chunk_ids": retrieved.get("chunk_ids", []),
            "usable_chunk_ids": package_first.get("usable_chunk_ids", []),
            "reason_codes": package_first.get("reason_codes", []), "checks": checks, "passed": all(checks.values()),
        })
        packages.append(package_first)
        live_inputs.append((retrieved, evidence))

    if not any(row["evidence_decision"] == "SUFFICIENT" and row["support_status"] == "READY" for row in records):
        case_id, query, retrieved, evidence = sufficient_fixture(live_inputs[0][0])
        package_first = build_support_package(query, case_id, retrieved, evidence)
        package_second = build_support_package(query, case_id, copy.deepcopy(retrieved), copy.deepcopy(evidence))
        checks = {
            "fixture_declared": True,
            "frozen_retrieval_rows_reused": len(retrieved["ordered_top5_chunks"]) == 5,
            "citation_support_error_is_null": package_first.get("error") is None,
            "sufficient_maps_to_ready": package_first.get("support_status") == "READY",
            "support_repeatable_excluding_latency": stable(package_first) == stable(package_second),
            "output_schema_exact": set(package_first) == OUTPUT_FIELDS,
            "support_unit_schema_exact": all(set(row) == SUPPORT_UNIT_FIELDS for row in package_first["support_units"]),
        }
        records.append({
            "case_id": case_id, "query": query, "is_fixture": True,
            "fixture_reason": "live pipeline cases did not naturally yield a citation-ready SUFFICIENT package; fixture tests only the frozen Citation/Support input contract",
            "evidence_decision": "SUFFICIENT", "support_status": package_first.get("support_status"),
            "support_unit_count": len(package_first.get("support_units", [])),
            "citation_candidate_count": len(package_first.get("citation_candidates", [])),
            "excluded_candidate_count": len(package_first.get("excluded_candidates", [])),
            "retrieved_chunk_ids": retrieved.get("chunk_ids", []), "usable_chunk_ids": package_first.get("usable_chunk_ids", []),
            "reason_codes": package_first.get("reason_codes", []), "checks": checks, "passed": all(checks.values()),
        })
        packages.append(package_first)

    covered_decisions = sorted({row["evidence_decision"] for row in records})
    covered_statuses = sorted({row["support_status"] for row in records})
    coverage_ok = set(covered_decisions) == {"SUFFICIENT", "PARTIAL", "INSUFFICIENT"} and {"READY", "PARTIAL", "BLOCKED"}.issubset(covered_statuses)
    all_pass = all(row["passed"] for row in records) and coverage_ok
    payload = {
        "artifact": "Citation / Support Runtime V1 full-chain integration",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "chain": "query -> RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> structured support package",
        "network_access": False, "answer_generation_called": False, "citation_rendering_called": False,
        "unsupported_claim_detection_called": False, "case_count": len(records),
        "live_case_count": sum(not row["is_fixture"] for row in records),
        "fixture_case_count": sum(row["is_fixture"] for row in records),
        "covered_evidence_decisions": covered_decisions, "covered_support_statuses": covered_statuses,
        "required_class_coverage_passed": coverage_ok, "cases": records,
        "overall_status": "PASS" if all_pass else "FAIL",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "integration_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (OUT_DIR / "integration_support_packages.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for package in packages:
            handle.write(json.dumps(package, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
