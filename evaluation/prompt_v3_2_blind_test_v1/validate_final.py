from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path


ROOT = Path(r"D:\python_projects\tsinghua_ai\data_second")
BASE = ROOT / "prompt_v3_2_blind_test_v1"


def load(relative: str):
    return json.loads((BASE / relative).read_text(encoding="utf-8"))


baseline = json.loads(
    (ROOT / "public_rebuild_v1" / "audit" / "public_rebuild_v1_all_audited.json").read_text(encoding="utf-8")
)
exclusions = load("manifest/blind_test_exclusion_list.json")
pool = load("manifest/blind_candidate_pool.json")
manifest = load("samples/blind_test_v1_sample_manifest.json")
human = load("human_label/blind_test_v1_human_label.json")

assert len(baseline) == 217
assert len(exclusions) == 30
assert len(pool) == 187
assert len(manifest) == len(human) == 50
assert sum(row["source_group"] == "random" for row in manifest) == 25
assert sum(row["source_group"] == "targeted" for row in manifest) == 25

excluded_ids = {row["id"] for row in exclusions}
excluded_urls = {row["url"] for row in exclusions}
excluded_normalized = {row["normalized_url"] for row in exclusions}
assert not ({row["original_id"] for row in manifest} & excluded_ids)
assert not ({row["url"] for row in manifest} & excluded_urls)
assert not ({row["normalized_url"] for row in manifest} & excluded_normalized)
assert len({row["original_id"] for row in manifest}) == 50
assert len({row["normalized_url"] for row in manifest}) == 50
assert len({row["content_sha256"] for row in manifest}) == 50

human_fields = [
    "human_action", "human_category", "human_reject_type", "human_topic_relevance",
    "human_time_status", "human_valid_until", "human_note",
]
for row in human:
    assert all(row[field] == "" for field in human_fields)
    assert row["category_hint"] in {"图书馆站点", "信息化技术中心站点", "校园安全与秩序站点", "清华公开站点"}
    content_path = BASE / row["content_file"]
    assert content_path.is_file() and content_path.stat().st_size > 0
    matching = next(item for item in manifest if item["blind_id"] == row["blind_id"])
    normalized_content = content_path.read_text(encoding="utf-8")
    assert normalized_content == row["cleaned_content"]
    assert hashlib.sha256(normalized_content.encode("utf-8")).hexdigest() == matching["content_sha256"]

for forbidden in ("old_V2_action", "V2_action", "V3_action", "ai_reason", "ai_category", "ai_topic_relevance"):
    assert all(forbidden not in row for row in human)

xlsx_files = [
    BASE / "manifest" / "blind_test_exclusion_list.xlsx",
    BASE / "manifest" / "blind_candidate_pool.xlsx",
    BASE / "samples" / "blind_test_v1_sample_manifest.xlsx",
    BASE / "human_label" / "blind_test_v1_human_label.xlsx",
]
formula_count = 0
formula_error_count = 0
human_has_data_validation = False
for index, workbook in enumerate(xlsx_files):
    assert workbook.is_file() and workbook.stat().st_size > 0
    with zipfile.ZipFile(workbook) as archive:
        worksheets = [name for name in archive.namelist() if name.startswith("xl/worksheets/") and name.endswith(".xml")]
        xml = "".join(archive.read(name).decode("utf-8", errors="replace") for name in worksheets)
        formula_count += len(re.findall(r"<f(?:\s|>)", xml))
        formula_error_count += len(re.findall(r'<c[^>]*\bt="e"', xml))
        if index == 3:
            human_has_data_validation = "dataValidations" in xml

assert formula_count == 0
assert formula_error_count == 0
assert human_has_data_validation

result = {
    "baseline": len(baseline),
    "exclusions": len(exclusions),
    "candidate_pool": len(pool),
    "sample_total": len(manifest),
    "random": 25,
    "targeted": 25,
    "historical_leak_by_id_url_normalized_url": 0,
    "unique_ids": len({row["original_id"] for row in manifest}),
    "unique_normalized_urls": len({row["normalized_url"] for row in manifest}),
    "unique_content_hashes": len({row["content_sha256"] for row in manifest}),
    "human_rows_all_blank": len(human),
    "content_files": len(list((BASE / "samples" / "content").glob("*.md"))),
    "xlsx_formula_count": formula_count,
    "xlsx_formula_error_count": formula_error_count,
    "human_data_validation": human_has_data_validation,
}
(BASE / "audit" / "final_validation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
