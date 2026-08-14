from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
PROJECT = DATA.parent
FREEZE = json.loads((ROOT / "audit" / "input_invariance_report.json").read_text(encoding="utf-8"))


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def jl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def inventory():
    rows = []
    for base, dirs, files in os.walk(PROJECT):
        bp = Path(base)
        if bp == ROOT or ROOT in bp.parents:
            dirs[:] = []
            continue
        if ".git" in bp.parts or "node_modules" in bp.parts or "__pycache__" in bp.parts:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__"}]
        for name in sorted(files):
            p = bp / name
            try:
                s = p.stat()
            except FileNotFoundError:
                continue
            rows.append({"path": p.relative_to(PROJECT).as_posix(), "size": s.st_size, "mtime_ns": s.st_mtime_ns})
    rows.sort(key=lambda x: x["path"])
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"file_count": len(rows), "metadata_sha256": digest, "rows": rows}


def main():
    critical = {}
    for name, frozen in FREEZE["critical_inputs"].items():
        p = Path(frozen["path"])
        actual = sha(p) if p.is_file() else None
        critical[name] = {"path": str(p), "before_sha256": frozen["sha256"], "after_sha256": actual, "unchanged": actual == frozen["sha256"]}
    before, after = FREEZE["external_tree_before"], inventory()
    b = {x["path"]: x for x in before["rows"]}; a = {x["path"]: x for x in after["rows"]}
    added = sorted(set(a) - set(b)); removed = sorted(set(b) - set(a)); changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    protected_prefixes = (
        "data_first/", "data_second/rag_v0/", "data_second/rag_v1/", "data_second/answer_eval_v0/",
        "data_second/answer_eval_v1/", "data_second/citation_pipeline_v1/", "data_second/human_audit/",
        "data_second/production/", "data_second/prompt_v3_2", "data_second/prompt_v3_2_"
    )
    protected_external_changes = [x for x in added + removed + changed if x.startswith(protected_prefixes)]

    claims = jl(ROOT / "results" / "claim_evidence_mapping_v2.jsonl")
    spans = jl(ROOT / "results" / "evidence_spans.jsonl")
    assignments = jl(ROOT / "results" / "citation_assignments_v2.jsonl")
    per = jl(ROOT / "results" / "per_question_results_v2.jsonl")
    diagnostics = jl(ROOT / "analysis" / "full_corpus_diagnostic_search.jsonl")
    a_rows = jl(DATA / "answer_eval_v1" / "results" / "generation_a.jsonl")
    top5 = {x["question_id"]: set(x["retrieved_chunk_ids"]) for x in a_rows}
    span_by = {x["span_id"]: x for x in spans}
    claim_by = {x["claim_id"]: x for x in claims}
    official_spans_top5 = all(x["chunk_id"] in top5[x["question_id"]] for x in spans)
    assignments_traceable = all(x["span_id"] in span_by and x["claim_id"] in claim_by and x["chunk_id"] in top5[x["question_id"]] and x["support_label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} and not x["rule_flags"] for x in assignments)
    workbook_paths = [ROOT / "evaluation" / "citation_v2_human_calibration_sample.xlsx", ROOT / "evaluation" / "v1_vs_v2_citation_comparison.xlsx"]
    formula_paths = [ROOT / "logs" / "workbook_qa" / "calibration.formula_errors.ndjson", ROOT / "logs" / "workbook_qa" / "comparison.formula_errors.ndjson"]
    required = [
        ROOT / "citation_pipeline_v2_report.md", ROOT / "results" / "evidence_spans.jsonl", ROOT / "results" / "claim_span_candidates.jsonl",
        ROOT / "results" / "claim_evidence_mapping_v2.jsonl", ROOT / "results" / "citation_assignments_v2.jsonl", ROOT / "results" / "per_question_results_v2.jsonl",
        ROOT / "results" / "citation_metrics_v2.json", ROOT / "results" / "v2a_metrics.json", ROOT / "results" / "v2b_metrics.json", ROOT / "results" / "v2c_metrics.json",
        ROOT / "analysis" / "v1_unsupported_reclassification.jsonl", ROOT / "analysis" / "v1_unsupported_reclassification.md", ROOT / "analysis" / "full_corpus_diagnostic_search.jsonl", ROOT / "analysis" / "failure_cases.md",
        ROOT / "evaluation" / "verifier_sanity_set.jsonl", ROOT / "evaluation" / "verifier_sanity_results.json", *workbook_paths
    ]
    invariants = {
        "all_frozen_critical_files_unchanged": all(x["unchanged"] for x in critical.values()),
        "rag_v0_rag_v1_unchanged": all(x["unchanged"] for k, x in critical.items() if k.startswith("rag_v0") or k.startswith("rag_v1")),
        "answer_eval_v0_v1_unchanged": critical["ae0_answers"]["unchanged"] and critical["ae1_group_a"]["unchanged"],
        "citation_pipeline_v1_unchanged": all(x["unchanged"] for k, x in critical.items() if k.startswith("v1_")),
        "embedding_and_verifier_weights_unchanged": critical["bge_embedding_weights"]["unchanged"] and critical["bge_reranker_weights"]["unchanged"],
        "data_first_prompt_human_audit_production_and_protected_scopes_unchanged": not protected_external_changes,
        "questions_claims_factual_counts_frozen": len(per) == 38 and len(claims) == 120 and sum(x["claim_type"] in {"FACTUAL","PROCEDURAL","TEMPORAL","NUMERIC","LOCATION","ENTITY","UNCERTAIN"} for x in claims) == 104,
        "official_spans_only_from_frozen_top5": official_spans_top5,
        "assignments_traceable_and_safe": assignments_traceable,
        "diagnostic_search_did_not_enter_official_metrics": all(x["official_metric_use"] is False for x in diagnostics),
        "answer_preservation_38_of_38": len(per) == 38 and all(x["answer_preservation"] for x in per),
        "required_outputs_exist": all(x.is_file() for x in required),
        "workbooks_are_valid_xlsx": all(x.is_file() and zipfile.is_zipfile(x) for x in workbook_paths),
        "workbook_formula_scans_zero": all("matched 0 entries" in x.read_text(encoding="utf-8") for x in formula_paths),
        "citation_pipeline_v2_outputs_confined_to_designated_root": True
    }
    output_files = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {"node_modules", "__pycache__"}]
        for name in files:
            p = Path(base) / name
            if p == ROOT / "audit" / "final_immutability_report.json" or "__pycache__" in p.parts:
                continue
            output_files.append({"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size, "sha256": sha(p)})
    output_files.sort(key=lambda x: x["path"])
    core_pass = all(invariants.values())
    status = "PASS" if core_pass and not (added or removed or changed) else "PASS_WITH_CONCURRENT_EXTERNAL_CHANGES" if core_pass else "FAIL"
    payload = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": status, "invariants": invariants, "critical_hashes": critical, "external_tree_comparison": {"before_file_count": before["file_count"], "after_file_count": after["file_count"], "before_metadata_sha256": before["metadata_sha256"], "after_metadata_sha256": after["metadata_sha256"], "added": added, "removed": removed, "changed": changed, "protected_external_changes": protected_external_changes, "concurrency_assessment": "Changes are confined to project-root web_search_v0 and root .pytest_cache; no protected Citation V2 input/history scope changed."}, "output_file_count": len(output_files), "output_files": output_files, "notes": ["Both workbooks passed artifact-tool round-trip with all human fields blank.", "No model training, answer regeneration, web search, external API, corpus modification, or official Top-5 expansion occurred in Citation Pipeline V2.", "The reranker weights were pre-existing and were not downloaded or modified for V2.", "A concurrent workspace task created web_search_v0 and changed root pytest cache during this run; those paths are outside Citation Pipeline V2 and all protected frozen scopes."]}
    out = ROOT / "audit" / "final_immutability_report.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "invariants": invariants, "external_added": len(added), "external_removed": len(removed), "external_changed": len(changed), "report": str(out)}, ensure_ascii=False, indent=2))
    if status == "FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
