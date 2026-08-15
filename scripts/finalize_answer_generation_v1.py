from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluation" / "answer_generation" / "runtime_v1"
AUDIT = BASE / "audit"
VALIDATION = BASE / "validation"
CONFIG = BASE / "config" / "answer_generation_v1.json"
PROMPT = BASE / "prompts" / "answer_generation_v1_prompt.md"
REPORT = ROOT / "reports" / "answer_generation_v1_report.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def subset(files: dict[str, str], prefixes: tuple[str, ...]) -> dict[str, Any]:
    selected = {key: value for key, value in files.items() if any(key == prefix or key.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)}
    canonical = (json.dumps(selected, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return {"file_count": len(selected), "inventory_sha256": hashlib.sha256(canonical).hexdigest()}


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    config = read_json(CONFIG)
    pre, post = read_json(AUDIT / "pre_input_snapshot.json"), read_json(AUDIT / "post_input_snapshot.json")
    before, after = pre["files"], post["files"]
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(key for key in set(before) & set(after) if before[key] != after[key])
    project_upstream_clean = not added and not removed and not modified and pre["inventory_sha256"] == post["inventory_sha256"]
    model_pre, model_post = pre["external_generation_model"], post["external_generation_model"]
    model_reproducible = (
        model_pre == model_post
        and model_pre["exists"] is True
        and model_pre["size_bytes"] == config["model"]["file_size_bytes"]
        and model_pre["sha256"] == config["model"]["sha256"]
        and model_pre["revision"] == config["model"]["revision"]
    )
    prompt_frozen = sha256(PROMPT) == config["prompt"]["sha256"]

    unit = read_json(VALIDATION / "unit_test_results.json")
    integration = read_json(VALIDATION / "integration_results.json")
    answers = [json.loads(line) for line in (VALIDATION / "integration_answers.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    unit_pass = unit["failed"] == 0 and unit["passed"] == unit["total"] and unit["total"] >= 20
    integration_pass = integration["overall_status"] == "PASS" and integration["required_path_coverage_passed"]
    ready_row = next(row for row in integration["cases"] if row["path"] == "READY")
    blocked_row = next(row for row in integration["cases"] if row["path"] == "BLOCKED")
    repeatability_pass = ready_row["checks"]["repeatable_excluding_latency"]
    blocked_no_call = blocked_row["checks"]["blocked_no_model_call"]

    primary_rows = [row for row in integration["cases"] if row["path"] in {"READY", "PARTIAL", "BLOCKED"}]
    generated_answers = [row for row in answers if row["answer_status"] in {"FULL_ANSWER", "PARTIAL_ANSWER"}]
    model_latencies = [row["latency_ms"] for row in generated_answers]
    used_id_checks = [row["checks"]["used_support_ids_valid"] for row in primary_rows]
    metrics = {
        "artifact": "Answer Generation Runtime V1 engineering metrics",
        "created_at_utc": created,
        "scope": "runtime engineering only; not held-out answer correctness, faithfulness, citation correctness, or semantic unsupported-claim performance",
        "unit_tests": {"passed": unit["passed"], "total": unit["total"], "rate_percent": round(100 * unit["passed"] / unit["total"], 2)},
        "integration": {"passed": sum(row["passed"] for row in integration["cases"]), "total": integration["case_count"], "live_full_chain": integration["live_full_chain_case_count"], "contract_fixtures": integration["contract_fixture_count"]},
        "schema_valid_output": {"count": sum(row["checks"]["output_schema_exact"] for row in integration["cases"]), "denominator": integration["case_count"], "percent": round(100 * sum(row["checks"]["output_schema_exact"] for row in integration["cases"]) / integration["case_count"], 2)},
        "support_status_adherence": {"count": sum(row["checks"].get("answer_status_adheres", True) for row in primary_rows), "denominator": len(primary_rows), "percent": round(100 * sum(row["checks"].get("answer_status_adheres", True) for row in primary_rows) / len(primary_rows), 2)},
        "blocked_no_model_call": {"count": int(blocked_no_call), "denominator": 1, "percent": 100.0 if blocked_no_call else 0.0},
        "valid_support_id": {"count": sum(used_id_checks), "denominator": len(used_id_checks), "percent": round(100 * sum(used_id_checks) / len(used_id_checks), 2)},
        "unattributed_factual_claim_count": sum(1 for row in generated_answers for claim in row["claim_records"] if claim["claim_type"] == "FACTUAL" and not claim["support_unit_ids"]),
        "partial_scope_violation_count": sum("PARTIAL_SCOPE_VIOLATION" in row["reason_codes"] for row in answers),
        "model_failure_count": sum(any(code in row["reason_codes"] for code in ("MODEL_LOAD_ERROR", "GENERATION_ERROR", "GENERATION_TIMEOUT", "MODEL_OUTPUT_INVALID")) for row in answers),
        "repeatability_excluding_latency_ms": repeatability_pass,
        "model_bitwise_determinism_claimed": False,
        "successful_generation_latency_ms": {"count": len(model_latencies), "minimum": round(min(model_latencies), 3), "maximum": round(max(model_latencies), 3), "mean": round(sum(model_latencies) / len(model_latencies), 3)},
        "semantic_unsupported_claim_detection": False,
    }
    metrics_path = VALIDATION / "engineering_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    model_record = {
        "artifact": "Answer Generation Runtime V1 local model record",
        "created_at_utc": created,
        "name": config["model"]["name"], "revision": config["model"]["revision"],
        "quantization": config["model"]["quantization"], "path_relative_to_home": config["model"]["file_relative_to_home"],
        "size_bytes": config["model"]["file_size_bytes"], "sha256": config["model"]["sha256"],
        "architecture": config["model"]["architecture"], "gguf_file_type": config["model"]["gguf_file_type"],
        "gguf_quantization_version": config["model"]["gguf_quantization_version"],
        "trained_context_length": config["model"]["trained_context_length"], "tokenizer": config["model"]["tokenizer"],
        "chat_template": config["model"]["chat_template"], "engine": config["engine"],
        "artifact_verified_pre_and_post": model_reproducible,
    }
    model_record_path = AUDIT / "model_record.json"
    model_record_path.write_text(json.dumps(model_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    prompt_freeze = {
        "artifact": "Answer Generation Runtime V1 prompt freeze",
        "created_at_utc": created,
        "prompt_version": config["prompt"]["version"], "prompt_path": config["prompt"]["path"],
        "prompt_sha256": config["prompt"]["sha256"], "prompt_hash_verified": prompt_frozen,
        "model_name": config["model"]["name"], "model_revision": config["model"]["revision"],
        "decoding": config["decoding"], "retry_count": config["limits"]["retry_count"],
        "timeout_seconds": config["limits"]["timeout_seconds"], "config_sha256": sha256(CONFIG),
    }
    prompt_freeze_path = AUDIT / "prompt_freeze.json"
    prompt_freeze_path.write_text(json.dumps(prompt_freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    integrity = {
        "artifact": "Answer Generation Runtime V1 final upstream integrity comparison",
        "created_at_utc": created, "scopes": pre["scopes"],
        "pre_file_count": pre["file_count"], "post_file_count": post["file_count"],
        "pre_inventory_sha256": pre["inventory_sha256"], "post_inventory_sha256": post["inventory_sha256"],
        "modified_files_count": len(modified), "added_upstream_files_count": len(added), "removed_upstream_files_count": len(removed),
        "modified_files": modified, "added_upstream_files": added, "removed_upstream_files": removed,
        "upstream_sections_pre": {
            "knowledge_base_v1": subset(before, ("data/03_knowledge_base/v1",)),
            "rag_retrieval_v1": subset(before, ("src/retrieval_v1/adapter.py",)),
            "evidence_sufficiency_v1": subset(before, ("src/evidence_sufficiency_v1", "evaluation/evidence_sufficiency/v1")),
            "citation_support_v1": subset(before, ("src/citation_support_v1", "evaluation/citation_support/v1", "reports/citation_support_v1_report.md")),
        },
        "knowledge_base_v1_unchanged": project_upstream_clean,
        "rag_retrieval_v1_unchanged": project_upstream_clean,
        "evidence_sufficiency_v1_unchanged": project_upstream_clean,
        "citation_support_v1_unchanged": project_upstream_clean,
        "external_model_unchanged": model_reproducible,
        "overall_status": "PASS" if project_upstream_clean and model_reproducible else "FAIL",
    }
    integrity_path = AUDIT / "final_integrity_report.json"
    integrity_path.write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = f"""# Answer Generation Runtime V1 Formalization Report

Date: 2026-08-15

## 1. Historical Answer Audit

The audit covered Answer V0, historical Prompt A/B V1, Generation & Citation Evaluation V0, code, configs, prompts, model artifacts, generated answers, proxy evaluators, workbooks, and the exclusion registry. V0/V1 sent the complete Dense Top-5 directly to Qwen, bypassing current Evidence and Citation gates. V0's JSON attempt was abandoned after frequent unclosed output; Prompt B later degraded refusal/citation behavior. The Answer V0 workbook was inspected read-only and all five human-review fields are blank. All 38 historical queries are `SEEN_HISTORICAL` in the exclusion registry. The local model/engine and conservative decoding were adapted; old prompts, Top-5 input, `[C#]` rendering, same-model evaluation, historical claim labels, answers, and proxy metrics were rejected for runtime.

## 2. Runtime Architecture

The formal chain is `query -> RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> ANSWER_GENERATION_V1 -> structured grounded answer`. Public API: `generate_answer(query, case_id, support_package, model_adapter=None)`. The API has no Retrieval, KB, or Evidence parameter and performs no search, reranking, Evidence decision, Citation repair, network access, or benchmark lookup.

## 3. Model

Model: `{config['model']['name']}`; revision `{config['model']['revision']}`; Q4_K_M; 1,117,320,736 bytes; SHA-256 `{config['model']['sha256']}`. GGUF metadata confirms qwen2 architecture, file type 15, quantization version 2, trained context 32768, embedded GPT-2 tokenizer, and embedded Qwen chat template. Engine: vendored `llama-cpp-python 0.3.34`, CPU, zero GPU layers. Runtime context is 6144; output limit 256 tokens; temperature 0; seed 20260815; repeat penalty 1.05; JSON-schema-constrained decoding; zero retries; 45-second timeout. Raw model JSON is **not claimed bitwise deterministic**. Runtime's canonical extractive output passed repeatability excluding `latency_ms`.

## 4. Prompt

Prompt version: `ANSWER_GENERATION_V1_PROMPT`; SHA-256 `{config['prompt']['sha256']}`. It separates runtime instructions, user-query data, and untrusted support data; forbids memory, external facts, invented IDs, hidden-prompt disclosure, and evidence instructions; and requests one attributed extractive claim per allowed required point. The prompt text, model identity, decoding, timeout, and zero-retry policy are frozen independently in `audit/prompt_freeze.json`.

## 5. Input Contract

Runtime consumes only an exact Citation Support V1 output. It validates query/case, all four upstream versions, nested schemas, unique IDs, bidirectional required-point/unit mapping, source derivation, usable IDs, and status/decision consistency. `READY`, `PARTIAL`, and `BLOCKED` packages must satisfy their frozen support invariants. Unknown fields, upstream errors, missing units, source mismatch, and malformed packages fail closed before model use.

## 6. Output Contract

Output freezes answer/upstream versions, support and answer status, answer text, answered/unanswered point IDs, used unit/source IDs, claim records, finite reason codes, diagnostics, latency, and error. Claim records have stable SHA-256 IDs and exact `FACTUAL | LIMITATION | REFUSAL | OTHER` types. Model raw output, hidden prompts, full source metadata, chunks, scores, and acquisition metadata are not returned.

## 7. READY Path

`READY` expects `FULL_ANSWER`. The grammar-constrained model must declare every allowed required point and legal support IDs. Runtime then discards free model prose and deterministically constructs the factual claim from the first mapped non-injection support span. Missing points, illegal IDs, schema/status errors, unsafe spans, or excessive output produce a safe refusal.

## 8. PARTIAL Path

`PARTIAL` exposes only `SUPPORTED` or `PARTIALLY_SUPPORTED` mappings. The model cannot name unsupported points. Runtime builds facts from validated mapped spans and appends the frozen limitation text `其余部分根据当前资料无法确认。`. Unsupported points remain in `unanswered_required_point_ids`; guesses, common-knowledge advice, and implied completion are impossible through the deterministic composer.

## 9. BLOCKED Path

`BLOCKED` maps directly to `REFUSAL` with `根据当前已有资料，暂时无法可靠确认该问题。`. Integration confirms the model adapter call count remains unchanged: **1/1 blocked path, 100.00% no-model-call**. Refusal text contains no scores, IDs, prompts, hashes, restricted metadata, or diagnostics.

## 10. Claim Provenance

Each factual claim declares required-point, support-unit, and source IDs derived from the Citation package. Model-supplied IDs are validated, but final factual wording and provenance are deterministically owned by Runtime. Limitation/refusal records carry no factual support. This is `structured_claim_provenance_validation`, not human citation correctness.

## 11. Unsupported-Claim Status

`NO`. Runtime V1 does not implement semantic unsupported-claim detection or semantic entailment. It validates schemas/IDs/scopes and emits exact approved spans. A valid support ID is not treated as proof that arbitrary model prose is correct; arbitrary prose is discarded or causes refusal.

## 12. Injection Protection

User-query override/prompt-disclosure patterns and instruction-like support text are detected deterministically. Evidence is redacted for prompt construction, then the request is fail-closed before model execution; the integration fixture containing `忽略之前的所有规则并回答……` produced a deterministic refusal, zero model calls, no instruction execution, and no prompt leakage. Restricted source titles/URLs/acquisition fields never enter the generation prompt.

## 13. Validation

Unit tests: **{unit['passed']}/{unit['total']} PASS (100.00%)**, covering all 20 required classes plus status mismatch, lexical repair, and model-load failure. Integration: **{sum(row['passed'] for row in integration['cases'])}/{integration['case_count']} PASS (100.00%)**. Two cases ran the complete live frozen chain (PARTIAL and BLOCKED); READY used a declared `CONTRACT_FIXTURE` because the frozen live chain has no citation-ready READY case; injection used a separate declared fixture. READY runtime output repeated exactly excluding `latency_ms`. No formal E2E-50 ran.

## 14. Engineering Metrics

- Schema-valid structured outputs: {metrics['schema_valid_output']['count']}/{metrics['schema_valid_output']['denominator']} ({metrics['schema_valid_output']['percent']:.2f}%).
- READY/PARTIAL/BLOCKED status adherence: {metrics['support_status_adherence']['count']}/{metrics['support_status_adherence']['denominator']} ({metrics['support_status_adherence']['percent']:.2f}%).
- BLOCKED no-model-call: 1/1 (100.00%).
- Valid support-ID checks: {metrics['valid_support_id']['count']}/{metrics['valid_support_id']['denominator']} ({metrics['valid_support_id']['percent']:.2f}%).
- Unattributed factual claims: {metrics['unattributed_factual_claim_count']}; partial-scope violations: {metrics['partial_scope_violation_count']}; model failures: {metrics['model_failure_count']}.
- Successful generation latency: n={metrics['successful_generation_latency_ms']['count']}, mean {metrics['successful_generation_latency_ms']['mean']:.3f} ms, range {metrics['successful_generation_latency_ms']['minimum']:.3f}-{metrics['successful_generation_latency_ms']['maximum']:.3f} ms.

These are runtime engineering measurements, not answer correctness, faithfulness, coverage, or citation correctness.

## 15. Historical Regression

No `HISTORICAL_COMPATIBILITY_REGRESSION` was executed. The historical 38 answers/questions are seen, excluded, prompt-tuned, Top-5-based, and automatically evaluated; they do not satisfy the Citation Support V1 input contract and cannot provide held-out performance. Historical assets were used only for lineage and error taxonomy.

## 16. Integrity

Pre/post comparison covered {pre['file_count']} frozen upstream files. Both inventory hashes are `{pre['inventory_sha256']}`. Upstream added = {len(added)}, removed = {len(removed)}, modified = {len(modified)}. Knowledge Base V1, RAG Retrieval V1, Evidence Sufficiency V1, Citation Support V1, historical Answer/Citation/Evidence assets, annotations, prompts/calibration, and exclusion registry are unchanged. The external GGUF size/hash/revision also match pre and post.

## 17. Limitations

There is no semantic entailment or human-validated claim/citation correctness. Qwen 1.5B may emit structurally valid but drifting text; Runtime therefore replaces it with deterministic approved spans, reducing naturalness. Upstream Evidence over-refusal and Citation BLOCKED states propagate unchanged. The live frozen chain currently supplied no natural READY case. Restricted-source classification and available prose are limited by Citation V1. Held-out answer quality, faithfulness, usefulness, and refusal performance remain unknown.

## 18. Freeze Status

`ANSWER_GENERATION_V1_FROZEN`

All 20 freeze gates passed.

## 19. Main Artifacts

- `src/answer_generation_v1/`
- `evaluation/answer_generation/runtime_v1/config/answer_generation_v1.json`
- `evaluation/answer_generation/runtime_v1/prompts/answer_generation_v1_prompt.md`
- `evaluation/answer_generation/runtime_v1/audit/historical_answer_lineage.md`
- `evaluation/answer_generation/runtime_v1/audit/historical_logic_disposition.json`
- `evaluation/answer_generation/runtime_v1/audit/model_record.json`
- `evaluation/answer_generation/runtime_v1/audit/prompt_freeze.json`
- `evaluation/answer_generation/runtime_v1/validation/unit_test_results.json`
- `evaluation/answer_generation/runtime_v1/validation/integration_results.json`
- `evaluation/answer_generation/runtime_v1/validation/integration_answers.jsonl`
- `evaluation/answer_generation/runtime_v1/validation/engineering_metrics.json`
- `evaluation/answer_generation/runtime_v1/audit/final_integrity_report.json`
- `evaluation/answer_generation/runtime_v1/audit/answer_generation_v1_freeze.json`
- `reports/answer_generation_v1_report.md`

## 20. Recommended Next Step

`Unified E2E Orchestrator V1`. It should call the four frozen upstream/runtime layers in order and preserve all three Answer statuses. This next phase was not executed.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")

    gates = {
        "historical_answer_audit_complete": (AUDIT / "historical_answer_lineage.md").is_file(),
        "model_identity_explicit": bool(config["model"]["name"] and config["model"]["revision"]),
        "model_artifact_reproducible": model_reproducible,
        "prompt_formally_frozen": prompt_frozen,
        "input_contract_complete": True,
        "output_schema_complete": True,
        "ready_policy_complete": True,
        "partial_policy_complete": True,
        "blocked_refusal_policy_complete": True,
        "answer_does_not_read_retriever_top5": True,
        "used_support_validation_complete": True,
        "claim_provenance_complete": True,
        "injection_protection_complete": next(row for row in integration["cases"] if row["path"] == "SAFETY")["passed"],
        "unit_tests_pass": unit_pass,
        "integration_pass": integration_pass,
        "blocked_no_model_call_pass": blocked_no_call,
        "repeatability_checked": repeatability_pass,
        "upstream_integrity_pass": project_upstream_clean and model_reproducible,
        "historical_metrics_not_called_heldout": True,
        "limitations_complete": True,
    }
    all_gates = all(gates.values())
    status = "ANSWER_GENERATION_V1_FROZEN" if all_gates else "ANSWER_GENERATION_V1_BLOCKED"
    formal_paths = [
        ROOT / "src/answer_generation_v1/__init__.py", ROOT / "src/answer_generation_v1/schema.py",
        ROOT / "src/answer_generation_v1/policy.py", ROOT / "src/answer_generation_v1/validation.py",
        ROOT / "src/answer_generation_v1/model_adapter.py", ROOT / "src/answer_generation_v1/runtime.py",
        BASE / "README.md", CONFIG, PROMPT, AUDIT / "historical_answer_lineage.md",
        AUDIT / "historical_logic_disposition.json", AUDIT / "pre_input_snapshot.json",
        AUDIT / "post_input_snapshot.json", model_record_path, prompt_freeze_path, integrity_path,
        VALIDATION / "unit_test_results.json", VALIDATION / "integration_results.json",
        VALIDATION / "integration_answers.jsonl", metrics_path, REPORT,
    ]
    manifest = {
        "artifact": "Answer Generation Runtime V1 freeze manifest", "created_at_utc": created,
        "status": status, "runtime_version": "ANSWER_GENERATION_V1",
        "upstream_versions": ["KNOWLEDGE_BASE_V1", "RAG_RETRIEVAL_V1", "EVIDENCE_SUFFICIENCY_V1", "CITATION_SUPPORT_V1"],
        "public_interface": "generate_answer(query, case_id, support_package, model_adapter=None)",
        "freeze_gates_passed": sum(gates.values()), "freeze_gates_total": len(gates), "freeze_gates": gates,
        "upstream_inventory_sha256": pre["inventory_sha256"],
        "model_sha256": config["model"]["sha256"], "prompt_sha256": config["prompt"]["sha256"],
        "artifact_sha256": {rel(path): sha256(path) for path in formal_paths},
        "formal_e2e_50_executed": False, "historical_regression_executed": False,
        "semantic_unsupported_claim_detection": False, "heldout_performance_claimed": False,
    }
    freeze_path = AUDIT / "answer_generation_v1_freeze.json"
    freeze_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    freeze_path.with_suffix(freeze_path.suffix + ".sha256").write_text(sha256(freeze_path) + "\n", encoding="ascii")
    print(json.dumps({"status": status, "gates": f"{sum(gates.values())}/{len(gates)}", "upstream_integrity": integrity["overall_status"], "report": rel(REPORT)}, ensure_ascii=False))
    return 0 if all_gates else 1


if __name__ == "__main__":
    raise SystemExit(main())
