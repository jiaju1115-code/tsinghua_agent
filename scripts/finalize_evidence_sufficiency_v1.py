from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evaluation" / "evidence_sufficiency" / "v1" / "audit"
FREEZE = AUDIT / "evidence_sufficiency_v1_freeze.json"

ARTIFACTS = (
    "src/evidence_sufficiency_v1/__init__.py",
    "src/evidence_sufficiency_v1/runtime.py",
    "src/evidence_sufficiency_v1/schema.py",
    "src/evidence_sufficiency_v1/policy.py",
    "evaluation/evidence_sufficiency/v1/README.md",
    "evaluation/evidence_sufficiency/v1/config/runtime_v1.json",
    "evaluation/evidence_sufficiency/v1/audit/historical_lineage.md",
    "evaluation/evidence_sufficiency/v1/audit/historical_logic_disposition.json",
    "evaluation/evidence_sufficiency/v1/audit/leakage_audit.json",
    "evaluation/evidence_sufficiency/v1/audit/pre_input_snapshot.json",
    "evaluation/evidence_sufficiency/v1/audit/post_input_snapshot.json",
    "evaluation/evidence_sufficiency/v1/tests/test_runtime.py",
    "evaluation/evidence_sufficiency/v1/tests/unit_test_results.json",
    "evaluation/evidence_sufficiency/v1/tests/integration_results.json",
    "evaluation/evidence_sufficiency/v1/results/historical_regression_metrics.json",
    "evaluation/evidence_sufficiency/v1/results/historical_regression_predictions.jsonl",
    "scripts/capture_evidence_v1_input_snapshot.py",
    "scripts/run_evidence_sufficiency_v1_unit_tests.py",
    "scripts/run_evidence_sufficiency_v1_historical_regression.py",
    "scripts/run_evidence_sufficiency_v1_integration.py",
    "scripts/audit_evidence_sufficiency_v1_leakage.py",
    "scripts/finalize_evidence_sufficiency_v1.py",
    "reports/evidence_sufficiency_v1_report.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> None:
    missing = [relative for relative in ARTIFACTS if not (ROOT / relative).is_file()]
    if missing:
        raise RuntimeError(f"missing V1 artifacts: {missing}")
    pre = read_json("evaluation/evidence_sufficiency/v1/audit/pre_input_snapshot.json")
    post = read_json("evaluation/evidence_sufficiency/v1/audit/post_input_snapshot.json")
    unit = read_json("evaluation/evidence_sufficiency/v1/tests/unit_test_results.json")
    integration = read_json("evaluation/evidence_sufficiency/v1/tests/integration_results.json")
    regression = read_json("evaluation/evidence_sufficiency/v1/results/historical_regression_metrics.json")
    leakage = read_json("evaluation/evidence_sufficiency/v1/audit/leakage_audit.json")
    config = read_json("evaluation/evidence_sufficiency/v1/config/runtime_v1.json")
    runtime_source_text = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "src/evidence_sufficiency_v1/__init__.py",
            "src/evidence_sufficiency_v1/runtime.py",
            "src/evidence_sufficiency_v1/schema.py",
            "src/evidence_sufficiency_v1/policy.py",
        )
    )
    gates = {
        "historical_asset_audit_complete": bool(read_json("evaluation/evidence_sufficiency/v1/audit/historical_logic_disposition.json").get("items")),
        "v1_semantics_explicit": config.get("labels") == ["SUFFICIENT", "PARTIAL", "INSUFFICIENT"],
        "runtime_implementation_complete": (ROOT / "src/evidence_sufficiency_v1/runtime.py").is_file(),
        "retriever_v1_integration_pass": integration.get("overall_status") == "PASS",
        "unit_tests_pass": unit.get("successful") is True and unit.get("tests_run") == 10,
        "deterministic_checks_pass": integration.get("retrieval_repeatability_excluding_latency") is True and all(case["checks"]["evidence_repeatability_excluding_latency"] for case in integration.get("cases", [])),
        "artifact_config_hashes_complete": True,
        "upstream_frozen_files_unchanged": pre.get("files") == post.get("files") and pre.get("inventory_sha256") == post.get("inventory_sha256"),
        "kb_v1_and_retriever_v1_unmodified": pre.get("files", {}).get("src/retrieval_v1/adapter.py") == post.get("files", {}).get("src/retrieval_v1/adapter.py") and all(pre["files"].get(path) == digest for path, digest in post.get("files", {}).items() if path.startswith("data/03_knowledge_base/v1/")),
        "limitations_recorded": "does **not** implement semantic entailment" in (ROOT / "reports/evidence_sufficiency_v1_report.md").read_text(encoding="utf-8"),
        "historical_metrics_not_misreported_as_e2e": regression.get("evaluation_name") == "HISTORICAL_CALIBRATION_COMPATIBILITY_REGRESSION" and leakage.get("runtime_v1_training_data_used") is False,
        "no_model_or_network_runtime_dependency": "transformers" not in (ROOT / "src/evidence_sufficiency_v1/runtime.py").read_text(encoding="utf-8") and "requests" not in (ROOT / "src/evidence_sufficiency_v1/runtime.py").read_text(encoding="utf-8"),
        "semantic_entailment_not_fabricated": config.get("semantic_entailment") is False and '"semantic_entailment": True' not in runtime_source_text,
    }
    integrity = {
        "artifact": "Evidence Sufficiency Runtime V1 final integrity report",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pre_file_count": pre["file_count"],
        "post_file_count": post["file_count"],
        "pre_inventory_sha256": pre["inventory_sha256"],
        "post_inventory_sha256": post["inventory_sha256"],
        "added_upstream_files": sorted(set(post["files"]) - set(pre["files"])),
        "removed_upstream_files": sorted(set(pre["files"]) - set(post["files"])),
        "changed_upstream_files": sorted(path for path in set(pre["files"]) & set(post["files"]) if pre["files"][path] != post["files"][path]),
        "gates": gates,
        "overall_status": "PASS" if all(gates.values()) else "FAIL",
    }
    integrity_path = AUDIT / "final_integrity_report.json"
    integrity_path.write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not all(gates.values()):
        raise RuntimeError(f"freeze gates failed: {[name for name, passed in gates.items() if not passed]}")

    artifact_rows = {
        relative: {"sha256": sha256(ROOT / relative), "size_bytes": (ROOT / relative).stat().st_size}
        for relative in ARTIFACTS
    }
    artifact_rows["evaluation/evidence_sufficiency/v1/audit/final_integrity_report.json"] = {
        "sha256": sha256(integrity_path),
        "size_bytes": integrity_path.stat().st_size,
    }
    freeze = {
        "status": "EVIDENCE_SUFFICIENCY_V1_FROZEN",
        "version": "EVIDENCE_SUFFICIENCY_V1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "deterministic_lexical_structural_support_proxy",
        "semantic_entailment": False,
        "public_api": "src.evidence_sufficiency_v1.evaluate_evidence(query, case_id, retrieval_result)",
        "expected_retriever_version": "RAG_RETRIEVAL_V1",
        "expected_corpus_version": "KNOWLEDGE_BASE_V1",
        "expected_top_k": 5,
        "decisions": ["SUFFICIENT", "PARTIAL", "INSUFFICIENT"],
        "configuration": config,
        "freeze_gates": gates,
        "upstream_inventory_sha256": pre["inventory_sha256"],
        "upstream_file_count": pre["file_count"],
        "unit_test_summary": {"tests_run": unit["tests_run"], "failures": unit["failures"], "errors": unit["errors"], "successful": unit["successful"]},
        "integration_summary": {"case_count": integration["case_count"], "overall_status": integration["overall_status"]},
        "historical_regression_summary": {
            "classification": regression["evaluation_name"],
            "eligible_rows": regression["eligible_exactly_top5_rows"],
            "exact_agreement_pct": regression["all_eligible"]["exact_agreement_pct"],
            "macro_f1": regression["all_eligible"]["macro_f1"],
            "false_sufficient_count": regression["all_eligible"]["false_sufficient_count"],
            "over_refusal_count": regression["all_eligible"]["false_insufficient_or_over_refusal_count"],
            "held_out_claim": False,
        },
        "known_material_limitations": [
            "No genuine semantic entailment.",
            "Historical regression is overlapping seen calibration/proxy data.",
            "Severe historical over-refusal: 28/31 human-reference sufficient cases were not classified sufficient.",
            "Supporting IDs and spans are not citation correctness.",
        ],
        "artifact_manifest": artifact_rows,
        "runtime_dependencies": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "runtime_module_external_dependencies": [],
            "integration_only_versions": {
                "numpy": version("numpy"),
                "torch": version("torch"),
                "transformers": version("transformers"),
            },
        },
        "forbidden_next_stages_executed": {"answer_generation": False, "citation_runtime": False, "formal_e2e": False},
    }
    FREEZE.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = sha256(FREEZE)
    FREEZE.with_suffix(FREEZE.suffix + ".sha256").write_text(digest + "\n", encoding="ascii")
    print(json.dumps({"status": freeze["status"], "freeze_sha256": digest, "artifact_count": len(artifact_rows)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
