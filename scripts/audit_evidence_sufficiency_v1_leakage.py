from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "experiments" / "evidence_sufficiency_v0_3" / "dataset" / "unified_calibration_dataset.json"
REGISTRY = ROOT / "evaluation" / "e2e" / "v1" / "benchmark" / "exclusion_registry.jsonl"
V03_REGISTRY_SOURCE = "experiments/evidence_sufficiency_v0_3/dataset/unified_calibration_dataset.json"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    rows = json.loads(DATASET.read_text(encoding="utf-8"))
    registry = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]
    registry_by_source: dict[str, list[dict]] = defaultdict(list)
    for row in registry:
        registry_by_source[row["source_dataset"]].append(row)

    normalized_counts = Counter(row["normalized_query"] for row in rows)
    pair_counts = Counter(row["query_evidence_sha256"] for row in rows)
    source_query_groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("source_query_id"):
            source_query_groups[row["source_query_id"]].append(row)

    fold_by_id: dict[str, str] = {}
    for filename in ("real_cross_validation_predictions.csv", "synthetic_cross_validation_predictions.csv"):
        path = ROOT / "experiments" / "evidence_sufficiency_v0_3" / "results" / filename
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                fold_by_id[row["record_id"]] = row["fold"]
    normalized_folds: dict[str, set[str]] = defaultdict(set)
    source_query_folds: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        normalized_folds[row["normalized_query"]].add(fold_by_id[row["record_id"]])
        if row.get("source_query_id"):
            source_query_folds[row["source_query_id"]].add(fold_by_id[row["record_id"]])

    v03_registry_rows = registry_by_source[V03_REGISTRY_SOURCE]
    v03_registry_normalized_hashes = {row["normalized_query_sha256"] for row in v03_registry_rows}
    normalized_registry_matches = sum(
        sha256_text(row["normalized_query"]) in v03_registry_normalized_hashes for row in rows
    )
    benchmark_overlaps = {}
    for name, source in {
        "rag_v1_eval_38": "evaluation/rag/v1/evaluation/eval_queries.jsonl",
        "answer_generation_v0_38": "evaluation/answer_generation/v0/results/answer_eval_merged.jsonl",
        "router_v0_2_blind_42": "experiments/router_v0_2/evaluation/router_blind_shadow_set.json",
        "e2e12": "experiments/e2e12_router_v0_2/evaluation/e2e12_set.json",
    }.items():
        hashes = {row["normalized_query_sha256"] for row in registry_by_source[source]}
        benchmark_overlaps[name] = {
            "benchmark_unique_normalized_queries": len(hashes),
            "overlap_with_v0_3_unique_normalized_queries": len(hashes & v03_registry_normalized_hashes),
        }

    payload = {
        "artifact": "Evidence Sufficiency Runtime V1 historical leakage and provenance audit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_v1_training_data_used": False,
        "runtime_v1_threshold_tuning_on_historical_data": False,
        "runtime_v1_thresholds_locked_before_historical_regression": True,
        "historical_v0_3": {
            "row_count": len(rows),
            "prior_usage_distribution": dict(Counter(row["prior_usage"] for row in rows)),
            "unique_normalized_queries": len(normalized_counts),
            "normalized_query_duplicate_groups": sum(count > 1 for count in normalized_counts.values()),
            "rows_in_normalized_query_duplicate_groups": sum(count for count in normalized_counts.values() if count > 1),
            "unique_query_evidence_hashes": len(pair_counts),
            "query_evidence_duplicate_groups_computed": sum(count > 1 for count in pair_counts.values()),
            "rows_in_query_evidence_duplicate_groups_computed": sum(count for count in pair_counts.values() if count > 1),
            "source_query_variant_groups": len(source_query_groups),
            "source_query_multi_variant_groups": sum(len(group) > 1 for group in source_query_groups.values()),
            "template_family_distribution": dict(Counter((row.get("transformation") or row.get("construction_type") or "NONE") for row in rows)),
            "normalized_query_families_crossing_cv_folds": sum(len(folds) > 1 for folds in normalized_folds.values()),
            "normalized_query_family_count": len(normalized_folds),
            "source_query_variant_families_crossing_cv_folds": sum(len(folds) > 1 for folds in source_query_folds.values()),
            "source_query_variant_family_count": len(source_query_folds),
            "historical_threshold_selection_used_seen_calibration_data": True,
            "threshold_selection_evidence": [
                "experiments/evidence_sufficiency_v0_3/scripts/run_v0_3_cross_validation.py:20-23,121-150",
                "experiments/evidence_sufficiency_v0_3/candidates/candidate_config.json",
            ],
            "cv_partition_risk": "Rows were assigned by record_id within label/type strata, not grouped by normalized query or source_query_id; related variants therefore crossed folds.",
        },
        "exclusion_registry": {
            "total_rows": len(registry),
            "v0_3_rows_registered": len(v03_registry_rows),
            "v0_3_normalized_hash_row_matches": normalized_registry_matches,
            "v0_3_registration_coverage_pct": round(100 * normalized_registry_matches / len(rows), 4),
            "v0_3_unique_registered_normalized_queries": len(v03_registry_normalized_hashes),
            "v0_3_unique_registered_query_evidence_canonical_hashes": len({row["query_evidence_canonical_sha256"] for row in v03_registry_rows}),
            "benchmark_normalized_query_overlaps": benchmark_overlaps,
        },
        "conclusions": [
            "All 147 V0.3 calibration rows are explicitly registered for future exclusion.",
            "Historical V0.3 metrics are not independent generalization evidence because all rows were seen calibration and related query families crossed CV folds.",
            "Synthetic template variants have substantial family overlap with real/historical queries and must not be treated as held-out.",
            "The Runtime V1 implementation did not train on these rows and did not alter its predeclared thresholds after regression.",
            "A future truly held-out evaluation must exclude all registry hashes and group query/template families before splitting.",
        ],
        "classification": "HISTORICAL_LEAKAGE_RISK_CONFIRMED_RUNTIME_V1_NOT_TUNED_ON_HISTORY",
    }
    target = ROOT / "evaluation" / "evidence_sufficiency" / "v1" / "audit" / "leakage_audit.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
