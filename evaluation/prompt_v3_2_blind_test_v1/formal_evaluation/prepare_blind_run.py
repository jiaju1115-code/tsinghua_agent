from __future__ import annotations

import hashlib
import json
from pathlib import Path


SECOND = Path(r"D:\python_projects\tsinghua_ai\data_second")
BASE = SECOND / "prompt_v3_2_blind_test_v1"
FORMAL = BASE / "formal_evaluation"
AUDIT = FORMAL / "audit"
REPORTS = FORMAL / "reports"
PROMPT_PATH = SECOND / "prompt_v3_2_test" / "prompt" / "prompt_v3_2.md"
MANIFEST_PATH = BASE / "samples" / "blind_test_v1_sample_manifest.json"
EXCLUSION_PATH = BASE / "manifest" / "blind_test_exclusion_list.json"
HUMAN_PREFLIGHT_PATH = AUDIT / "human_label_preflight.json"

AUDIT.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
exclusions = json.loads(EXCLUSION_PATH.read_text(encoding="utf-8"))
human_preflight = json.loads(HUMAN_PREFLIGHT_PATH.read_text(encoding="utf-8"))

excluded_ids = {row["id"] for row in exclusions}
excluded_urls = {row["url"] for row in exclusions}
excluded_normalized = {row["normalized_url"] for row in exclusions}
sample_ids = {row["original_id"] for row in manifest}
sample_urls = {row["url"] for row in manifest}
sample_normalized = {row["normalized_url"] for row in manifest}

leaks_by_id = sorted(sample_ids & excluded_ids)
leaks_by_url = sorted(sample_urls & excluded_urls)
leaks_by_normalized = sorted(sample_normalized & excluded_normalized)
duplicate_urls = len(manifest) - len(sample_urls)
duplicate_normalized = len(manifest) - len(sample_normalized)

prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
prompt_sha256 = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest().upper()
sample_mentions = [row["original_id"] for row in manifest if row["original_id"] in prompt_text]

inputs = []
for row in manifest:
    content_file = BASE / row["content_file"]
    content = content_file.read_text(encoding="utf-8")
    assert hashlib.sha256(content.encode("utf-8")).hexdigest() == row["content_sha256"]
    inputs.append({
        "blind_id": row["blind_id"],
        "original_id": row["original_id"],
        "title": row["title"],
        "url": row["url"],
        "source_domain": row["domain"],
        "content_file": row["content_file"],
        "content_sha256": row["content_sha256"],
    })

input_path = AUDIT / "blind_model_inputs.json"
input_path.write_text(json.dumps(inputs, ensure_ascii=False, indent=2), encoding="utf-8")
input_sha256 = hashlib.sha256(input_path.read_bytes()).hexdigest().upper()

checks = {
    "sample_count": len(manifest),
    "historical_leaks_by_id": len(leaks_by_id),
    "historical_leaks_by_url": len(leaks_by_url),
    "historical_leaks_by_normalized_url": len(leaks_by_normalized),
    "duplicate_url_count": duplicate_urls,
    "duplicate_normalized_url_count": duplicate_normalized,
    "human_label_rows": human_preflight["dataRows"],
    "human_action_valid_count": human_preflight["actionValidCount"],
    "human_file_sha256": human_preflight["sha256"],
    "prompt_sha256": prompt_sha256,
    "prompt_sample_id_mentions": sample_mentions,
    "model_input_sha256": input_sha256,
    "model_input_fields": list(inputs[0]),
    "human_or_ai_label_fields_in_model_input": [],
}
assert checks["sample_count"] == 50
assert not leaks_by_id and not leaks_by_url and not leaks_by_normalized
assert duplicate_urls == duplicate_normalized == 0
assert human_preflight["actionValidCount"] == 50
assert not sample_mentions

(AUDIT / "leakage_check.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")

report = f"""# Prompt V3.2 Blind Test V1 泄漏检查

## 结论

`PASS — 0 SAMPLE LEAKAGE`

## 检查结果

- 冻结样本：50 条。
- 与历史 30 条调参集按 ID 交叉：0 条。
- 按原始 URL 交叉：0 条。
- 按 normalized URL 交叉：0 条。
- 样本内 URL 重复：0 条。
- 样本内 normalized URL 重复：0 条。
- 冻结人工文件 action 完整度：50/50。
- 人工文件 SHA-256：`{human_preflight['sha256']}`。
- Prompt V3.2 SHA-256：`{prompt_sha256}`。
- Prompt 中出现本批样本 ID：0 条。
- 独立模型输入仅含 blind_id、original_id、title、url、source_domain、content_file、content_sha256；不含人工标签、人工备注或任何历史 AI 判断。
- 模型输入清单 SHA-256：`{input_sha256}`。

## 阶段锁定

泄漏检查在 API 调用前完成。后续模型运行仅读取独立输入清单和正文文件；冻结人工标签只会在 AI 原始结果全部保存后用于合并评估。
"""
(REPORTS / "blind_test_v1_leakage_check.md").write_text(report, encoding="utf-8")
print(json.dumps(checks, ensure_ascii=False, indent=2))

