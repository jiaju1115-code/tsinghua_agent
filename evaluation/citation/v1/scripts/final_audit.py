from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
FREEZE = json.loads((ROOT / "audit" / "input_freeze.json").read_text(encoding="utf-8"))


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def external_inventory():
    rows = []
    for base, dirs, files in os.walk(DATA):
        bp = Path(base)
        if bp == ROOT or ROOT in bp.parents:
            dirs[:] = []
            continue
        for name in sorted(files):
            p = bp / name
            try:
                stat = p.stat()
            except FileNotFoundError:
                continue
            rows.append({"path": p.relative_to(DATA).as_posix(), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    rows.sort(key=lambda x: x["path"])
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"file_count": len(rows), "metadata_sha256": digest, "rows": rows}


def main():
    critical = {}
    for name, frozen in FREEZE["critical_inputs"].items():
        p = Path(frozen["path"])
        actual = sha(p) if p.is_file() else None
        critical[name] = {
            "path": str(p),
            "before_sha256": frozen["sha256"],
            "after_sha256": actual,
            "unchanged": actual == frozen["sha256"],
        }

    before = FREEZE["external_tree_before"]
    after = external_inventory()
    before_by = {x["path"]: x for x in before["rows"]}
    after_by = {x["path"]: x for x in after["rows"]}
    added = sorted(set(after_by) - set(before_by))
    removed = sorted(set(before_by) - set(after_by))
    changed = sorted(k for k in set(before_by) & set(after_by) if before_by[k] != after_by[k])

    workbook = ROOT / "evaluation" / "a_vs_citation_pipeline_v1.xlsx"
    formula_scan = (ROOT / "logs" / "workbook_qa" / "workbook.formula_errors.ndjson").read_text(encoding="utf-8")
    workbook_ok = workbook.is_file() and zipfile.is_zipfile(workbook)
    output_files = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != "node_modules" and d != "__pycache__"]
        for name in files:
            p = Path(base) / name
            if "__pycache__" in p.parts:
                continue
            if p == ROOT / "audit" / "final_immutability_report.json":
                continue
            output_files.append({"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size, "sha256": sha(p)})
    output_files.sort(key=lambda x: x["path"])

    invariants = {
        "rag_v0_unchanged": critical["rag_v0_chunks"]["unchanged"],
        "rag_v1_unchanged": all(v["unchanged"] for k, v in critical.items() if k.startswith("rag_v1_")),
        "answer_eval_v0_unchanged": critical["ae0_answers"]["unchanged"],
        "answer_eval_v1_unchanged": all(critical[k]["unchanged"] for k in ("ae1_group_a", "ae1_group_b", "ae1_ab_metrics")),
        "model_weights_unchanged": critical["bge_weights"]["unchanged"],
        "prompt_human_audit_production_and_all_other_external_files_unchanged": not added and not removed and not changed,
        "a_answers_exact_38_of_38": FREEZE["counts"]["answers_exact_match"] == 38 and critical["ae0_answers"]["unchanged"] and critical["ae1_group_a"]["unchanged"],
        "all_new_outputs_under_citation_pipeline_v1": not added,
        "workbook_is_valid_xlsx_container": workbook_ok,
        "workbook_formula_error_scan_zero": "matched 0 entries" in formula_scan,
    }
    status = "PASS" if all(invariants.values()) else "FAIL"
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "invariants": invariants,
        "critical_hashes": critical,
        "external_tree_comparison": {
            "before_file_count": before["file_count"],
            "after_file_count": after["file_count"],
            "before_metadata_sha256": before["metadata_sha256"],
            "after_metadata_sha256": after["metadata_sha256"],
            "added": added,
            "removed": removed,
            "changed": changed,
        },
        "output_file_count_excluding_runtime_junction_and_pycache": len(output_files),
        "output_files": output_files,
        "notes": [
            "Human fields were checked blank by artifact-tool XLSX round-trip during workbook creation.",
            "Human-validated citation correctness remains N/A.",
            "No generation model was called and no model was trained.",
        ],
    }
    out = ROOT / "audit" / "final_immutability_report.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "invariants": invariants, "external_added": len(added), "external_removed": len(removed), "external_changed": len(changed), "report": str(out)}, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
