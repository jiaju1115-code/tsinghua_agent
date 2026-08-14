from __future__ import annotations

import csv, hashlib, json, threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests, yaml

import sys
ROOT = Path(r"D:\python_projects\tsinghua_ai")
SECOND = ROOT / "data_second"
sys.path.insert(0, str(SECOND))
from llm.client import MomoClient  # noqa: E402
from llm.provider import load_provider  # noqa: E402

TEST = SECOND / "prompt_v3_2_test"
AUDIT = TEST / "audit"; RAW = AUDIT / "raw_api"; RAW.mkdir(parents=True, exist_ok=True)
PROMPT = (TEST / "prompt" / "prompt_v3_2.md").read_text(encoding="utf-8")
INPUT_PATH = SECOND / "prompt_v3_test" / "audit" / "v3_inputs.json"
INPUT_SHA256 = hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest().upper()
EXPECTED_SHA256 = "60C385C5DA026DF0F25B03034D63DA97F62FBDF2FF365A8DD83A27E14990BC1C"
if INPUT_SHA256 != EXPECTED_SHA256: raise RuntimeError(f"fixed sample changed: {INPUT_SHA256}")
INPUTS = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
CONFIG = yaml.safe_load((SECOND / "config.yaml").read_text(encoding="utf-8")); PROVIDER = load_provider()

ALLOWED_ACTIONS = {"approve", "review", "reject"}; ALLOWED_REJECT = {"", "topic_irrelevant", "expired_event", "other"}
ALLOWED_TOPIC = {"high", "medium", "low"}; ALLOWED_TIME = {"evergreen", "active_time_bound", "expired", "historical_but_valuable", "unknown"}
ALLOWED_TYPES = {"service_entry", "procedure_guide", "policy", "faq", "resource_directory", "current_notice", "organization_intro", "mixed", "news_event", "research_news", "promotional_content", "achievement_report"}
ALLOWED_CATEGORIES = {"清华基本信息", "教务与学籍", "学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康", "网络与信息化", "图书馆服务", "体育与场馆", "奖助与资助", "国际事务与签证", "就业与职业发展", "校园访问", "校园综合服务", "科研参与与资源导航", "教学与培养", "校园机构与部门", "校园文化与历史", "非目标范围"}
REQUIRED = ["action", "reject_type", "category", "content_type", "audience", "topic_relevance", "time_status", "valid_from", "valid_until", "candidate_user_question", "positive_evidence", "negative_evidence", "possible_duplicate", "reason"]
FIELDS = ["id", "parent_list_id", "title", "url", "source_domain", "source_file", "crawl_time", "extraction_method", "content_quality_class", *REQUIRED, "model", "reviewed_at", "prompt_version"]

def now(): return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
def validate(obj):
    if not isinstance(obj, dict): raise ValueError("not_json_object")
    missing=[x for x in REQUIRED if x not in obj]
    if missing: raise ValueError("missing_fields:"+",".join(missing))
    if obj["action"] not in ALLOWED_ACTIONS: raise ValueError("invalid_action")
    if obj["reject_type"] not in ALLOWED_REJECT: raise ValueError("invalid_reject_type")
    if obj["action"]=="reject" and not obj["reject_type"]: raise ValueError("reject_type_required")
    if obj["action"]!="reject" and obj["reject_type"]: raise ValueError("reject_type_must_be_empty")
    if obj["topic_relevance"] not in ALLOWED_TOPIC: raise ValueError("invalid_topic_relevance")
    if obj["topic_relevance"]=="low" and not (obj["action"]=="reject" and obj["reject_type"]=="topic_irrelevant"): raise ValueError("low_must_topic_reject")
    if obj["category"] not in ALLOWED_CATEGORIES: raise ValueError("invalid_category:"+str(obj["category"]))
    if obj["content_type"] not in ALLOWED_TYPES: raise ValueError("invalid_content_type")
    if obj["time_status"] not in ALLOWED_TIME: raise ValueError("invalid_time_status")
    if not isinstance(obj["valid_from"],str) or not isinstance(obj["valid_until"],str): raise ValueError("invalid_valid_dates")
    if not isinstance(obj["possible_duplicate"],bool): raise ValueError("invalid_possible_duplicate")
    return {k:obj[k] for k in REQUIRED}

class CountingSession(requests.Session):
    def __init__(self): super().__init__(); self.request_attempts=0
    def request(self,*args,**kwargs): self.request_attempts+=1; return super().request(*args,**kwargs)

lock=threading.Lock(); stats={"network_request_attempts":0,"resumed":0}
def review(item):
    ident=item["id"]; raw_path=RAW/f"{ident}.json"; session=CountingSession(); stamp=now()
    try:
        if raw_path.exists():
            obj=validate(json.loads(raw_path.read_text(encoding="utf-8")))
            with lock: stats["resumed"]+=1
        else:
            content=(SECOND/"public_rebuild_v1"/item["source_file"]).read_text(encoding="utf-8")
            if len(content)>int(CONFIG["max_input_chars"]): content=content[:22000]+"\n[中间内容截断]\n"+content[-28000:]
            meta={k:item.get(k,"") for k in ("id","parent_list_id","title","url","source_domain","crawl_time","extraction_method","content_quality_class")}
            user="页面元数据：\n"+json.dumps(meta,ensure_ascii=False)+"\n\n请严格按照 Prompt V3.2 的 JSON schema 输出。\n\nUNTRUSTED_WEBPAGE_BEGIN\n"+content+"\nUNTRUSTED_WEBPAGE_END"
            client=MomoClient(PROVIDER,int(CONFIG["request_timeout_seconds"]),int(CONFIG["max_retries"]),int(CONFIG["retry_delay_seconds"]),session)
            response=client.chat({"id":ident,"access_level":"public","source_mode":"prompt_v3_2_test"},[{"role":"system","content":PROMPT},{"role":"user","content":user}],int(CONFIG["max_completion_tokens"]),float(CONFIG["temperature"]),True)
            raw=response["choices"][0]["message"]["content"]; obj=validate(json.loads(raw)); raw_path.write_text(raw,encoding="utf-8")
        with lock: stats["network_request_attempts"]+=session.request_attempts
        row={**item,**obj,"model":PROVIDER.model,"reviewed_at":stamp,"prompt_version":"v3.2"}
        return {k:row.get(k,"") for k in FIELDS},None
    except Exception as exc:
        with lock: stats["network_request_attempts"]+=session.request_attempts
        return None,{"id":ident,"title":item.get("title",""),"error":str(exc)[:1200]}

results=[]; failures=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    futures=[pool.submit(review,item) for item in INPUTS]
    for i,future in enumerate(as_completed(futures),1):
        row,failure=future.result()
        if row: results.append(row)
        if failure: failures.append(failure)
        if i%5==0 or i==len(INPUTS): print(f"[Prompt V3.2] {i}/{len(INPUTS)} 成功={len(results)} 失败={len(failures)}",flush=True)
results.sort(key=lambda r:r["id"]); failures.sort(key=lambda r:r["id"])
with (AUDIT/"v3_2_results.jsonl").open("w",encoding="utf-8") as f:
    for r in results: f.write(json.dumps(r,ensure_ascii=False)+"\n")
with (AUDIT/"v3_2_results.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(results)
with (AUDIT/"v3_2_failures.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["id","title","error"]); w.writeheader(); w.writerows(failures)
summary={"total_calls":len(INPUTS),"successes":len(results),"failures":len(failures),"network_request_attempts":stats["network_request_attempts"],"resumed":stats["resumed"],"actual_retries":max(0,stats["network_request_attempts"]-len(INPUTS)),"model":PROVIDER.model,"temperature":CONFIG["temperature"],"max_concurrency":3,"max_completion_tokens":CONFIG["max_completion_tokens"],"prompt_version":"v3.2","input_sha256":INPUT_SHA256,"actions":dict(Counter(r["action"] for r in results)),"reject_types":dict(Counter(r["reject_type"] for r in results if r["action"]=="reject")),"topic_relevance":dict(Counter(r["topic_relevance"] for r in results))}
(AUDIT/"v3_2_api_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
if failures: raise SystemExit(f"Prompt V3.2 failures: {len(failures)}")
