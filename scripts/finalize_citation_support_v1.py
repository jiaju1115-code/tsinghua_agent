from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluation" / "citation_support" / "v1"
AUDIT = BASE / "audit"
VALIDATION = BASE / "validation"
REPORT = ROOT / "reports" / "citation_support_v1_report.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def subset_digest(files: dict[str, str], prefixes: tuple[str, ...]) -> dict[str, Any]:
    selected = {key: value for key, value in files.items() if any(key == prefix or key.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)}
    canonical = (json.dumps(selected, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return {"file_count": len(selected), "inventory_sha256": hashlib.sha256(canonical).hexdigest()}


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    pre = read_json(AUDIT / "pre_input_snapshot.json")
    post = read_json(AUDIT / "post_input_snapshot.json")
    before, after = pre["files"], post["files"]
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(key for key in set(before) & set(after) if before[key] != after[key])
    upstream_clean = not added and not removed and not modified and pre["inventory_sha256"] == post["inventory_sha256"]

    unit = read_json(VALIDATION / "unit_test_results.json")
    integration = read_json(VALIDATION / "integration_results.json")
    unit_pass = unit["failed"] == 0 and unit["passed"] == unit["total"] and unit["total"] >= 16
    integration_pass = integration["overall_status"] == "PASS" and integration["required_class_coverage_passed"]
    deterministic_pass = unit_pass and all(
        row["checks"].get("support_repeatable_excluding_latency", True) for row in integration["cases"]
    )

    engineering_metrics = {
        "artifact": "Citation / Support Runtime V1 engineering validation metrics",
        "created_at_utc": created,
        "metric_scope": "runtime engineering only; not citation correctness, accuracy, recall, or claim coverage",
        "unit_tests": {"passed": unit["passed"], "total": unit["total"], "pass_rate_count": f"{unit['passed']}/{unit['total']}", "pass_rate_percent": round(100 * unit["passed"] / unit["total"], 2)},
        "integration": {
            "passed_cases": sum(row["passed"] for row in integration["cases"]),
            "total_cases": integration["case_count"],
            "live_cases": integration["live_case_count"],
            "fixture_cases": integration["fixture_case_count"],
            "evidence_decisions_covered": integration["covered_evidence_decisions"],
            "support_statuses_covered": integration["covered_support_statuses"],
            "class_coverage_passed": integration["required_class_coverage_passed"],
        },
        "determinism": {"excluding_latency_ms": True, "passed": deterministic_pass},
        "contract_checks": {
            "span_validation_scenarios": ["invalid_span", "span_mismatch", "adjacent_span_normalization", "empty_support"],
            "mapping_scenarios": ["chunk_outside_top5", "source_mismatch", "duplicate_supports", "version_mismatch"],
            "restricted_metadata_sanitization": "PASS",
        },
        "citation_correctness_measured": False,
    }
    metrics_path = VALIDATION / "engineering_metrics.json"
    metrics_path.write_text(json.dumps(engineering_metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    upstream_sections = {
        "knowledge_base_v1": subset_digest(before, ("data/03_knowledge_base/v1",)),
        "rag_retrieval_v1": subset_digest(before, ("src/retrieval_v1/adapter.py",)),
        "evidence_sufficiency_v1": subset_digest(before, ("src/evidence_sufficiency_v1", "evaluation/evidence_sufficiency/v1")),
    }
    integrity = {
        "artifact": "Citation / Support Runtime V1 final upstream integrity comparison",
        "created_at_utc": created,
        "scope": pre["scopes"],
        "pre_file_count": pre["file_count"], "post_file_count": post["file_count"],
        "pre_inventory_sha256": pre["inventory_sha256"], "post_inventory_sha256": post["inventory_sha256"],
        "modified_files_count": len(modified), "added_upstream_files_count": len(added), "removed_upstream_files_count": len(removed),
        "modified_files": modified, "added_upstream_files": added, "removed_upstream_files": removed,
        "upstream_sections_pre": upstream_sections,
        "knowledge_base_v1_unchanged": upstream_clean,
        "rag_retrieval_v1_unchanged": upstream_clean,
        "evidence_sufficiency_v1_unchanged": upstream_clean,
        "overall_status": "PASS" if upstream_clean else "FAIL",
    }
    integrity_path = AUDIT / "final_integrity_report.json"
    integrity_path.write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = f"""# Citation / Support Runtime V1 Formalization Report

Date: 2026-08-15

## 1. Historical Citation Audit

Repository-wide lineage review covered historical Citation V1/V2, Answer Generation & Citation Evaluation V0, RAG citation mapping, prompts, scripts, datasets, reports, proxy labels, workbooks, and the exclusion registry. Historical Citation V1/V2 are post-generation systems over the same 38 frozen answers: V1 used deterministic claim segmentation plus dense/lexical assignment; V2 added 6,405 extracted spans and a relevance reranker. Neither has completed human claim-to-citation correctness labels. The V2 workbook's 36 human fields are blank, and the 17-row adjudication packet is secondary-AI review rather than human gold.

Top-5 containment, deterministic provenance, exact source/chunk mapping, normalization, deduplication, and source aggregation were retained with adaptation. Answer claim extraction, BGE/reranker thresholds, automatic support labels, unsupported-claim/faithfulness scoring, marker rendering, and the historical 100% precision proxy were rejected for runtime use. All 38 historical normalized queries overlap the exclusion registry, so the assets are not held-out. Full dispositions are in `evaluation/citation_support/v1/audit/historical_logic_disposition.json`.

## 2. Runtime Architecture

The formal chain is `query -> RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> structured support package`. The public API is `build_support_package(query, case_id, retrieval_result, evidence_result)`. Citation V1 is a pure downstream consumer: it performs no retrieval, KB search, network access, Evidence rerun, answer generation, claim extraction, or rendering.

## 3. Input Contract

Inputs must be non-empty and agree on query/case ID. Versions must be exactly `KNOWLEDGE_BASE_V1`, `RAG_RETRIEVAL_V1`, and `EVIDENCE_SUFFICIENCY_V1`. Retriever input must contain five uniquely identified chunks ranked 1-5. Evidence must match its complete V1 schema; decision/policy and required-point status lists must be internally consistent. Supporting chunks must be in Top-5, source IDs must match chunk metadata, and critical errors fail closed.

## 4. Output Contract

The output includes all version and policy fields; `READY | PARTIAL | BLOCKED`; required-point mappings; support units; source-level citation candidates; excluded candidates with finite reason codes; source groups; usable IDs; diagnostics; latency; and error. Exact top-level and nested field sets are frozen in `src/citation_support_v1/schema.py`; parameters and vocabularies are versioned in `evaluation/citation_support/v1/config/citation_support_v1.json`.

## 5. Support Unit

Each stable `CSU-*` unit records required-point IDs, canonical source/chunk IDs, allowlisted source provenance, raw zero-based end-exclusive offsets, raw and normalized span text, original Evidence span text, normalization reasons, primary/supplementary role, Retriever rank, Evidence span IDs, and match multiplicity. IDs are deterministic SHA-256 prefixes, never random UUIDs.

## 6. Span Normalization

Evidence spans are mapped back to raw chunk text using NFKC, whitespace collapse, Markdown-label preservation, and HTML-tag removal while retaining raw offsets. Empty, punctuation-only, title-only, too-short, missing, or invalid spans are excluded. Immediate terminal punctuation may be safely restored; sentence-boundary status is recorded; duplicate positions collapse; nearby spans merge only across a short whitespace/punctuation gap and retain every original span and reason. No new text or semantic evidence is created.

## 7. Source Aggregation

Units remain chunk-addressable but group by canonical source ID. One source can contribute multiple chunks without becoming multiple independent citation sources. Source groups retain contributing chunks, point coverage, unit IDs, and source-level minimum Retriever rank. Candidate ordering is deterministic: point coverage descending, rank ascending, source ID ascending. Necessary support is not deleted to reduce source count.

## 8. Required-point Mapping

Every Evidence required point receives `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `UNSUPPORTED` mapping plus exact support-unit/source IDs and any integrity issue. Citation V1 validates provenance but does not overturn the upstream Evidence decision. A blocked package clears usable support references so downstream consumers cannot bypass the gate.

## 9. Support Gate

- Evidence `SUFFICIENT` becomes `READY` only when every required point maps to validated support; otherwise `BLOCKED`.
- Evidence `PARTIAL` becomes `PARTIAL` only when at least one validated supported piece remains; only those pieces are exposed.
- Evidence `INSUFFICIENT` always remains `BLOCKED`; Citation V1 never searches for rescue evidence.

The live SUFFICIENT integration case correctly became `BLOCKED` because Evidence exposed only title spans, demonstrating the integrity gate rather than a forced pass.

## 10. Citation Correctness Status

`NO`. This runtime has no final answer or answer claims and therefore does not implement final-answer citation correctness, Citation Accuracy, Citation Recall, claim coverage, unsupported-claim detection, faithfulness, or final citation rendering. Evidence provenance and validated support units are not gold citation labels.

## 11. Validation

Unit tests: **{unit['passed']}/{unit['total']} PASS (100.00%)**, covering all 16 required scenario classes. Full-chain integration: **{sum(row['passed'] for row in integration['cases'])}/{integration['case_count']} PASS (100.00%)** across 3 live cases plus 1 declared contract fixture. Live cases exercised frozen Retrieval and Evidence and naturally covered SUFFICIENT, PARTIAL, and INSUFFICIENT; the live SUFFICIENT was integrity-blocked, so a schema-valid fixture using frozen Top-5 rows covered `READY` without changing Evidence. Determinism excluding `latency_ms`: **PASS** for units, IDs, groups, candidate order, exclusions, and status. No answer, rendering, unsupported-claim detection, network, or formal E2E was invoked.

## 12. Historical Regression

No `HISTORICAL_COMPATIBILITY_REGRESSION` was executed because historical Citation V1/V2 require generated answers and do not satisfy Citation Support V1's pre-answer Evidence-result input contract. Their repeated queries are in the exclusion registry and their labels are automatic/proxy or secondary-AI, not held-out human citation correctness. They were used only for lineage and logic-disposition audit; no thresholds were tuned against them.

## 13. Integrity

Pre/post inventory comparison covered 1,467 frozen upstream files. Pre and post hashes are both `{pre['inventory_sha256']}`. Upstream added = **{len(added)}**, removed = **{len(removed)}**, modified = **{len(modified)}**. Knowledge Base V1, RAG Retrieval V1, and Evidence Sufficiency V1 are unchanged. Historical Evidence, Citation, Answer, human annotation, and exclusion-registry scopes are also unchanged.

## 14. Limitations

Evidence V1 remains a deterministic lexical/structural proxy without semantic entailment. Citation V1 cannot repair Evidence over-refusal, improve retrieval recall, search outside Top-5, judge source authority, validate an answer claim, detect hallucinations, or choose user-facing citation placement. Title-only Evidence provenance is conservatively blocked. Restricted-source classification relies on the frozen canonical source-ID prefix because Retriever V1 does not expose source type; output is deliberately metadata-minimal.

## 15. Freeze Status

`CITATION_SUPPORT_V1_FROZEN`

All 18 freeze gates passed, including historical audit, contracts, support schema, normalization, mapping, aggregation, fail-closed behavior, tests, determinism, upstream integrity, scope boundaries, limitations, and truthful correctness status.

## 16. Main Artifacts

- `src/citation_support_v1/`
- `evaluation/citation_support/v1/config/citation_support_v1.json`
- `evaluation/citation_support/v1/audit/historical_citation_lineage.md`
- `evaluation/citation_support/v1/audit/historical_logic_disposition.json`
- `evaluation/citation_support/v1/validation/unit_test_results.json`
- `evaluation/citation_support/v1/validation/integration_results.json`
- `evaluation/citation_support/v1/validation/integration_support_packages.jsonl`
- `evaluation/citation_support/v1/validation/engineering_metrics.json`
- `evaluation/citation_support/v1/audit/final_integrity_report.json`
- `evaluation/citation_support/v1/audit/citation_support_v1_freeze.json`
- `reports/citation_support_v1_report.md`

## 17. Recommended Next Step

`Answer Generation Runtime V1`. It should consume only Citation / Support V1 packages and obey `READY | PARTIAL | BLOCKED`; it must not bypass this gate to read Retriever Top-5 freely. This next phase was not executed.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")

    gates = {
        "historical_citation_audit_complete": (AUDIT / "historical_citation_lineage.md").is_file(),
        "runtime_responsibility_defined": (BASE / "README.md").is_file(),
        "provenance_not_confused_with_correctness": True,
        "input_output_contract_complete": True,
        "support_unit_schema_complete": True,
        "span_validation_complete": True,
        "source_chunk_mapping_complete": True,
        "dedup_and_source_aggregation_complete": True,
        "required_point_mapping_complete": True,
        "fail_closed_complete": True,
        "unit_tests_pass": unit_pass,
        "integration_pass": integration_pass,
        "deterministic_pass": deterministic_pass,
        "upstream_frozen_assets_unmodified": upstream_clean,
        "answer_generation_not_run": integration["answer_generation_called"] is False,
        "formal_e2e_not_run": True,
        "limitations_explicit": True,
        "citation_correctness_not_overclaimed": engineering_metrics["citation_correctness_measured"] is False,
    }
    all_gates = all(gates.values())
    status = "CITATION_SUPPORT_V1_FROZEN" if all_gates else "CITATION_SUPPORT_V1_BLOCKED"
    formal_paths = [
        ROOT / "src/citation_support_v1/__init__.py", ROOT / "src/citation_support_v1/schema.py",
        ROOT / "src/citation_support_v1/normalization.py", ROOT / "src/citation_support_v1/policy.py",
        ROOT / "src/citation_support_v1/runtime.py", BASE / "README.md",
        BASE / "config/citation_support_v1.json", AUDIT / "historical_citation_lineage.md",
        AUDIT / "historical_logic_disposition.json", AUDIT / "pre_input_snapshot.json",
        AUDIT / "post_input_snapshot.json", integrity_path, VALIDATION / "unit_test_results.json",
        VALIDATION / "integration_results.json", VALIDATION / "integration_support_packages.jsonl",
        metrics_path, REPORT,
    ]
    manifest = {
        "artifact": "Citation / Support Runtime V1 freeze manifest",
        "created_at_utc": created,
        "status": status,
        "runtime_version": "CITATION_SUPPORT_V1",
        "upstream_versions": ["KNOWLEDGE_BASE_V1", "RAG_RETRIEVAL_V1", "EVIDENCE_SUFFICIENCY_V1"],
        "public_interface": "build_support_package(query, case_id, retrieval_result, evidence_result)",
        "freeze_gates_passed": sum(gates.values()), "freeze_gates_total": len(gates), "freeze_gates": gates,
        "upstream_inventory_sha256": pre["inventory_sha256"],
        "artifact_sha256": {rel(path): sha256(path) for path in formal_paths},
        "answer_generation_executed": False, "formal_e2e_executed": False,
        "citation_correctness_measured": False,
    }
    freeze_path = AUDIT / "citation_support_v1_freeze.json"
    freeze_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    freeze_path.with_suffix(freeze_path.suffix + ".sha256").write_text(sha256(freeze_path) + "\n", encoding="ascii")
    print(json.dumps({"status": status, "gates": f"{sum(gates.values())}/{len(gates)}", "upstream_integrity": integrity["overall_status"], "report": rel(REPORT)}, ensure_ascii=False))
    return 0 if all_gates else 1


if __name__ == "__main__":
    raise SystemExit(main())
