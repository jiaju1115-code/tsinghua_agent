"""One-shot Held-out E2E Evaluation V1 runner; default mode never calls the system."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "evaluation" / "e2e_heldout" / "v1"
CANONICAL_CASES = BASE / "cases" / "e2e_50_cases.jsonl"
CANONICAL_FREEZE = BASE / "audit" / "dataset_freeze.json"
HISTORICAL_REGISTRY = ROOT / "evaluation" / "e2e" / "v1" / "benchmark" / "exclusion_registry.jsonl"
REQUIRED_FIELDS = {
    "case_id", "query", "category", "question_type", "creation_method", "seen_status",
    "slice", "sampling_source", "pre_registered",
}
QUESTION_TYPES = {
    "procedural", "service_navigation", "current_status", "troubleshooting", "resource_lookup",
    "service_scope", "policy_lookup", "policy_currency", "current_unavailable", "multi_part",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize(query: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKC", query).lower()
        if unicodedata.category(char)[0] not in {"P", "Z", "S"}
    )


def trigrams(value: str) -> set[str]:
    return {value[index:index + 3] for index in range(max(1, len(value) - 2))} or {value}


def validate_cases(cases: list[dict[str, Any]], require_exact_50: bool = True) -> list[str]:
    errors: list[str] = []
    if require_exact_50 and len(cases) != 50:
        errors.append(f"expected 50 cases, got {len(cases)}")
    ids = [row.get("case_id") for row in cases]
    if len(ids) != len(set(ids)):
        errors.append("case_id values are not unique")
    if require_exact_50 and ids != [f"E2E{index:03d}" for index in range(1, 51)]:
        errors.append("case_id sequence must be E2E001 through E2E050")
    for row in cases:
        if set(row) != REQUIRED_FIELDS:
            errors.append(f"{row.get('case_id', '<missing>')}: field set differs from frozen case contract")
            continue
        if not isinstance(row["query"], str) or len(row["query"].strip()) < 8:
            errors.append(f"{row['case_id']}: query is invalid")
        if row["question_type"] not in QUESTION_TYPES:
            errors.append(f"{row['case_id']}: question_type is invalid")
        if row["creation_method"] != "MANUAL_REAL_CAMPUS_QA_DESIGN_V1":
            errors.append(f"{row['case_id']}: creation_method is invalid")
        if row["seen_status"] != "HELD_OUT" or row["pre_registered"] is not True:
            errors.append(f"{row['case_id']}: held-out status contract is invalid")
    return errors


def contamination_audit(cases: list[dict[str, Any]]) -> dict[str, Any]:
    historical = read_jsonl(HISTORICAL_REGISTRY)
    exact_matches: list[dict[str, Any]] = []
    normalized_matches: list[dict[str, Any]] = []
    near_matches: list[dict[str, Any]] = []
    nearest: list[dict[str, Any]] = []
    for case in cases:
        query = case["query"]
        normalized = normalize(query)
        best: tuple[float, float, dict[str, Any]] | None = None
        for historical_row in historical:
            historical_query = historical_row["raw_query"]
            historical_normalized = normalize(historical_query)
            sequence = difflib.SequenceMatcher(None, normalized, historical_normalized).ratio()
            first, second = trigrams(normalized), trigrams(historical_normalized)
            jaccard = len(first & second) / len(first | second)
            record = (sequence, jaccard, historical_row)
            if best is None or record[:2] > best[:2]:
                best = record
            hit = {
                "case_id": case["case_id"], "historical_source_dataset": historical_row["source_dataset"],
                "historical_raw_query_sha256": historical_row["raw_query_sha256"],
            }
            if query == historical_query:
                exact_matches.append(hit)
            if normalized == historical_normalized:
                normalized_matches.append(hit)
        assert best is not None
        sequence, jaccard, historical_row = best
        nearest.append({
            "case_id": case["case_id"], "max_sequence_ratio": round(sequence, 6),
            "max_trigram_jaccard": round(jaccard, 6),
            "nearest_historical_source_dataset": historical_row["source_dataset"],
            "nearest_historical_raw_query_sha256": historical_row["raw_query_sha256"],
        })
        if sequence >= 0.80 or jaccard >= 0.65:
            near_matches.append(nearest[-1])
    source_counts = Counter(row["source_dataset"] for row in historical)
    return {
        "artifact": "Held-out E2E Evaluation V1 contamination audit",
        "method": {
            "exact": "raw Unicode string equality",
            "normalized": "NFKC + lowercase + whitespace/punctuation/symbol removal",
            "near_duplicate": "max SequenceMatcher ratio >= 0.80 OR character-trigram Jaccard >= 0.65 against the historical exclusion registry",
            "external_model_or_api_called": False,
        },
        "historical_registry": {
            "path": "evaluation/e2e/v1/benchmark/exclusion_registry.jsonl",
            "row_count": len(historical),
            "source_dataset_count": len(source_counts),
            "source_dataset_rows": dict(sorted(source_counts.items())),
            "coverage_scope": [
                "Historical Answer 38", "Router evaluation", "Evidence calibration/evaluation",
                "Citation evaluation", "Answer evaluation", "gold-label and Human Check lineage",
                "synthetic cases", "fixtures", "integration cases", "Prompt debugging cases",
            ],
        },
        "case_count": len(cases),
        "exact_duplicate_count": len(exact_matches),
        "normalized_duplicate_count": len(normalized_matches),
        "near_duplicate_count": len(near_matches),
        "exact_matches": exact_matches,
        "normalized_matches": normalized_matches,
        "near_duplicate_matches": near_matches,
        "nearest_historical_summary": nearest,
        "all_cases_held_out": not exact_matches and not normalized_matches and not near_matches,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_heldout_registry(path: Path, cases: list[dict[str, Any]]) -> None:
    rows = [
        {
            "case_id": case["case_id"],
            "raw_query_sha256": hashlib.sha256(case["query"].encode("utf-8")).hexdigest(),
            "normalized_query_sha256": hashlib.sha256(normalize(case["query"]).encode("utf-8")).hexdigest(),
            "status": "HELD_OUT_FROZEN_NOT_RUN",
            "source_dataset": "evaluation/e2e_heldout/v1/cases/e2e_50_cases.jsonl",
        }
        for case in cases
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--cases", type=Path, default=CANONICAL_CASES)
    parser.add_argument("--audit-output", type=Path, default=BASE / "audit" / "contamination_audit.json")
    parser.add_argument("--heldout-registry-output", type=Path, default=BASE / "audit" / "heldout_exclusion_registry_v1.jsonl")
    parser.add_argument("--results-output", type=Path, default=BASE / "results" / "e2e_50_results.jsonl")
    parser.add_argument("--allow-contract-fixture", action="store_true")
    args = parser.parse_args()
    if sum(bool(value) for value in (args.validate_only, args.audit_only, args.execute)) != 1:
        parser.error("select exactly one mode")
    cases_path = args.cases if args.cases.is_absolute() else ROOT / args.cases
    cases = read_jsonl(cases_path)
    errors = validate_cases(cases, require_exact_50=not args.allow_contract_fixture)
    if args.audit_only:
        if args.allow_contract_fixture:
            parser.error("contamination audit is reserved for canonical E2E-50 cases")
        audit = contamination_audit(cases)
        write_json(args.audit_output if args.audit_output.is_absolute() else ROOT / args.audit_output, audit)
        write_heldout_registry(
            args.heldout_registry_output if args.heldout_registry_output.is_absolute() else ROOT / args.heldout_registry_output,
            cases,
        )
        print(json.dumps({"mode": "audit_only", "schema_errors": errors, "all_cases_held_out": audit["all_cases_held_out"]}))
        return 0 if not errors and audit["all_cases_held_out"] else 1
    if args.validate_only:
        print(json.dumps({"mode": "validate_only", "case_count": len(cases), "schema_errors": errors, "system_calls": 0}))
        return 0 if not errors else 1
    if errors:
        raise SystemExit("refusing execution: dataset schema validation failed")
    if cases_path.resolve() != CANONICAL_CASES.resolve():
        raise SystemExit("refusing execution: --execute accepts only canonical frozen E2E-50")
    freeze = json.loads(CANONICAL_FREEZE.read_text(encoding="utf-8"))
    if freeze.get("status") != "HELD_OUT_E2E_V1_DATASET_FROZEN" or freeze.get("dataset_sha256") != sha256(CANONICAL_CASES):
        raise SystemExit("refusing execution: frozen dataset manifest/hash is invalid")
    from src.e2e_orchestrator_v1 import run_e2e
    output = args.results_output if args.results_output.is_absolute() else ROOT / args.results_output
    if output.exists():
        raise SystemExit("refusing execution: result destination already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            result = run_e2e(case["query"], case["case_id"])
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"mode": "execute", "case_count": len(cases), "retries": 0, "repair": False, "result_path": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
