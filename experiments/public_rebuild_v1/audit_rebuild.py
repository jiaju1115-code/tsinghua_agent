from __future__ import annotations

import csv
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


ROOT = Path(r"D:\python_projects\tsinghua_ai")
SECOND = ROOT / "data_second"
OUT = SECOND / "public_rebuild_v1"
SOURCE_AUDIT = SECOND / "public_expansion_v1" / "audit_v2.py"
sys.path.insert(0, str(SECOND))

from llm.client import MomoClient  # noqa: E402
from llm.provider import load_provider  # noqa: E402


# Frozen Prompt V2 is loaded byte-for-byte from the already validated run_6 module.
import importlib.util
spec = importlib.util.spec_from_file_location("frozen_audit_v2", SOURCE_AUDIT)
frozen = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(frozen)
SYSTEM, SCHEMA = frozen.SYSTEM, frozen.SCHEMA
ALLOWED_ACTIONS, ALLOWED_TIME, ALLOWED_TYPES = frozen.ALLOWED_ACTIONS, frozen.ALLOWED_TIME, frozen.ALLOWED_TYPES

AUDIT = OUT / "audit"
RAW = AUDIT / "raw_api"
RAW.mkdir(parents=True, exist_ok=True)
FIELDS = [
    "id", "parent_list_id", "title", "url", "source_domain", "source_file", "crawl_time",
    "extraction_method", "selector_used", "content_quality_class", "quality_gate_pass",
    "old_action", "action", "category", "content_type", "audience", "time_status",
    "candidate_user_question", "positive_evidence", "negative_evidence", "possible_duplicate", "reason",
    "model", "reviewed_at", "prompt_version",
]


def now() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def validate(obj: dict) -> dict:
    if not isinstance(obj, dict): raise ValueError("not_json_object")
    missing = [x for x in SCHEMA if x not in obj]
    if missing: raise ValueError("missing_fields:" + ",".join(missing))
    if obj["action"] not in ALLOWED_ACTIONS: raise ValueError("invalid_action")
    if obj["time_status"] not in ALLOWED_TIME: raise ValueError("invalid_time_status")
    if obj["content_type"] not in ALLOWED_TYPES: raise ValueError("invalid_content_type")
    if not isinstance(obj["possible_duplicate"], bool): raise ValueError("invalid_possible_duplicate")
    return {k: obj[k] for k in SCHEMA}


def excerpt(text: str, limit: int) -> str:
    if len(text) <= limit: return text
    return text[:22000] + "\n[中间内容截断]\n" + text[-28000:]


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def main() -> None:
    candidates = read_jsonl(OUT / "intermediate" / "audit_candidates.jsonl")
    if not candidates:
        raise SystemExit("no audit candidates")
    provider = load_provider()
    if not provider.api_key or not provider.api_base or not provider.model:
        raise SystemExit("MOMO provider is incomplete")
    config = yaml.safe_load((SECOND / "config.yaml").read_text(encoding="utf-8"))
    lock = threading.Lock()
    counters = {"attempts": 0, "resumed": 0}

    class CountingSession(requests.Session):
        def __init__(self):
            super().__init__(); self.request_attempts = 0
        def request(self, *args, **kwargs):
            self.request_attempts += 1
            return super().request(*args, **kwargs)

    def review(c: dict):
        raw_path = RAW / f"{c['id']}.json"
        stamp = now()
        session = CountingSession()
        try:
            if raw_path.exists():
                obj = validate(json.loads(raw_path.read_text(encoding="utf-8")))
                with lock: counters["resumed"] += 1
            else:
                page = excerpt((OUT / c["source_file"]).read_text(encoding="utf-8"), int(config["max_input_chars"]))
                meta = {k: c.get(k, "") for k in ("id", "parent_list_id", "title", "url", "source_domain", "crawl_time", "extraction_method", "content_quality_class")}
                user = "页面元数据：\n" + json.dumps(meta, ensure_ascii=False) + "\n\n必须返回：\n" + json.dumps(SCHEMA, ensure_ascii=False) + "\n\nUNTRUSTED_WEBPAGE_BEGIN\n" + page + "\nUNTRUSTED_WEBPAGE_END"
                client = MomoClient(provider, int(config["request_timeout_seconds"]), int(config["max_retries"]), int(config["retry_delay_seconds"]), session)
                response = client.chat({"id": c["id"], "access_level": "public", "source_mode": "public_rebuild_v1"},
                                       [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                                       int(config["max_completion_tokens"]), float(config["temperature"]), True)
                content = response["choices"][0]["message"]["content"]
                obj = validate(json.loads(content))
                raw_path.write_text(content, encoding="utf-8")
            with lock: counters["attempts"] += session.request_attempts
            row = {**c, **obj, "old_action": c.get("old_action", ""), "model": provider.model,
                   "reviewed_at": stamp, "prompt_version": "v2_frozen"}
            return {k: row.get(k, "") for k in FIELDS}, None
        except Exception as exc:
            with lock: counters["attempts"] += session.request_attempts
            return None, {"id": c["id"], "title": c.get("title", ""), "error": str(exc)[:1200]}

    results, failures = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(review, c) for c in candidates]
        for i, future in enumerate(as_completed(futures), 1):
            row, failure = future.result()
            if row: results.append(row)
            if failure: failures.append(failure)
            if i % 10 == 0 or i == len(candidates):
                print(f"[Prompt V2] {i}/{len(candidates)} 成功={len(results)} 失败={len(failures)}", flush=True)
    results.sort(key=lambda r: r["id"]); failures.sort(key=lambda r: r["id"])
    with (AUDIT / "audit_results.jsonl").open("w", encoding="utf-8") as f:
        for row in results: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_csv(AUDIT / "audit_results.csv", results, FIELDS)
    write_csv(AUDIT / "audit_failures.csv", failures, ["id", "title", "error"])
    summary = {"total_calls": len(candidates), "successes": len(results), "failures": len(failures),
               "resumed_completed_calls": counters["resumed"], "network_request_attempts": counters["attempts"],
               "max_concurrency": 3, "model": provider.model, "prompt_version": "v2_frozen",
               "actions": dict(Counter(r["action"] for r in results))}
    (AUDIT / "api_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if failures:
        raise SystemExit(f"Prompt V2 failures: {len(failures)}")


if __name__ == "__main__":
    main()
