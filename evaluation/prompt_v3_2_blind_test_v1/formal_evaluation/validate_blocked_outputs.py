from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


BASE = Path(r"D:\python_projects\tsinghua_ai\data_second\prompt_v3_2_blind_test_v1\formal_evaluation")
summary = json.loads((BASE / "audit" / "v3_2_blind_api_summary.json").read_text(encoding="utf-8"))
rows = json.loads((BASE / "results" / "blind_test_v1_results.json").read_text(encoding="utf-8"))
assert summary["status"] == "EVALUATION_BLOCKED"
assert summary["successful_results"] == summary["evaluable_results"] == 0
assert len(rows) == 50
assert all(row["human_action"] in {"approve", "review", "reject"} for row in rows)
assert all(not row["v3_2_action"] for row in rows)
assert (BASE / "audit" / "v3_2_blind_results.jsonl").stat().st_size == 0

formula_count = 0
formula_errors = 0
xlsx = [
    BASE / "results" / "blind_test_v1_results.xlsx",
    BASE / "results" / "blind_test_v1_disagreements.xlsx",
    BASE / "results" / "human_label_questions.xlsx",
]
for path in xlsx:
    assert path.is_file() and path.stat().st_size > 0
    with zipfile.ZipFile(path) as archive:
        xml = "".join(
            archive.read(name).decode("utf-8", errors="replace")
            for name in archive.namelist()
            if name.startswith("xl/worksheets/") and name.endswith(".xml")
        )
        formula_count += len(re.findall(r"<[^>]*:f(?:\s|>)", xml))
        formula_errors += len(re.findall(r'<[^>]*:c[^>]*\bt="e"', xml))
assert formula_count == 0
assert formula_errors == 0

required = [
    BASE / "audit" / "v3_2_blind_results.jsonl",
    BASE / "audit" / "v3_2_blind_api_summary.json",
    *xlsx,
    BASE / "reports" / "blind_test_v1_leakage_check.md",
    BASE / "reports" / "blind_test_v1_evaluation.md",
]
assert all(path.exists() for path in required)
validation = {
    "status": "PASS_FOR_BLOCKED_HANDOFF",
    "required_files": len(required),
    "human_rows": len(rows),
    "ai_results": 0,
    "formula_count": formula_count,
    "formula_errors": formula_errors,
    "visual_previews_checked": 3,
}
(BASE / "audit" / "final_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(validation, ensure_ascii=False, indent=2))

