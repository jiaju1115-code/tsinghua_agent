from __future__ import annotations

import hashlib
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

SECOND = Path(r"D:\python_projects\tsinghua_ai\data_second")
sys.path.insert(0, str(SECOND))
from llm.client import MomoClient  # noqa: E402
from llm.provider import load_provider  # noqa: E402

BASE = SECOND / "prompt_v3_2_blind_test_v1"
FORMAL = BASE / "formal_evaluation"
AUDIT = FORMAL / "audit"
RAW = AUDIT / "raw_api"
RAW.mkdir(parents=True, exist_ok=True)
PROMPT_PATH = SECOND / "prompt_v3_2_test" / "prompt" / "prompt_v3_2.md"
PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_SHA256 = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest().upper()
INPUT_PATH = AUDIT / "blind_model_inputs.json"
INPUT_SHA256 = hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest().upper()
INPUTS = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
CONFIG = yaml.safe_load((SECOND / "config.yaml").read_text(encoding="utf-8"))
PROVIDER = load_provider()

if PROVIDER.model != "gpt-5.4-mini":
    raise RuntimeError(f"model changed: {PROVIDER.model}")
if float(CONFIG["temperature"]) != 0.1:
    raise RuntimeError(f"temperature changed: {CONFIG['temperature']}")
if int(CONFIG["max_completion_tokens"]) != 900:
    raise RuntimeError(f"max_completion_tokens changed: {CONFIG['max_completion_tokens']}")
if len(INPUTS) != 50:
    raise RuntimeError(f"blind input count changed: {len(INPUTS)}")

ALLOWED_ACTIONS = {"approve", "review", "reject"}
ALLOWED_REJECT = {"", "topic_irrelevant", "expired_event", "other"}
ALLOWED_TOPIC = {"high", "medium", "low"}
ALLOWED_TIME = {"evergreen", "active_time_bound", "expired", "historical_but_valuable", "unknown"}
ALLOWED_TYPES = {"service_entry", "procedure_guide", "policy", "faq", "resource_directory", "current_notice", "organization_intro", "mixed", "news_event", "research_news", "promotional_content", "achievement_report"}
ALLOWED_CATEGORIES = {"清华基本信息", "教务与学籍", "学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康", "网络与信息化", "图书馆服务", "体育与场馆", "奖助与资助", "国际事务与签证", "就业与职业发展", "校园访问", "校园综合服务", "科研参与与资源导航", "教学与培养", "校园机构与部门", "校园文化与历史", "非目标范围"}
REQUIRED = ["action", "reject_type", "category", "content_type", "audience", "topic_relevance", "time_status", "valid_from", "valid_until", "candidate_user_question", "positive_evidence", "negative_evidence", "possible_duplicate", "reason"]


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def validate(obj):
    if not isinstance(obj, dict):
        raise ValueError("not_json_object")
    missing = [field for field in REQUIRED if field not in obj]
    if missing:
        raise ValueError("missing_fields:" + ",".join(missing))
    if obj["action"] not in ALLOWED_ACTIONS:
        raise ValueError("invalid_action")
    if obj["reject_type"] not in ALLOWED_REJECT:
        raise ValueError("invalid_reject_type")
    if obj["action"] == "reject" and not obj["reject_type"]:
        raise ValueError("reject_type_required")
    if obj["action"] != "reject" and obj["reject_type"]:
        raise ValueError("reject_type_must_be_empty")
    if obj["topic_relevance"] not in ALLOWED_TOPIC:
        raise ValueError("invalid_topic_relevance")
    if obj["topic_relevance"] == "low" and not (obj["action"] == "reject" and obj["reject_type"] == "topic_irrelevant"):
        raise ValueError("low_must_topic_reject")
    if obj["category"] not in ALLOWED_CATEGORIES:
        raise ValueError("invalid_category:" + str(obj["category"]))
    if obj["content_type"] not in ALLOWED_TYPES:
        raise ValueError("invalid_content_type")
    if obj["time_status"] not in ALLOWED_TIME:
        raise ValueError("invalid_time_status")
    if not isinstance(obj["valid_from"], str) or not isinstance(obj["valid_until"], str):
        raise ValueError("invalid_valid_dates")
    if not isinstance(obj["possible_duplicate"], bool):
        raise ValueError("invalid_possible_duplicate")
    return {field: obj[field] for field in REQUIRED}


class CountingSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.request_attempts = 0

    def request(self, *args, **kwargs):
        self.request_attempts += 1
        return super().request(*args, **kwargs)


lock = threading.Lock()
stats = {"network_request_attempts": 0, "resumed": 0}


def review(item):
    ident = item["blind_id"]
    raw_path = RAW / f"{ident}.json"
    session = CountingSession()
    stamp = now()
    try:
        if raw_path.exists():
            obj = validate(json.loads(raw_path.read_text(encoding="utf-8")))
            with lock:
                stats["resumed"] += 1
        else:
            content = (BASE / item["content_file"]).read_text(encoding="utf-8")
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != item["content_sha256"]:
                raise ValueError("content_hash_changed")
            if len(content) > int(CONFIG["max_input_chars"]):
                content = content[:22000] + "\n[中间内容截断]\n" + content[-28000:]
            metadata = {key: item[key] for key in ("blind_id", "original_id", "title", "url", "source_domain")}
            user = "页面元数据：\n" + json.dumps(metadata, ensure_ascii=False) + "\n\n请严格按照 Prompt V3.2 的 JSON schema 输出。\n\nUNTRUSTED_WEBPAGE_BEGIN\n" + content + "\nUNTRUSTED_WEBPAGE_END"
            client = MomoClient(PROVIDER, int(CONFIG["request_timeout_seconds"]), int(CONFIG["max_retries"]), int(CONFIG["retry_delay_seconds"]), session)
            response = client.chat(
                {"id": ident, "access_level": "public", "source_mode": "prompt_v3_2_blind_test_v1"},
                [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}],
                int(CONFIG["max_completion_tokens"]),
                float(CONFIG["temperature"]),
                True,
            )
            raw = response["choices"][0]["message"]["content"]
            obj = validate(json.loads(raw))
            raw_path.write_text(raw, encoding="utf-8")
        with lock:
            stats["network_request_attempts"] += session.request_attempts
        row = {
            "blind_id": item["blind_id"],
            "original_id": item["original_id"],
            "title": item["title"],
            "url": item["url"],
            "source_domain": item["source_domain"],
            **obj,
            "model": PROVIDER.model,
            "reviewed_at": stamp,
            "prompt_version": "v3.2",
            "prompt_sha256": PROMPT_SHA256,
            "input_sha256": INPUT_SHA256,
        }
        return row, None
    except Exception as exc:
        with lock:
            stats["network_request_attempts"] += session.request_attempts
        return None, {"blind_id": ident, "title": item.get("title", ""), "error": str(exc)[:1200]}


results = []
failures = []
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = [pool.submit(review, item) for item in INPUTS]
    for index, future in enumerate(as_completed(futures), 1):
        row, failure = future.result()
        if row:
            results.append(row)
        if failure:
            failures.append(failure)
        if index % 5 == 0 or index == len(INPUTS):
            print(f"[Prompt V3.2 Blind] {index}/{len(INPUTS)} 成功={len(results)} 失败={len(failures)}", flush=True)

order = {item["blind_id"]: index for index, item in enumerate(INPUTS)}
results.sort(key=lambda row: order[row["blind_id"]])
failures.sort(key=lambda row: row["blind_id"])
with (AUDIT / "v3_2_blind_results.jsonl").open("w", encoding="utf-8") as handle:
    for row in results:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
(AUDIT / "v3_2_blind_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
summary = {
    "total_calls": len(INPUTS),
    "successes": len(results),
    "failures": len(failures),
    "network_request_attempts": stats["network_request_attempts"],
    "resumed": stats["resumed"],
    "actual_retries": max(0, stats["network_request_attempts"] - (len(INPUTS) - stats["resumed"])),
    "model": PROVIDER.model,
    "temperature": CONFIG["temperature"],
    "max_concurrency": 3,
    "max_completion_tokens": CONFIG["max_completion_tokens"],
    "prompt_version": "v3.2",
    "prompt_sha256": PROMPT_SHA256,
    "input_sha256": INPUT_SHA256,
    "actions": dict(Counter(row["action"] for row in results)),
    "reject_types": dict(Counter(row["reject_type"] for row in results if row["action"] == "reject")),
    "topic_relevance": dict(Counter(row["topic_relevance"] for row in results)),
}
(AUDIT / "v3_2_blind_api_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
if failures:
    raise SystemExit(f"Prompt V3.2 blind failures: {len(failures)}")

