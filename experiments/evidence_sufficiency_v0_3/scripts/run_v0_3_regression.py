"""Run the frozen V0.3 candidate on historical, already-seen datasets."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import joblib


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
CV_SCRIPT = ROOT / "scripts" / "run_v0_3_cross_validation.py"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_cv_module():
    spec = importlib.util.spec_from_file_location("v03_cv_frozen", CV_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def normalize(rows, source_dataset: str, data_kind: str):
    normalized = []
    for row in rows:
        item = dict(row)
        item["record_id"] = f"{source_dataset}::{row['sample_id']}"
        item["source_dataset"] = source_dataset
        item["data_kind"] = data_kind
        item["construction_type"] = row.get("construction_type") or "REAL"
        item["label"] = (
            row.get("label")
            or row.get("adjudicated_evidence_gate")
            or row.get("expected_gate")
        )
        item["calibration_status"] = "SEEN_REGRESSION"
        normalized.append(item)
    return normalized


def simple_metrics(cv, predictions):
    result = cv.metrics(predictions)
    result["evaluation_status"] = "SEEN_REGRESSION"
    return result


def write_predictions(path: Path, rows):
    fields = [
        "record_id", "sample_id", "source_dataset", "construction_type",
        "expected", "predicted", "correct", "class_probabilities",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "record_id": row["record_id"],
                "sample_id": row["sample_id"],
                "source_dataset": row["source_dataset"],
                "construction_type": row["construction_type"],
                "expected": row["expected"],
                "predicted": row["predicted"],
                "correct": row["expected"] == row["predicted"],
                "class_probabilities": json.dumps(
                    row["output"].get("class_probabilities", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            })


def main() -> None:
    cv = load_cv_module()
    config = load_json(ROOT / "candidates" / "candidate_config.json")
    model = joblib.load(ROOT / "candidates" / "candidate_model.joblib")

    v01 = PROJECT / "experiments" / "evidence_sufficiency_v0_1"
    v02 = PROJECT / "experiments" / "evidence_sufficiency_v0_2"
    datasets = {
        "v0_2_real_development": normalize(
            load_json(v02 / "development" / "real_development_set.json"),
            "V0_2_REAL_DEVELOPMENT", "REAL_ADJUDICATED"),
        "v0_2_real_internal_holdout": normalize(
            load_json(v02 / "evaluation" / "real_internal_holdout.json"),
            "V0_2_REAL_INTERNAL_HOLDOUT", "REAL_ADJUDICATED"),
        "v0_2_synthetic_development": normalize(
            load_json(v02 / "development" / "synthetic_development_set.json"),
            "V0_2_SYNTHETIC_DEVELOPMENT", "SYNTHETIC_CONSTRUCTED"),
        "v0_2_synthetic_holdout": normalize(
            load_json(v02 / "evaluation" / "synthetic_stress_holdout.json"),
            "V0_2_SYNTHETIC_HOLDOUT", "SYNTHETIC_CONSTRUCTED"),
        "legacy_synthetic_v0_1": normalize(
            load_json(v01 / "evaluation" / "synthetic_stress_set.json"),
            "LEGACY_SYNTHETIC_V0_1", "SYNTHETIC_CONSTRUCTED"),
        "historical_17": normalize(
            load_json(v01 / "development" / "adjudicated_development_set.json")
            + load_json(v01 / "evaluation" / "adjudicated_holdout.json"),
            "HISTORICAL_17", "REAL_ADJUDICATED"),
    }

    all_predictions = {}
    reports = {
        "candidate_variant": config["variant"],
        "evaluation_status": "SEEN_REGRESSION",
        "datasets": {},
    }
    for name, rows in datasets.items():
        predictions = cv.model_predict(rows, model, config["config"])
        all_predictions[name] = predictions
        reports["datasets"][name] = simple_metrics(cv, predictions)

    correction_ids = set()
    with (v01 / "results" / "historical_correction_regression.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        correction_ids = {row["sample_id"] for row in csv.DictReader(handle)}
    correction_predictions = [
        row for row in all_predictions["historical_17"]
        if row["sample_id"] in correction_ids
    ]
    reports["historical_correction_9"] = simple_metrics(cv, correction_predictions)

    old = {
        "v0_2_real_development": load_json(v02 / "results" / "real_development_metrics.json"),
        "v0_2_real_internal_holdout": load_json(v02 / "results" / "real_internal_holdout_metrics.json"),
        "v0_2_synthetic_development": load_json(v02 / "results" / "synthetic_development_metrics.json"),
        "v0_2_synthetic_holdout": load_json(v02 / "results" / "synthetic_stress_holdout_metrics.json"),
        "legacy_synthetic_v0_1": load_json(v02 / "results" / "legacy_synthetic_v0_1_regression.json")["metrics"],
        "historical_17": load_json(v02 / "results" / "historical_17_regression.json")["metrics"],
    }
    comparison = {
        "evaluation_status": "SEEN_REGRESSION",
        "sets": {
            name: {"v0_2": old[name], "v0_3": reports["datasets"][name]}
            for name in old
        },
        "legacy_same_set_false_sufficient": {
            "v0_1": {"count": 7, "denominator": 40, "rate": 7 / 40},
            "v0_2": {"count": 6, "denominator": 40, "rate": 6 / 40},
            "v0_3": reports["datasets"]["legacy_synthetic_v0_1"]["false_sufficient"],
        },
    }

    (ROOT / "results" / "historical_regression_metrics.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "results" / "v0_2_vs_v0_3_metrics.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    flat_predictions = [row for rows in all_predictions.values() for row in rows]
    write_predictions(ROOT / "results" / "historical_regression_predictions.csv", flat_predictions)
    print(json.dumps({
        "candidate": config["variant"],
        "dataset_metrics": {
            name: {
                "accuracy": metric["accuracy"],
                "sufficient_recall": metric["sufficient_recall"],
                "false_sufficient": metric["false_sufficient"],
            }
            for name, metric in reports["datasets"].items()
        },
        "correction_9_accuracy": reports["historical_correction_9"]["accuracy"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
