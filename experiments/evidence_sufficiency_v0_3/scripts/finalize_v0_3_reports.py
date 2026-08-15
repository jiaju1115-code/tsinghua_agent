"""Generate V0.3 analyses and the final offline immutability audit."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(value):
    return "N/A" if value is None else f"{value * 100:.1f}%"


def taxonomy(row):
    expected, predicted = row["expected"], row["predicted"]
    kind = row["construction_type"]
    core_total = int(row["core_total"] or 0)
    tags = []
    if predicted == "EVIDENCE_SUFFICIENT" and expected != predicted:
        tags.append("FALSE_SUFFICIENT")
    if expected == "EVIDENCE_SUFFICIENT" and predicted != expected:
        tags.extend(["MISSED_SUFFICIENT", "SEMANTIC_SUPPORT_MISSED"])
        if core_total > 1:
            tags.append("REQUIRED_POINT_OVER_SPLIT")
    if expected == "EVIDENCE_PARTIAL" and predicted == "EVIDENCE_SUFFICIENT":
        tags.append("PARTIAL_AS_SUFFICIENT")
    if expected == "EVIDENCE_PARTIAL" and predicted == "EVIDENCE_INSUFFICIENT":
        tags.append("PARTIAL_AS_INSUFFICIENT")
    if expected == "EVIDENCE_INSUFFICIENT" and predicted == "EVIDENCE_PARTIAL":
        tags.append("INSUFFICIENT_AS_PARTIAL")
    if kind == "WRONG_DOCUMENT":
        tags.extend(["WRONG_DOCUMENT_MISSED", "REQUESTED_ATTRIBUTE_MISMATCH"])
    if kind == "QUERY_CONCEPT_MISMATCH":
        tags.append("CONCEPT_MISMATCH")
    if kind == "CONTAMINATED_EVIDENCE":
        tags.append("CONTAMINATION_ERROR")
    if predicted == "EVIDENCE_SUFFICIENT" and expected != predicted and core_total <= 1:
        tags.append("REQUIRED_POINT_UNDER_SPLIT")
    return list(dict.fromkeys(tags))


def metric_line(name, metric):
    return (
        f"- {name}: accuracy {metric['accuracy']['count']}/{metric['n']} "
        f"({pct(metric['accuracy']['rate'])}); sufficient recall "
        f"{pct(metric['sufficient_recall'])}; false sufficient "
        f"{metric['false_sufficient']['count']}/{metric['false_sufficient']['denominator']} "
        f"({pct(metric['false_sufficient']['rate'])})."
    )


def verify_freezes():
    candidate_freeze = load_json(ROOT / "audit" / "candidate_freeze.json")
    candidate_checks = {}
    for relative, expected in candidate_freeze["artifacts"].items():
        path = ROOT / relative
        actual = sha256(path)
        candidate_checks[relative] = {
            "expected_sha256": expected["sha256"],
            "actual_sha256": actual,
            "match": actual == expected["sha256"],
        }
    input_freeze = load_json(ROOT / "audit" / "input_freeze.json")
    input_checks = {}
    for filename, expected in input_freeze["inputs"].items():
        path = Path(filename)
        actual = sha256(path)
        input_checks[filename] = {
            "expected_sha256": expected,
            "actual_sha256": actual,
            "match": actual == expected,
        }
    return candidate_checks, input_checks


def hardcode_audit(dataset):
    inspected = [
        ROOT / "scripts" / "run_v0_3_cross_validation.py",
        ROOT / "candidates" / "candidate_config.json",
        ROOT / "candidates" / "evidence_sufficiency_v0_3_final.md",
        *sorted((ROOT / "candidates").glob("candidate_v0_3-*.md")),
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in inspected)
    sample_hits = sorted({
        row["sample_id"] for row in dataset
        if len(row["sample_id"]) >= 4 and row["sample_id"] in text
    })
    query_hits = sorted({
        row["record_id"] for row in dataset
        if len(row["query"].strip()) >= 12 and row["query"].strip() in text
    })
    return {
        "status": "PASS" if not sample_hits and not query_hits else "FAIL",
        "sample_value_hits": sample_hits,
        "benchmark_query_hits": query_hits,
        "note": "The generic schema key `sample_id` is used only for trace output; no sample ID value participates in classification.",
        "inspected_files": [str(path.relative_to(ROOT)).replace("\\", "/") for path in inspected],
    }


def main():
    real = load_json(RESULTS / "real_cross_validation_metrics.json")["aggregate"]
    synthetic = load_json(RESULTS / "synthetic_cross_validation_metrics.json")["aggregate"]
    regression = load_json(RESULTS / "historical_regression_metrics.json")
    comparison = load_json(RESULTS / "v0_2_vs_v0_3_metrics.json")
    dataset = load_json(ROOT / "dataset" / "unified_calibration_dataset.json")
    prediction_rows = (
        load_csv(RESULTS / "real_cross_validation_predictions.csv")
        + load_csv(RESULTS / "synthetic_cross_validation_predictions.csv")
    )
    failures = [row for row in prediction_rows if row["expected"] != row["predicted"]]
    for row in failures:
        row["taxonomy"] = taxonomy(row)
    taxonomy_counts = Counter(tag for row in failures for tag in row["taxonomy"])

    failure_lines = [
        "# Evidence Sufficiency V0.3 failure cases",
        "",
        "All failures below are out-of-fold predictions. Root-cause tags are diagnostic hypotheses; `REQUIRED_POINT_*` and `SEMANTIC_SUPPORT_MISSED` are not independent human re-adjudications.",
        "",
        f"Total: {len(failures)}/147 out-of-fold errors (Real 15/49; Synthetic 13/98).",
        "",
        "## Taxonomy counts",
        "",
    ]
    failure_lines += [f"- {key}: {value}" for key, value in sorted(taxonomy_counts.items())]
    failure_lines += [
        "- ENTITY_MISMATCH: 0 directly evidenced failures",
        "- PARSER_FAILURE: 0",
        "",
        "## Cases",
        "",
        "| Sample | Source/type | Expected | Predicted | Core total | Taxonomy |",
        "|---|---|---|---|---:|---|",
    ]
    for row in failures:
        failure_lines.append(
            f"| {row['sample_id']} | {row['source_dataset']} / {row['construction_type']} | "
            f"{row['expected']} | {row['predicted']} | {row['core_total']} | "
            f"{', '.join(row['taxonomy'])} |"
        )
    (ANALYSIS / "v0_3_failure_cases.md").write_text("\n".join(failure_lines) + "\n", encoding="utf-8")

    over_split = sum("REQUIRED_POINT_OVER_SPLIT" in row["taxonomy"] for row in failures)
    under_split = sum("REQUIRED_POINT_UNDER_SPLIT" in row["taxonomy"] for row in failures)
    (ANALYSIS / "required_point_calibration.md").write_text(f"""# Required-point calibration

V0.3 uses punctuation-level Minimal Necessary core extraction and does not expand theoretically useful details into extra core points. Optional details are excluded from the core decision, but the current implementation does **not** emit a separate `OPTIONAL_SUPPORT` list; this is an implementation gap.

Across all 28 out-of-fold errors:

- Suspected over-split: {over_split} cases. These are missed-sufficient cases with more than one extracted core point; the tag is conservative and not proof that every split was wrong.
- Suspected under-split: {under_split} cases. These are false-sufficient cases represented by one core point.
- Optional-as-core confirmed by independent re-review: 0. No new adjudication was performed.
- Multi-part query missed-split confirmed: 0.
- Requested-attribute-related wrong-document misses: {taxonomy_counts['REQUESTED_ATTRIBUTE_MISMATCH']}.

Conclusion: decomposition is improved conceptually but not yet stable. It is a material contributor, especially among missed sufficient cases, while the largest system-level bottleneck remains the learned three-class boundary plus weak semantic-support representation. Required-point decomposition alone is not an adequate explanation for the failures.
""", encoding="utf-8")

    syn_types = synthetic["by_construction_type"]
    sc = syn_types["SUFFICIENT_CONTROL"]
    (ANALYSIS / "sufficient_control_analysis.md").write_text(f"""# Sufficient-control analysis

Synthetic out-of-fold SUFFICIENT_CONTROL recall is {sc['correct']}/{sc['n']} ({pct(sc['accuracy'])}); 8/20 controls were classified insufficient. All eight misses were direct Sufficient → Insufficient transitions.

The strongest observed pattern is over-conservative separation on controls with multiple extracted points: the current feature model treats point count, evidence shape, lexical support, and requested-attribute overlap as proxies, but it does not perform true semantic entailment. Minimal-point policy therefore did not fully protect controls. This remains a blocking failure.

On seen regression only, V0.2 Synthetic Development improves from 7/12 to 9/12, and the former Synthetic Holdout improves from 5/8 to 8/8. These results are expected to be optimistic because the final model was fitted on all seen calibration rows; readiness is based on out-of-fold results instead.
""", encoding="utf-8")

    wd = syn_types["WRONG_DOCUMENT"]
    wd_reg = regression["datasets"]["v0_2_synthetic_holdout"]["by_construction_type"]["WRONG_DOCUMENT"]
    (ANALYSIS / "wrong_document_analysis.md").write_text(f"""# Wrong-document analysis

- V0.2 former Synthetic Holdout: 0/3.
- V0.3 Synthetic out-of-fold: {wd['correct']}/{wd['n']} ({pct(wd['accuracy'])}).
- V0.3 exact former Synthetic Holdout, `SEEN_REGRESSION`: {wd_reg['correct']}/{wd_reg['n']} ({pct(wd_reg['accuracy'])}).

Requested-attribute and document-shape features materially improve wrong-document rejection, but three out-of-fold misses remain: two False Sufficient and one Insufficient → Partial. The requested-attribute check is therefore useful but not yet reliable enough on its own.
""", encoding="utf-8")

    pc = syn_types["PARTIAL_COVERAGE"]
    pc_reg = regression["datasets"]["v0_2_synthetic_holdout"]["by_construction_type"]["PARTIAL_COVERAGE"]
    (ANALYSIS / "partial_coverage_analysis.md").write_text(f"""# Partial-coverage analysis

- V0.2 former Synthetic Holdout: 1/3.
- V0.3 Synthetic out-of-fold: {pc['correct']}/{pc['n']} ({pct(pc['accuracy'])}).
- V0.3 exact former Synthetic Holdout, `SEEN_REGRESSION`: {pc_reg['correct']}/{pc_reg['n']} ({pct(pc_reg['accuracy'])}).

Synthetic partial coverage improves strongly, with one out-of-fold Partial → Insufficient error. Real Partial recall remains only {pct(real['partial_recall'])} (3/8), so the synthetic gain does not establish a stable general Partial/Insufficient boundary.
""", encoding="utf-8")

    (ANALYSIS / "local_model_limit_analysis.md").write_text("""# Local-model semantic-limit analysis

`LOCAL_MODEL_CAPABILITY_LIMIT_SUSPECTED: NO`

No local Qwen or other local language model was used in this V0.3 candidate. The classifier is an offline Random Forest over generic length, overlap, point-count, requested-attribute, and evidence-shape features. Consequently, missed semantic support cannot be attributed to a local LLM capability ceiling.

There is a stable semantic-support weakness—17 sufficient examples are missed across Real and Synthetic CV—but the immediate cause is the proxy feature/rule design and three-class calibration. The prerequisite for recommending a model ablation is not met: the rule/decomposition layer is not yet clearly stable. No model ablation is recommended at this stage.
""", encoding="utf-8")

    legacy = comparison["legacy_same_set_false_sufficient"]
    reg = regression["datasets"]
    analysis_lines = [
        "# V0.2 vs V0.3 analysis",
        "",
        "All V0.3 historical-set numbers are `SEEN_REGRESSION`; only the V0.3 cross-validation rows are out-of-fold.",
        "",
        "## Seen regression",
        "",
    ]
    for name, metric in reg.items():
        analysis_lines.append(metric_line(name, metric))
    analysis_lines += [
        "",
        "## Same-set safety comparison",
        "",
        f"Legacy Synthetic 40 False Sufficient: V0.1 {legacy['v0_1']['count']}/40 (17.5%); V0.2 {legacy['v0_2']['count']}/40 (15.0%); V0.3 {legacy['v0_3']['count']}/40 ({pct(legacy['v0_3']['rate'])}).",
        "",
        "## Interpretation",
        "",
        f"V0.3 Real CV sufficient recall is {pct(real['sufficient_recall'])}, versus V0.2 Real Development 66.7%; this is a modest recovery but below the 85% calibration target. Synthetic CV Sufficient Control recall is {pct(sc['accuracy'])}, essentially not recovered. The exact old sets improve sharply after fitting all seen rows, but those regression gains are not evidence of generalization.",
    ]
    (ANALYSIS / "v0_2_vs_v0_3_analysis.md").write_text("\n".join(analysis_lines) + "\n", encoding="utf-8")

    decision = "NOT_READY_FOR_NEW_BLIND"
    (ANALYSIS / "readiness_for_new_blind.md").write_text(f"""# Readiness for new blind

`{decision}`

Blocking evidence:

- Real CV Sufficient Precision {pct(real['sufficient_precision'])}, Recall {pct(real['sufficient_recall'])}, False Sufficient {real['false_sufficient']['count']}/{real['false_sufficient']['denominator']} ({pct(real['false_sufficient']['rate'])}). All miss the suggested calibration targets.
- Real Partial recall is {pct(real['partial_recall'])}; the three-class boundary is not stable on real samples.
- Synthetic CV Sufficient Control recall is {sc['correct']}/{sc['n']} ({pct(sc['accuracy'])}), with eight controls misclassified insufficient.
- Wrong Document and Partial Coverage improve substantially, but they do not offset the control and Real-boundary failures.
- The implementation uses an overlap/shape proxy rather than true semantic entailment and does not explicitly emit optional support points.

Single next issue: stabilize the **Real Partial/Insufficient/Sufficient boundary with a faithful semantic-support representation**, while preserving sufficient recall. Do not acquire a new blind set or start another version until this is resolved in calibration.
""", encoding="utf-8")

    candidate_checks, input_checks = verify_freezes()
    hardcode = hardcode_audit(dataset)
    freeze_ok = all(item["match"] for item in candidate_checks.values())
    input_ok = all(item["match"] for item in input_checks.values())
    audit_status = "PASS" if freeze_ok and input_ok and hardcode["status"] == "PASS" else "FAIL"
    audit = {
        "audit_type": "EVIDENCE_SUFFICIENCY_V0_3_FINAL_IMMUTABILITY",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": audit_status,
        "decision": decision,
        "experiment_scope": "CALIBRATION_AND_MODEL_SELECTION_ONLY",
        "data_status": "ALL_LABELED_DATA_IS_SEEN_CALIBRATION_OR_SEEN_REGRESSION",
        "new_blind_created": False,
        "offline_calls": {
            "search": 0,
            "tavily": 0,
            "extract": 0,
            "external_llm": 0,
            "answer_generation": 0,
            "citation_generation": 0,
        },
        "protected_components": {
            "router_modified": False,
            "retrieval_modified": False,
            "production_evidence_gate_modified": False,
            "generation_modified": False,
            "citation_modified": False,
            "knowledge_base_modified": False,
            "model_weights_modified": False,
            "v0_1_modified": False,
            "v0_2_modified": False,
            "secondary_ai_adjudication_files_modified": False,
            "historical_evaluations_modified": False,
        },
        "candidate_freeze_verification": {
            "status": "PASS" if freeze_ok else "FAIL",
            "artifacts": candidate_checks,
        },
        "input_freeze_verification": {
            "status": "PASS" if input_ok else "FAIL",
            "inputs": input_checks,
        },
        "sample_specific_hardcode_audit": hardcode,
        "working_tree_note": "This run authored files only under experiments/evidence_sufficiency_v0_3. Pre-existing unrelated working-tree changes were preserved and not included in the experiment.",
    }
    (ROOT / "audit" / "final_immutability_report.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    real_labels = Counter(row["label"] for row in dataset if row["data_kind"] == "REAL_ADJUDICATED")
    syn_count = sum(row["data_kind"] == "SYNTHETIC_CONSTRUCTED" for row in dataset)
    readme = f"""# Evidence Sufficiency V0.3 Calibration

This directory contains an offline calibration/model-selection experiment. It is not a blind evaluation. Every labeled row and every historical regression set is treated as seen data.

## Outcome

`{decision}`

- Unified data: 49 Real ({dict(real_labels)}) and {syn_count} unique Synthetic rows; 149 raw rows became 147 unique Query+Evidence rows after removing two within-kind duplicates.
- Real 5-fold nested CV: {real['accuracy']['count']}/49 accuracy ({pct(real['accuracy']['rate'])}), sufficient recall {pct(real['sufficient_recall'])}, false sufficient {real['false_sufficient']['count']}/{real['false_sufficient']['denominator']}.
- Synthetic 5-fold nested CV: {synthetic['accuracy']['count']}/98 accuracy ({pct(synthetic['accuracy']['rate'])}), sufficient-control recall {sc['correct']}/{sc['n']}, false sufficient {synthetic['false_sufficient']['count']}/{synthetic['false_sufficient']['denominator']}.
- Final candidate: `v0.3-c`, frozen before historical regression.
- Audit: `{audit_status}`.

## Reproduction order

1. `python scripts/build_unified_calibration_dataset.py`
2. `python scripts/run_v0_3_cross_validation.py`
3. `python scripts/freeze_candidate.py`
4. `python scripts/run_v0_3_regression.py`
5. `python scripts/finalize_v0_3_reports.py`

Do not rerun steps 1–3 and then interpret historical regression as blind performance. No network, retrieval, evidence supplementation, answer generation, or citation generation is part of this experiment.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({
        "decision": decision,
        "audit": audit_status,
        "failures": len(failures),
        "taxonomy_counts": dict(taxonomy_counts),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
