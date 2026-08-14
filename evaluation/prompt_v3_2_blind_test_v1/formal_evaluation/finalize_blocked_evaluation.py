from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


SECOND = Path(r"D:\python_projects\tsinghua_ai\data_second")
BASE = SECOND / "prompt_v3_2_blind_test_v1"
FORMAL = BASE / "formal_evaluation"
AUDIT = FORMAL / "audit"
RESULTS = FORMAL / "results"
REPORTS = FORMAL / "reports"
for folder in (AUDIT, RESULTS, REPORTS):
    folder.mkdir(parents=True, exist_ok=True)

manifest = json.loads((BASE / "samples" / "blind_test_v1_sample_manifest.json").read_text(encoding="utf-8"))
human = json.loads((AUDIT / "frozen_human_labels.json").read_text(encoding="utf-8"))
preflight = json.loads((AUDIT / "human_label_preflight.json").read_text(encoding="utf-8"))
leakage = json.loads((AUDIT / "leakage_check.json").read_text(encoding="utf-8"))
manifest_by_id = {row["blind_id"]: row for row in manifest}


def clean(value):
    text = str(value or "").strip()
    return "" if text in {"29", "30", "29.0", "30.0"} else text


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


rows = []
for source in human:
    item = manifest_by_id[source["blind_id"]]
    rows.append({
        "blind_id": source["blind_id"],
        "original_id": source["original_id"],
        "title": source["title"],
        "url": source["url"],
        "source_group": source["source_group"],
        "domain": source["domain"],
        "category_hint_internal": item["category_hint"],
        "content_type_hint_internal": item["content_type_hint"],
        "coverage_tags": item["coverage_tags"],
        "human_action": clean(source["human_action"]),
        "human_topic_relevance": clean(source["human_topic_relevance"]),
        "human_reject_type": clean(source["human_reject_type"]),
        "human_category": clean(source["human_category"]),
        "human_time_status": clean(source["human_time_status"]),
        "v3_2_action": "",
        "v3_2_topic_relevance": "",
        "v3_2_reject_type": "",
        "v3_2_category": "",
        "v3_2_content_type": "",
        "v3_2_time_status": "",
        "v3_2_valid_from": "",
        "v3_2_valid_until": "",
        "v3_2_candidate_user_question": "",
        "v3_2_reason": "",
        "action_match": "",
        "topic_relevance_match": "",
        "reject_type_match": "",
        "disagreement_type": "not_evaluated_api_blocked",
        "evaluation_note": "上游 chat completion 接口超时；没有模型结果，不得计算正式盲测指标。",
    })

assert len(rows) == 50
assert all(row["human_action"] in {"approve", "review", "reject"} for row in rows)
assert all(row["human_topic_relevance"] in {"high", "medium", "low"} for row in rows)
assert all(not row["v3_2_action"] for row in rows)

(RESULTS / "blind_test_v1_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
(RESULTS / "blind_test_v1_disagreements.json").write_text("[]\n", encoding="utf-8")
(RESULTS / "human_label_questions.json").write_text("[]\n", encoding="utf-8")
(AUDIT / "v3_2_blind_results.jsonl").write_text("", encoding="utf-8")

api_summary = {
    "status": "EVALUATION_BLOCKED",
    "blocked_reason": "UPSTREAM_CHAT_COMPLETION_READ_TIMEOUT",
    "intended_calls": 50,
    "successful_results": 0,
    "raw_results_saved": 0,
    "evaluable_results": 0,
    "initial_sandbox_attempt": {
        "successes": 0,
        "failures": 50,
        "network_request_attempts": 150,
        "actual_retries": 100,
        "failure": "WinError 10013 socket permission denied",
    },
    "escalated_batch_attempts": 2,
    "escalated_batch_raw_results": 0,
    "escalated_batches_terminated_after_seconds": [900, 1800],
    "diagnostics": {
        "tcp_443": "PASS",
        "http_head": "PASS (404 from service, endpoint reachable)",
        "authenticated_models_get": "PASS (HTTP 200)",
        "frozen_model_present": True,
        "minimal_chat_completion_probe": "FAIL ReadTimeout after 60 seconds",
    },
    "model": "gpt-5.4-mini",
    "temperature": 0.1,
    "max_concurrency": 3,
    "max_completion_tokens": 900,
    "prompt_version": "v3.2",
    "prompt_sha256": leakage["prompt_sha256"],
    "input_sha256": leakage["model_input_sha256"],
    "human_file_sha256": preflight["sha256"],
    "recorded_at": now(),
}
(AUDIT / "v3_2_blind_api_summary.json").write_text(json.dumps(api_summary, ensure_ascii=False, indent=2), encoding="utf-8")

human_actions = Counter(row["human_action"] for row in rows)
human_topics = Counter(row["human_topic_relevance"] for row in rows)
report = f"""# Prompt V3.2 Blind Test V1 正式评估报告

## 执行状态

`EVALUATION_BLOCKED — UPSTREAM_CHAT_COMPLETION_READ_TIMEOUT`

本次没有得到任何有效 Prompt V3.2 输出，因此不能计算或发布正式盲测性能指标，也不能从四个规定结论中选择 PASS/NEEDS_REVISION/FAIL。该状态是基础设施故障，不是模型性能结论。

## A. 样本与泄漏检查

- 冻结样本：50 条；random 25、targeted 25。
- 历史调参样本泄漏：0。
- URL 与 normalized URL 重复：0。
- 冻结人工文件 SHA-256：`{preflight['sha256']}`。
- Prompt V3.2 SHA-256：`{leakage['prompt_sha256']}`。
- 模型输入不含人工标签、人工备注或历史 AI 判断。

## B. 冻结人工标签

- human_action：50/50 有效；approve {human_actions.get('approve',0)}、review {human_actions.get('review',0)}、reject {human_actions.get('reject',0)}。
- human_topic_relevance：50/50 有效；high {human_topics.get('high',0)}、medium {human_topics.get('medium',0)}、low {human_topics.get('low',0)}。
- 数字 `29`、`30` 等模板残留仅在辅助字段中按 missing 处理；原始人工文件未被修改。

## C. API 执行记录

- 冻结配置：gpt-5.4-mini、temperature 0.1、concurrency 3、max_completion_tokens 900。
- 首轮沙箱内调用：0 成功、50 失败；150 次网络尝试，含 100 次重试，均为套接字权限拒绝。
- 获准联网后进行两次完整批次尝试：分别运行约 15 分钟和 30 分钟，均无单条原始结果落盘，随后终止残留进程以避免重复调用。
- TCP 443、HTTP 服务、鉴权和 `/models` 均正常；模型列表包含 `gpt-5.4-mini`。
- 不含样本数据的最小 chat completion 探针在 60 秒后 ReadTimeout，故障定位为上游生成接口。

## D. 正式指标

以下指标均为 `NOT_AVAILABLE — 0 EVALUABLE AI RESULTS`：

- action 一致率与 3×3 混淆矩阵
- approve precision / recall
- reject precision / recall
- topic_relevance 一致率
- reject_type 一致率
- low + approve
- random vs targeted
- medium 专项
- domain/content_type/category 与各定向覆盖专项
- action 分歧与 Human label 疑问

## E. 系统性错误与冻结建议

- 是否存在 Prompt 系统性错误：`NOT_EVALUABLE`。
- 是否建议冻结 Prompt V3.2：`NO — 等待同一冻结配置成功完成 50/50 API 结果后再判断`。
- 正式盲测结论：`EVALUATION_BLOCKED`，不是 `BLIND_TEST_FAIL`。

## F. 重跑要求

上游 chat completion 恢复后，应直接重跑现有冻结运行器。不得更换样本、模型、Prompt、temperature、并发或 token 参数；只有 50 条原始结果全部保存后，才能读取冻结人工标签并计算正式指标。
"""
(REPORTS / "blind_test_v1_evaluation.md").write_text(report, encoding="utf-8")
print(json.dumps({"status": api_summary["status"], "rows": len(rows), "human_actions": dict(human_actions), "human_topics": dict(human_topics)}, ensure_ascii=False, indent=2))

