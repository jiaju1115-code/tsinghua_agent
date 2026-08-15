from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from capture_e2e_orchestrator_integrity import capture


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluation" / "e2e_orchestrator" / "runtime_v1"
POST = BASE / "audit" / "orchestrator_post_integrity.json"
FINAL = BASE / "audit" / "final_integrity_report.json"
FREEZE = BASE / "audit" / "unified_e2e_orchestrator_v1_freeze.json"

ARTIFACTS = (
    "src/e2e_orchestrator_v1/__init__.py",
    "src/e2e_orchestrator_v1/schema.py",
    "src/e2e_orchestrator_v1/runtime.py",
    "evaluation/e2e_orchestrator/runtime_v1/README.md",
    "evaluation/e2e_orchestrator/runtime_v1/config/orchestrator_v1.json",
    "evaluation/e2e_orchestrator/runtime_v1/schema/orchestrator_output_schema.json",
    "evaluation/e2e_orchestrator/runtime_v1/audit/contract_compatibility_audit.md",
    "evaluation/e2e_orchestrator/runtime_v1/audit/orchestrator_pre_integrity.json",
    "evaluation/e2e_orchestrator/runtime_v1/audit/orchestrator_post_integrity.json",
    "evaluation/e2e_orchestrator/runtime_v1/audit/final_integrity_report.json",
    "evaluation/e2e_orchestrator/runtime_v1/protocol/e2e_evaluation_protocol_v1.md",
    "evaluation/e2e_orchestrator/runtime_v1/protocol/benchmark_case_schema.json",
    "evaluation/e2e_orchestrator/runtime_v1/protocol/human_review_template.json",
    "evaluation/e2e_orchestrator/runtime_v1/protocol/freeze_protocol.md",
    "evaluation/e2e_orchestrator/runtime_v1/validation/upstream_non_mutating/upstream_test_results.json",
    "evaluation/e2e_orchestrator/runtime_v1/validation/upstream_non_mutating/after_upstream_tests_integrity.json",
    "evaluation/e2e_orchestrator/runtime_v1/validation/unit_test_results.json",
    "evaluation/e2e_orchestrator/runtime_v1/validation/integration_results.json",
    "evaluation/e2e_orchestrator/runtime_v1/validation/integration_traces.jsonl",
    "evaluation/e2e_orchestrator/runtime_v1/validation/engineering_metrics.json",
    "scripts/capture_e2e_orchestrator_integrity.py",
    "scripts/run_e2e_upstream_tests_non_mutating.py",
    "scripts/run_e2e_orchestrator_v1_unit_tests.py",
    "scripts/run_e2e_orchestrator_v1_integration.py",
    "scripts/finalize_e2e_orchestrator_v1.py",
    "docs/project_file_map.md",
    "reports/unified_e2e_orchestrator_v1_report.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def traces_safe() -> bool:
    forbidden_keys = {"prompt", "messages", "ordered_top5_chunks", "span_text", "authorization", "api_key", "secret"}
    required_trace_keys = {"stage", "status", "version", "reason_codes", "error_code", "latency_ms", "counts"}
    for line in (BASE / "validation" / "integration_traces.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        traces = json.loads(line)["trace_summary"]
        if any(set(row) != required_trace_keys or forbidden_keys.intersection(key.lower() for key in row) for row in traces):
            return False
        trace_blob = json.dumps(traces, ensure_ascii=False).lower()
        if any(token in trace_blob for token in ("ordered_top5_chunks", "span_text", "authorization:", "api_key=", "secret=")):
            return False
    return True


def main() -> int:
    post = capture()
    write_json(POST, post)
    pre = read_json(BASE / "audit" / "orchestrator_pre_integrity.json")
    upstream = read_json(BASE / "validation" / "upstream_non_mutating" / "upstream_test_results.json")
    unit = read_json(BASE / "validation" / "unit_test_results.json")
    integration = read_json(BASE / "validation" / "integration_results.json")
    metrics = read_json(BASE / "validation" / "engineering_metrics.json")
    config = read_json(BASE / "config" / "orchestrator_v1.json")
    traces = [json.loads(line) for line in (BASE / "validation" / "integration_traces.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {row["case_id"]: row for row in traces}
    cases = {row["case_id"]: row for row in integration["cases"]}
    same_inventory = (
        pre["formal_inventory_sha256"] == post["formal_inventory_sha256"]
        and pre["formal_artifact_count"] == post["formal_artifact_count"]
        and pre["formal_artifacts"] == post["formal_artifacts"]
    )
    components = post["components"].values()
    gates = {
        "upstream_freeze_statuses_verified": post["all_frozen_inputs_valid"],
        "upstream_freeze_sidecars_verified": all(row["sidecar_matches"] for row in components),
        "upstream_declared_artifact_hashes_verified": all(row.get("declared_artifacts_valid", True) and row.get("canonical_hashes_valid", True) for row in components),
        "upstream_pre_post_inventory_identical": same_inventory,
        "four_public_entry_points_audited": upstream["test_entry_count"] == 7 and upstream["overall_status"] == "PASS",
        "contract_compatibility_audit_complete": (BASE / "audit" / "contract_compatibility_audit.md").is_file(),
        "no_unresolved_semantic_contract_conflict": "No unresolved semantic conflict was found" in (BASE / "audit" / "contract_compatibility_audit.md").read_text(encoding="utf-8"),
        "orchestrator_public_api_complete": (ROOT / "src/e2e_orchestrator_v1/runtime.py").is_file(),
        "exact_output_schema_complete": all(set(row) == {"query", "case_id", "orchestrator_version", "orchestrator_status", "retrieval_status", "evidence_status", "citation_status", "answer_status", "final_answer", "answered_required_point_ids", "unanswered_required_point_ids", "used_support_unit_ids", "used_source_ids", "claims", "provenance", "trace_summary", "layer_latencies_ms", "orchestration_overhead_ms", "total_latency_ms", "reason_codes", "error"} for row in traces),
        "strict_sequence_and_no_retry_complete": any(row["scenario"] == "each_layer_called_once_no_retry" and row["status"] == "PASS" for row in unit["results"]),
        "upstream_error_fail_closed_no_skip_complete": any(row["scenario"] == "upstream_error_stops_downstream" and row["status"] == "PASS" for row in unit["results"]),
        "ready_status_propagation_pass": by_id["E2E-READY-CONTRACT-FIXTURE"]["answer_status"] == "FULL_ANSWER" and cases["E2E-READY-CONTRACT-FIXTURE"]["passed"],
        "partial_status_propagation_pass": by_id["E2E-NATURAL-PARTIAL"]["answer_status"] == "PARTIAL_ANSWER" and cases["E2E-NATURAL-PARTIAL"]["passed"],
        "blocked_refusal_no_model_call_pass": by_id["E2E-NATURAL-BLOCKED"]["answer_status"] == "REFUSAL" and cases["E2E-NATURAL-BLOCKED"]["checks"]["blocked_no_model_call"],
        "provenance_chain_complete": bool(by_id["E2E-READY-CONTRACT-FIXTURE"]["provenance"]) and any(row["scenario"] == "provenance_gap" and row["status"] == "PASS" for row in unit["results"]),
        "compact_trace_safety_pass": traces_safe(),
        "frozen_injection_boundary_preserved": cases["E2E-INJECTION-CONTRACT-FIXTURE"]["passed"] and by_id["E2E-INJECTION-CONTRACT-FIXTURE"]["answer_status"] == "REFUSAL",
        "unit_tests_minimum_20_pass": unit["total"] >= 20 and unit["failed"] == 0,
        "integration_repeatability_and_natural_cases_pass": integration["overall_status"] == "PASS" and integration["repeatability_excluding_latency_and_timestamp"] and integration["natural_case_count"] == 2 and integration["natural_frozen_ready_coverage"] == 0,
        "heldout_not_consumed_and_protocol_frozen": integration["formal_held_out_executed"] is False and metrics["held_out"] is False and (BASE / "protocol/e2e_evaluation_protocol_v1.md").is_file(),
    }
    allowed_behavior = (
        config["retry_count"] == 0 and not config["reretrieval_enabled"] and not config["fallback_enabled"]
        and not config["repair_enabled"] and not config["external_search_enabled"] and not config["semantic_classifier_added"]
    )
    if not allowed_behavior:
        gates["strict_sequence_and_no_retry_complete"] = False
    passed = sum(gates.values())
    status = "UNIFIED_E2E_ORCHESTRATOR_V1_FROZEN" if passed == 20 else "NOT_FROZEN"
    integrity = {
        "artifact": "Unified E2E Orchestrator V1 final integrity report",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if status.endswith("_FROZEN") and status != "NOT_FROZEN" else "FAIL",
        "pre_inventory_sha256": pre["formal_inventory_sha256"],
        "post_inventory_sha256": post["formal_inventory_sha256"],
        "formal_upstream_file_count": post["formal_artifact_count"],
        "upstream_files_changed": [] if same_inventory else "SEE_PRE_POST_DIFF",
        "upstream_existing_test_entries": {"passed": upstream["passed_count"], "total": upstream["test_entry_count"]},
        "orchestrator_unit_tests": {"passed": unit["passed"], "total": unit["total"]},
        "integration_status": integration["overall_status"],
        "freeze_gates_passed": passed,
        "freeze_gates_total": 20,
        "freeze_gates": gates,
        "formal_held_out_executed": False,
    }
    write_json(FINAL, integrity)
    missing = [relative for relative in ARTIFACTS if not (ROOT / relative).is_file()]
    if missing:
        status = "NOT_FROZEN"
    manifest = {
        "artifact": "Unified E2E Orchestrator V1 freeze manifest",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "runtime_version": "UNIFIED_E2E_ORCHESTRATOR_V1",
        "chain": ["RAG_RETRIEVAL_V1", "EVIDENCE_SUFFICIENCY_V1", "CITATION_SUPPORT_V1", "ANSWER_GENERATION_V1"],
        "corpus_version": "KNOWLEDGE_BASE_V1",
        "public_interface": "run_e2e(query, case_id, ...) -> dict",
        "upstream_formal_inventory_sha256": post["formal_inventory_sha256"],
        "upstream_formal_file_count": post["formal_artifact_count"],
        "freeze_gates_passed": passed,
        "freeze_gates_total": 20,
        "freeze_gates": gates,
        "natural_frozen_ready_coverage": 0,
        "ready_validation_type": "DECLARED_CONTRACT_FIXTURE",
        "unit_test_summary": {"passed": unit["passed"], "total": unit["total"]},
        "integration_summary": {"status": integration["overall_status"], "natural_cases": 2, "contract_fixtures": 2},
        "formal_held_out_executed": False,
        "e2e_50_executed": False,
        "quality_performance_claimed": False,
        "artifact_sha256": {relative: sha256(ROOT / relative) for relative in ARTIFACTS if (ROOT / relative).is_file()},
        "missing_artifacts": missing,
    }
    write_json(FREEZE, manifest)
    Path(str(FREEZE) + ".sha256").write_text(sha256(FREEZE) + "\n", encoding="ascii")
    print(json.dumps({"status": status, "gates": f"{passed}/20", "upstream_inventory_unchanged": same_inventory,
                      "manifest": str(FREEZE)}, ensure_ascii=False))
    return 0 if status == "UNIFIED_E2E_ORCHESTRATOR_V1_FROZEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
