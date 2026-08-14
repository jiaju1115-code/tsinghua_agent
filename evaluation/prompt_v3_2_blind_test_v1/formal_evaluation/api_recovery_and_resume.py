from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests


SECOND = Path(r"D:\python_projects\tsinghua_ai\data_second")
BASE = SECOND / "prompt_v3_2_blind_test_v1"
FORMAL = BASE / "formal_evaluation"
AUDIT = FORMAL / "audit"
DIAG = FORMAL / "diagnostics"
PROMPT_PATH = SECOND / "prompt_v3_2_test" / "prompt" / "prompt_v3_2.md"
INPUT_PATH = AUDIT / "blind_model_inputs.json"
RESULTS_PATH = AUDIT / "v3_2_blind_results.jsonl"
CHECKPOINT_PATH = AUDIT / "v3_2_blind_checkpoint.json"
SUMMARY_PATH = AUDIT / "v3_2_blind_api_summary.json"
DIAG_JSON = DIAG / "api_recovery_probe.json"
DIAG_MD = DIAG / "api_recovery_report.md"
for folder in (AUDIT, DIAG):
    folder.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ.pop("MOMO_API_KEY_RUNTIME", "").strip()
if not API_KEY:
    raise RuntimeError("temporary runtime API key missing")

sys.path.insert(0, str(SECOND))
from llm.provider import load_provider  # noqa: E402

provider = load_provider()
API_BASE = provider.api_base
MODEL = "gpt-5.4-mini"
PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_SHA256 = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest().upper()
INPUTS = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
INPUT_SHA256 = hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest().upper()

if provider.model != MODEL:
    raise RuntimeError(f"frozen model mismatch: {provider.model}")
if len(INPUTS) != 50:
    raise RuntimeError(f"frozen input count mismatch: {len(INPUTS)}")

ALLOWED_ACTIONS = {"approve", "review", "reject"}
ALLOWED_REJECT = {"", "topic_irrelevant", "expired_event", "other"}
ALLOWED_TOPIC = {"high", "medium", "low"}
ALLOWED_TIME = {"evergreen", "active_time_bound", "expired", "historical_but_valuable", "unknown"}
ALLOWED_TYPES = {"service_entry", "procedure_guide", "policy", "faq", "resource_directory", "current_notice", "organization_intro", "mixed", "news_event", "research_news", "promotional_content", "achievement_report"}
ALLOWED_CATEGORIES = {"清华基本信息", "教务与学籍", "学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康", "网络与信息化", "图书馆服务", "体育与场馆", "奖助与资助", "国际事务与签证", "就业与职业发展", "校园访问", "校园综合服务", "科研参与与资源导航", "教学与培养", "校园机构与部门", "校园文化与历史", "非目标范围"}
REQUIRED = ["action", "reject_type", "category", "content_type", "audience", "topic_relevance", "time_status", "valid_from", "valid_until", "candidate_user_question", "positive_evidence", "negative_evidence", "possible_duplicate", "reason"]


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def safe_error(exc):
    return str(exc).replace(API_KEY, "[REDACTED]")[:1200]


def headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def request_with_limited_retry(method, url, *, json_body=None, read_timeout=180, allow_retries=True):
    attempts = []
    delays = [0, 10, 30] if allow_retries else [0]
    for index, delay in enumerate(delays, 1):
        if delay:
            time.sleep(delay)
        started = time.perf_counter()
        try:
            response = requests.request(method, url, headers=headers(), json=json_body, timeout=(20, read_timeout))
            latency = round(time.perf_counter() - started, 3)
            attempts.append({"attempt": index, "latency_seconds": latency, "http_status": response.status_code, "error_type": ""})
            if response.status_code in {429} or 500 <= response.status_code < 600:
                if index < len(delays):
                    continue
            return response, attempts, None
        except requests.ReadTimeout as exc:
            latency = round(time.perf_counter() - started, 3)
            attempts.append({"attempt": index, "latency_seconds": latency, "http_status": None, "error_type": "ReadTimeout"})
            last = exc
        except requests.RequestException as exc:
            latency = round(time.perf_counter() - started, 3)
            attempts.append({"attempt": index, "latency_seconds": latency, "http_status": None, "error_type": type(exc).__name__})
            last = exc
        if index >= len(delays):
            return None, attempts, safe_error(last)
    return None, attempts, "unreachable"


def validate_result(obj):
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
        raise ValueError("invalid_category")
    if obj["content_type"] not in ALLOWED_TYPES:
        raise ValueError("invalid_content_type")
    if obj["time_status"] not in ALLOWED_TIME:
        raise ValueError("invalid_time_status")
    if not isinstance(obj["possible_duplicate"], bool):
        raise ValueError("invalid_possible_duplicate")
    return {field: obj[field] for field in REQUIRED}


def parse_chat_response(response):
    payload = response.json()
    text = payload["choices"][0]["message"]["content"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty_model_response")
    return text


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_diagnostic(diag):
    write_json(DIAG_JSON, diag)
    probes = diag.get("minimal_probes", [])
    probe_lines = [f"- Probe {p['probe_id']}: {'SUCCESS' if p['success'] else 'FAIL'}；latency={p.get('latency_seconds','')}s；error={p.get('error_type','') or 'none'}" for p in probes]
    real = diag.get("real_sample_probe", {"status": "NOT_RUN"})
    report = f"""# API Recovery Report

## API是否恢复

`{diag['final_api_recovery_status']}`

- API Base：`{API_BASE}`
- API_KEY_SOURCE：`temporary_runtime`
- TCP 443：{diag['phase_a']['tcp']['status']}
- HTTP：{diag['phase_a']['http']['status']}；status={diag['phase_a']['http'].get('http_status')}；latency={diag['phase_a']['http'].get('latency_seconds')}s
- Auth：{diag['phase_a']['auth']['status']}
- gpt-5.4-mini available：{diag['phase_a']['model']['available']}

## 三次最小生成探针

{chr(10).join(probe_lines) if probe_lines else '- NOT_RUN'}

## 真实样本探针

- 状态：{real.get('status','NOT_RUN')}
- blind_id：{real.get('blind_id','')}
- latency：{real.get('latency_seconds','')}s
- error：{real.get('error_type','')}

## 是否进入正式50条执行

`{diag.get('entered_formal_run', False)}`

## ReadTimeout

- timeout_count：{diag.get('timeout_count',0)}
- 本诊断不记录 API Key、Authorization Header 或盲测正文。
"""
    DIAG_MD.write_text(report, encoding="utf-8")


def existing_results():
    records = {}
    if RESULTS_PATH.exists():
        for line in RESULTS_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                validate_result(row)
                if row.get("blind_id"):
                    records[row["blind_id"]] = row
            except Exception:
                continue
    return records


append_lock = threading.Lock()


def append_result(row, completed):
    with append_lock:
        current = existing_results()
        if row["blind_id"] in current:
            return
        with RESULTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        completed.add(row["blind_id"])
        write_json(CHECKPOINT_PATH, {"completed_ids": sorted(completed), "updated_at": now()})


host = urlsplit(API_BASE).hostname
diag = {
    "api_base": API_BASE,
    "api_key_source": "temporary_runtime",
    "model": MODEL,
    "read_timeout_seconds": 180,
    "phase_a": {},
    "minimal_probes": [],
    "real_sample_probe": {"status": "NOT_RUN"},
    "entered_formal_run": False,
    "timeout_count": 0,
    "final_api_recovery_status": "DIAGNOSTIC_RUNNING",
    "started_at": now(),
}

# Phase A: DNS/TCP/HTTP/Auth/model.
started = time.perf_counter()
addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
tcp_status = "FAIL"
tcp_error = ""
for address in addresses:
    try:
        with socket.create_connection((address, 443), timeout=15) as sock:
            context = ssl.create_default_context()
            with context.wrap_socket(sock, server_hostname=host):
                pass
        tcp_status = "PASS"
        break
    except Exception as exc:
        tcp_error = safe_error(exc)
diag["phase_a"]["tcp"] = {"status": tcp_status, "resolved_address_count": len(addresses), "latency_seconds": round(time.perf_counter()-started,3), "error_type": type(Exception(tcp_error)).__name__ if tcp_error else ""}

http_started = time.perf_counter()
try:
    http_response = requests.get(API_BASE, timeout=(20, 30))
    diag["phase_a"]["http"] = {"status": "PASS", "http_status": http_response.status_code, "latency_seconds": round(time.perf_counter()-http_started,3)}
except requests.RequestException as exc:
    diag["phase_a"]["http"] = {"status": "FAIL", "http_status": None, "latency_seconds": round(time.perf_counter()-http_started,3), "error_type": type(exc).__name__}

auth_response, auth_attempts, auth_error = request_with_limited_retry("GET", API_BASE + "/models", read_timeout=60, allow_retries=False)
if auth_response is not None and auth_response.status_code == 200:
    model_ids = [item.get("id") for item in auth_response.json().get("data", [])]
    diag["phase_a"]["auth"] = {"status": "PASS", "http_status": 200, "latency_seconds": auth_attempts[-1]["latency_seconds"]}
    diag["phase_a"]["model"] = {"available": MODEL in model_ids, "status": "PASS" if MODEL in model_ids else "FAIL"}
else:
    status = auth_response.status_code if auth_response is not None else None
    diag["phase_a"]["auth"] = {"status": "FAIL", "http_status": status, "error_type": auth_attempts[-1]["error_type"] if auth_attempts else "HTTPError"}
    diag["phase_a"]["model"] = {"available": False, "status": "NOT_CHECKED"}

phase_a_ok = tcp_status == "PASS" and diag["phase_a"]["http"]["status"] == "PASS" and diag["phase_a"]["auth"]["status"] == "PASS" and diag["phase_a"]["model"]["available"]
if not phase_a_ok:
    diag["final_api_recovery_status"] = "API_STILL_BLOCKED"
    diag["finished_at"] = now()
    write_diagnostic(diag)
    print(json.dumps({"status": diag["final_api_recovery_status"], "phase_a": diag["phase_a"]}, ensure_ascii=False))
    raise SystemExit(2)

# Phase B: three independent minimal probes. One network attempt each; any fail stops immediately.
probe_payload = {"model": MODEL, "messages": [{"role": "user", "content": "Reply with only OK"}], "max_tokens": 8, "temperature": 0.1}
for probe_id in range(1, 4):
    response, attempts, error = request_with_limited_retry("POST", API_BASE + "/chat/completions", json_body=probe_payload, read_timeout=180, allow_retries=False)
    probe = {"probe_id": probe_id, "attempts": attempts, "success": False, "latency_seconds": attempts[-1]["latency_seconds"] if attempts else None, "http_status": response.status_code if response is not None else None, "error_type": attempts[-1]["error_type"] if attempts else "UnknownError"}
    try:
        if response is None:
            raise RuntimeError(error or "no_response")
        if not response.ok:
            raise RuntimeError(f"HTTP_{response.status_code}")
        body = parse_chat_response(response)
        probe["success"] = bool(body.strip())
        probe["error_type"] = ""
        probe["response_valid"] = True
    except Exception as exc:
        probe["error_type"] = probe["error_type"] or (f"HTTP_{response.status_code}" if response is not None else type(exc).__name__)
        probe["response_valid"] = False
    diag["minimal_probes"].append(probe)
    diag["timeout_count"] += sum(attempt["error_type"] == "ReadTimeout" for attempt in attempts)
    if not probe["success"]:
        diag["final_api_recovery_status"] = "API_STILL_BLOCKED"
        diag["finished_at"] = now()
        write_diagnostic(diag)
        print(json.dumps({"status": diag["final_api_recovery_status"], "probe": probe}, ensure_ascii=False))
        raise SystemExit(3)

# Phase C/D: real first sample, then remaining with incremental persistence.
completed_records = existing_results()
completed_ids = set(completed_records)
stats = {"total_attempts": 0, "retry_count": 0, "timeout_count": 0, "latencies": [], "failed": []}


def run_real(item, allow_retries):
    content = (BASE / item["content_file"]).read_text(encoding="utf-8")
    if hashlib.sha256(content.encode("utf-8")).hexdigest() != item["content_sha256"]:
        raise ValueError("content_hash_changed")
    meta = {key: item[key] for key in ("blind_id", "original_id", "title", "url", "source_domain")}
    user = "页面元数据：\n" + json.dumps(meta, ensure_ascii=False) + "\n\n请严格按照 Prompt V3.2 的 JSON schema 输出。\n\nUNTRUSTED_WEBPAGE_BEGIN\n" + content + "\nUNTRUSTED_WEBPAGE_END"
    payload = {"model": MODEL, "messages": [{"role":"system","content":PROMPT},{"role":"user","content":user}], "max_tokens":900, "temperature":0.1, "response_format":{"type":"json_object"}}
    response, attempts, error = request_with_limited_retry("POST", API_BASE+"/chat/completions", json_body=payload, read_timeout=180, allow_retries=allow_retries)
    stats["total_attempts"] += len(attempts)
    stats["retry_count"] += max(0, len(attempts)-1)
    stats["timeout_count"] += sum(attempt["error_type"] == "ReadTimeout" for attempt in attempts)
    stats["latencies"].extend(attempt["latency_seconds"] for attempt in attempts)
    if response is None:
        return None, attempts, error or "no_response"
    if not response.ok:
        return None, attempts, f"HTTP_{response.status_code}"
    try:
        obj = validate_result(json.loads(parse_chat_response(response)))
    except Exception as exc:
        return None, attempts, safe_error(exc)
    row = {"blind_id":item["blind_id"],"original_id":item["original_id"],"title":item["title"],"url":item["url"],"source_domain":item["source_domain"],**obj,"model":MODEL,"reviewed_at":now(),"prompt_version":"v3.2","prompt_sha256":PROMPT_SHA256,"input_sha256":INPUT_SHA256,"latency_seconds":attempts[-1]["latency_seconds"],"attempt_count":len(attempts)}
    return row, attempts, None

first = INPUTS[0]
if first["blind_id"] in completed_ids:
    diag["real_sample_probe"] = {"status":"SUCCESS_EXISTING","blind_id":first["blind_id"],"latency_seconds":completed_records[first["blind_id"]].get("latency_seconds")}
else:
    row, attempts, error = run_real(first, allow_retries=False)
    if row is None:
        diag["real_sample_probe"] = {"status":"REAL_SAMPLE_PROBE_FAILED","blind_id":first["blind_id"],"latency_seconds":attempts[-1]["latency_seconds"] if attempts else None,"error_type":attempts[-1]["error_type"] if attempts else type(Exception(error)).__name__}
        diag["timeout_count"] += sum(attempt["error_type"] == "ReadTimeout" for attempt in attempts)
        diag["final_api_recovery_status"] = "API_STILL_BLOCKED"
        diag["finished_at"] = now()
        write_diagnostic(diag)
        print(json.dumps({"status":diag["final_api_recovery_status"],"real_sample_probe":diag["real_sample_probe"]},ensure_ascii=False))
        raise SystemExit(4)
    append_result(row, completed_ids)
    diag["real_sample_probe"] = {"status":"SUCCESS","blind_id":first["blind_id"],"latency_seconds":attempts[-1]["latency_seconds"],"error_type":""}
    write_diagnostic(diag)

diag["entered_formal_run"] = True
diag["final_api_recovery_status"] = "API_RECOVERED"
write_diagnostic(diag)

remaining = [item for item in INPUTS if item["blind_id"] not in completed_ids]
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(run_real,item,True):item for item in remaining}
    for future in as_completed(futures):
        item = futures[future]
        try:
            row, attempts, error = future.result()
        except Exception as exc:
            row, attempts, error = None, [], safe_error(exc)
        if row:
            append_result(row, completed_ids)
        else:
            stats["failed"].append({"blind_id":item["blind_id"],"error_type":attempts[-1]["error_type"] if attempts else type(Exception(error)).__name__,"attempt_count":len(attempts)})

final_records = existing_results()
completed = len(final_records)
failed = 50-completed
api_summary = {
    "status":"API_RECOVERED" if completed==50 else "EVALUATION_PARTIAL",
    "api_key_source":"temporary_runtime",
    "total_samples":50,
    "completed":completed,
    "failed":failed,
    "skipped_existing":len(completed_records),
    "total_attempts":stats["total_attempts"],
    "retry_count":stats["retry_count"],
    "timeout_count":stats["timeout_count"],
    "mean_latency":round(sum(stats["latencies"])/len(stats["latencies"]),3) if stats["latencies"] else None,
    "max_latency":max(stats["latencies"]) if stats["latencies"] else None,
    "model":MODEL,
    "temperature":0.1,
    "concurrency":3,
    "max_completion_tokens":900,
    "read_timeout":180,
    "prompt_sha256":PROMPT_SHA256,
    "input_sha256":INPUT_SHA256,
    "actions":dict(Counter(row["action"] for row in final_records.values())),
    "failures":stats["failed"],
    "finished_at":now(),
}
write_json(SUMMARY_PATH,api_summary)
diag["final_api_recovery_status"] = "API_RECOVERED" if completed==50 else "EVALUATION_PARTIAL"
diag["completed"] = completed
diag["failed"] = failed
diag["timeout_count"] += stats["timeout_count"]
diag["finished_at"] = now()
write_diagnostic(diag)
print(json.dumps({"status":diag["final_api_recovery_status"],"completed":completed,"failed":failed},ensure_ascii=False))
if completed != 50:
    raise SystemExit(5)
