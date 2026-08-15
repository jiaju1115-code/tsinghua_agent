from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence_sufficiency_v1 import evaluate_evidence
from src.evidence_sufficiency_v1.schema import DECISIONS, OUTPUT_FIELDS


SOURCE = ROOT / "experiments" / "evidence_sufficiency_v0_3" / "dataset" / "unified_calibration_dataset.json"
OUT_DIR = ROOT / "evaluation" / "evidence_sufficiency" / "v1" / "results"
LABEL_MAP = {
    "EVIDENCE_SUFFICIENT": "SUFFICIENT",
    "EVIDENCE_PARTIAL": "PARTIAL",
    "EVIDENCE_INSUFFICIENT": "INSUFFICIENT",
}


def pct(count: int, denominator: int) -> float:
    return round(100.0 * count / denominator, 4) if denominator else 0.0


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    confusion = {truth: {pred: 0 for pred in DECISIONS} for truth in DECISIONS}
    for row in rows:
        confusion[row["reference_label"]][row["runtime_decision"]] += 1
    exact = sum(confusion[label][label] for label in DECISIONS)
    per_class = {}
    f1_values = []
    for label in DECISIONS:
        tp = confusion[label][label]
        fp = sum(confusion[truth][label] for truth in DECISIONS if truth != label)
        fn = sum(confusion[label][pred] for pred in DECISIONS if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        per_class[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": sum(confusion[label].values()),
            "precision": round(precision, 6),
            "precision_pct": round(precision * 100, 4),
            "recall": round(recall, 6),
            "recall_pct": round(recall * 100, 4),
            "f1": round(f1, 6),
            "f1_pct": round(f1 * 100, 4),
        }
    false_sufficient = sum(
        1 for row in rows if row["runtime_decision"] == "SUFFICIENT" and row["reference_label"] != "SUFFICIENT"
    )
    missed_sufficient = sum(
        1 for row in rows if row["reference_label"] == "SUFFICIENT" and row["runtime_decision"] != "SUFFICIENT"
    )
    partial_boundary = sum(
        1 for row in rows if (row["reference_label"] == "PARTIAL") != (row["runtime_decision"] == "PARTIAL")
    )
    return {
        "sample_count": total,
        "reference_distribution": dict(Counter(row["reference_label"] for row in rows)),
        "runtime_distribution": dict(Counter(row["runtime_decision"] for row in rows)),
        "confusion_matrix_reference_rows_runtime_columns": confusion,
        "exact_agreement_count": exact,
        "exact_agreement_pct": pct(exact, total),
        "macro_f1": round(sum(f1_values) / len(f1_values), 6),
        "macro_f1_pct": round(100 * sum(f1_values) / len(f1_values), 4),
        "per_class": per_class,
        "false_sufficient_count": false_sufficient,
        "false_sufficient_pct_of_all": pct(false_sufficient, total),
        "missed_sufficient_count": missed_sufficient,
        "missed_sufficient_pct_of_all": pct(missed_sufficient, total),
        "false_insufficient_or_over_refusal_count": missed_sufficient,
        "false_insufficient_or_over_refusal_pct_of_all": pct(missed_sufficient, total),
        "partial_boundary_error_count": partial_boundary,
        "partial_boundary_error_pct_of_all": pct(partial_boundary, total),
    }


def main() -> None:
    source_rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    eligible = [row for row in source_rows if len(row.get("frozen_evidence", [])) == 5]
    predictions = []
    schema_failures = []
    for row in eligible:
        chunks = []
        for rank, evidence in enumerate(row["frozen_evidence"], 1):
            chunks.append(
                {
                    "rank": rank,
                    "source_id": str(evidence.get("source_id") or f"UNKNOWN_SOURCE_{rank}"),
                    "chunk_id": f"{row['record_id']}::{evidence.get('evidence_id', rank)}",
                    "score": round(1.0 / rank, 6),
                    "title": str(evidence.get("title") or ""),
                    "url": str(evidence.get("url") or ""),
                    "category": str(row.get("category") or "historical"),
                    "text": str(evidence.get("text") or ""),
                }
            )
        retrieval = {
            "query": row["query"],
            "case_id": row["record_id"],
            "retriever_version": "RAG_RETRIEVAL_V1",
            "corpus_version": "KNOWLEDGE_BASE_V1",
            "ordered_top5_chunks": chunks,
            "error": None,
        }
        result = evaluate_evidence(row["query"], row["record_id"], retrieval)
        if set(result) != OUTPUT_FIELDS:
            schema_failures.append(row["record_id"])
        predictions.append(
            {
                "record_id": row["record_id"],
                "sample_id": row["sample_id"],
                "query": row["query"],
                "data_kind": row["data_kind"],
                "source_dataset": row["source_dataset"],
                "prior_usage": row["prior_usage"],
                "reference_label": LABEL_MAP[row["label"]],
                "runtime_decision": result["decision"],
                "policy_signal": result["policy_signal"],
                "reason_codes": result["reason_codes"],
                "supported_points": result["supported_points"],
                "partially_supported_points": result["partially_supported_points"],
                "unsupported_points": result["unsupported_points"],
                "missing_requested_attributes": result["missing_requested_attributes"],
                "supporting_chunk_ids": result["supporting_chunk_ids"],
                "error": result["error"],
            }
        )

    real = [row for row in predictions if row["data_kind"] == "REAL_ADJUDICATED"]
    synthetic = [row for row in predictions if row["data_kind"] == "SYNTHETIC_CONSTRUCTED"]
    payload = {
        "evaluation_name": "HISTORICAL_CALIBRATION_COMPATIBILITY_REGRESSION",
        "runtime_version": "EVIDENCE_SUFFICIENCY_V1",
        "input_source": SOURCE.relative_to(ROOT).as_posix(),
        "input_total_rows": len(source_rows),
        "eligible_exactly_top5_rows": len(eligible),
        "excluded_non_top5_rows": len(source_rows) - len(eligible),
        "eligibility_rule": "Only historical rows already containing exactly five frozen evidence items are accepted; no truncation, padding, or retrieval rerun.",
        "interpretation_limits": [
            "This is compatibility regression on previously used calibration/adjudication/synthetic material.",
            "It is not a new blind test, held-out test, production estimate, or semantic-entailment validation.",
            "Historical reference labels are evaluation references, not absolute gold truth.",
        ],
        "thresholds_locked_before_regression": True,
        "schema_failure_count": len(schema_failures),
        "schema_failure_ids": schema_failures,
        "all_eligible": metrics(predictions),
        "real_adjudicated": metrics(real),
        "synthetic_constructed": metrics(synthetic),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "historical_regression_metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (OUT_DIR / "historical_regression_predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in predictions:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
