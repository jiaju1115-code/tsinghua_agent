"""Verify frozen critical inputs and every pre-existing external file are unchanged."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DATA = Path(r"D:\python_projects\tsinghua_ai\data_second")
ROOT = DATA / "answer_eval_v0"
FREEZE = ROOT / "audit" / "input_freeze.json"
OUT = ROOT / "audit" / "final_immutability_report.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory() -> list[dict]:
    rows = []
    for path in DATA.rglob("*"):
        if not path.is_file() or ROOT in path.parents:
            continue
        st = path.stat()
        rows.append({
            "path": path.relative_to(DATA).as_posix(),
            "size": st.st_size,
            "mtime_ns": st.st_mtime_ns,
        })
    return sorted(rows, key=lambda x: x["path"])


def main() -> None:
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    before = frozen["external_tree_before"]["rows"]
    after = inventory()
    before_map = {r["path"]: r for r in before}
    after_map = {r["path"]: r for r in after}
    added = sorted(set(after_map) - set(before_map))
    removed = sorted(set(before_map) - set(after_map))
    changed = [p for p in sorted(set(before_map) & set(after_map)) if before_map[p] != after_map[p]]

    critical = {}
    for name, info in frozen["critical_inputs"].items():
        path = Path(info["path"])
        exists = path.exists()
        actual = sha(path) if exists else None
        critical[name] = {
            "path": str(path), "exists": exists,
            "expected_sha256": info["sha256"], "actual_sha256": actual,
            "unchanged": exists and actual == info["sha256"],
        }

    all_outputs = [p for p in ROOT.rglob("*") if p.is_file()]
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not (added or removed or changed) and all(v["unchanged"] for v in critical.values()) else "FAIL",
        "external_tree": {
            "before_file_count": len(before), "after_file_count": len(after),
            "added": added, "removed": removed, "metadata_changed": changed,
        },
        "critical_inputs": critical,
        "output_scope": {
            "all_new_outputs_under_answer_eval_v0": all(ROOT in p.parents for p in all_outputs),
            "output_file_count_before_final_report": len(all_outputs),
        },
        "protected_areas": {
            "rag_v0_modified": any(p.startswith("rag_v0/") for p in added + removed + changed),
            "rag_v1_modified": any(p.startswith("rag_v1/") for p in added + removed + changed),
            "human_audit_modified": any(p.startswith("human_audit/") for p in added + removed + changed),
            "prompt_v3_2_modified": any("prompt_v3_2" in p for p in added + removed + changed),
            "production_modified": any(p.startswith("production/") for p in added + removed + changed),
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
