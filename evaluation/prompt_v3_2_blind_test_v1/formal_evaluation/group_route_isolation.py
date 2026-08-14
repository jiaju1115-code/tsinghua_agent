from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
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
OUTPUT_JSON = DIAG / "group_route_isolation_probe.json"
OUTPUT_MD = DIAG / "group_route_isolation_report.md"
DIAG.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ.pop("MOMO_API_KEY_RUNTIME", "").strip()
if not API_KEY:
    raise RuntimeError("temporary runtime API key missing")

sys.path.insert(0, str(SECOND))
from llm.provider import load_provider  # noqa: E402

provider = load_provider()
API_BASE = provider.api_base
TARGET_MODEL = "gpt-5.4-mini"
PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_SHA256 = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest().upper()
INPUTS = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
INPUT_SHA256 = hashlib.sha256(INPUT_PATH.read_bytes()).hexdigest().upper()

ALLOWED_ACTIONS = {"approve", "review", "reject"}
ALLOWED_REJECT = {"", "topic_irrelevant", "expired_event", "other"}
ALLOWED_TOPIC = {"high", "medium", "low"}
ALLOWED_TIME = {"evergreen", "active_time_bound", "expired", "historical_but_valuable", "unknown"}
ALLOWED_TYPES = {"service_entry", "procedure_guide", "policy", "faq", "resource_directory", "current_notice", "organization_intro", "mixed", "news_event", "research_news", "promotional_content", "achievement_report"}
ALLOWED_CATEGORIES = {"清华基本信息", "教务与学籍", "学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康", "网络与信息化", "图书馆服务", "体育与场馆", "奖助与资助", "国际事务与签证", "就业与职业发展", "校园访问", "校园综合服务", "科研参与与资源导航", "教学与培养", "校园机构与部门", "校园文化与历史", "非目标范围"}
REQUIRED = ["action", "reject_type", "category", "content_type", "audience", "topic_relevance", "time_status", "valid_from", "valid_until", "candidate_user_question", "positive_evidence", "negative_evidence", "possible_duplicate", "reason"]


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def redact(text):
    return str(text).replace(API_KEY, "[REDACTED]")


def safe_headers(response):
    allowed = ["x-request-id", "request-id", "x-oneapi-request-id", "trace-id", "x-trace-id", "cf-ray"]
    return {key: response.headers[key] for key in allowed if key in response.headers}


def error_body(response):
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error", payload)
            if isinstance(error, dict):
                return {key: redact(error.get(key, ""))[:300] for key in ("type", "code", "message") if key in error}
        return {"type": "HTTP_ERROR"}
    except Exception:
        return {"type": "HTTP_ERROR", "message": redact(response.text[:300])}


def probe(model, probe_id):
    payload = {"model": model, "messages": [{"role": "user", "content": "只回复 OK"}], "max_tokens": 10, "temperature": 0.1}
    started = time.perf_counter()
    try:
        response = requests.post(API_BASE + "/chat/completions", headers=headers(), json=payload, timeout=(20, 180))
        latency = round(time.perf_counter() - started, 3)
        record = {"probe_id": probe_id, "model": model, "success": False, "latency_seconds": latency, "http_status": response.status_code, "error_type": "", "request_ids": safe_headers(response)}
        if not response.ok:
            record["error_type"] = f"HTTP_{response.status_code}"
            record["error"] = error_body(response)
            return record
        try:
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty_model_response")
            record["success"] = True
            record["response_valid"] = True
            return record
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            record["response_valid"] = False
            return record
    except requests.ReadTimeout:
        return {"probe_id": probe_id, "model": model, "success": False, "latency_seconds": round(time.perf_counter()-started,3), "http_status": None, "error_type": "ReadTimeout", "request_ids": {}}
    except requests.RequestException as exc:
        return {"probe_id": probe_id, "model": model, "success": False, "latency_seconds": round(time.perf_counter()-started,3), "http_status": None, "error_type": type(exc).__name__, "request_ids": {}}


def validate_result(obj):
    if not isinstance(obj, dict):
        raise ValueError("not_json_object")
    if any(field not in obj for field in REQUIRED):
        raise ValueError("missing_fields")
    if obj["action"] not in ALLOWED_ACTIONS or obj["reject_type"] not in ALLOWED_REJECT or obj["topic_relevance"] not in ALLOWED_TOPIC:
        raise ValueError("invalid_enum")
    if obj["category"] not in ALLOWED_CATEGORIES or obj["content_type"] not in ALLOWED_TYPES or obj["time_status"] not in ALLOWED_TIME:
        raise ValueError("invalid_enum")
    if obj["action"] == "reject" and not obj["reject_type"]:
        raise ValueError("reject_type_required")
    if obj["action"] != "reject" and obj["reject_type"]:
        raise ValueError("reject_type_must_be_empty")
    if obj["topic_relevance"] == "low" and not (obj["action"] == "reject" and obj["reject_type"] == "topic_irrelevant"):
        raise ValueError("low_must_topic_reject")
    return {field: obj[field] for field in REQUIRED}


def real_sample_probe(item):
    content = (BASE / item["content_file"]).read_text(encoding="utf-8")
    if hashlib.sha256(content.encode("utf-8")).hexdigest() != item["content_sha256"]:
        raise ValueError("content_hash_changed")
    metadata = {key:item[key] for key in ("blind_id","original_id","title","url","source_domain")}
    user = "页面元数据：\n" + json.dumps(metadata,ensure_ascii=False) + "\n\n请严格按照 Prompt V3.2 的 JSON schema 输出。\n\nUNTRUSTED_WEBPAGE_BEGIN\n" + content + "\nUNTRUSTED_WEBPAGE_END"
    payload = {"model":TARGET_MODEL,"messages":[{"role":"system","content":PROMPT},{"role":"user","content":user}],"max_tokens":900,"temperature":0.1,"response_format":{"type":"json_object"}}
    attempts=[]
    for attempt,delay in ((1,0),(2,10)):
        if delay: time.sleep(delay)
        started=time.perf_counter()
        try:
            response=requests.post(API_BASE+"/chat/completions",headers=headers(),json=payload,timeout=(20,180))
            latency=round(time.perf_counter()-started,3)
            entry={"attempt":attempt,"latency_seconds":latency,"http_status":response.status_code,"error_type":"","request_ids":safe_headers(response)}
            attempts.append(entry)
            if not response.ok:
                entry["error_type"]=f"HTTP_{response.status_code}";entry["error"]=error_body(response)
                if response.status_code>=500 and attempt==1: continue
                return {"status":"FAILED","blind_id":item["blind_id"],"attempts":attempts}
            obj=validate_result(json.loads(response.json()["choices"][0]["message"]["content"]))
            row={"blind_id":item["blind_id"],"original_id":item["original_id"],"title":item["title"],"url":item["url"],"source_domain":item["source_domain"],**obj,"model":TARGET_MODEL,"reviewed_at":now(),"prompt_version":"v3.2","prompt_sha256":PROMPT_SHA256,"input_sha256":INPUT_SHA256,"latency_seconds":latency,"attempt_count":attempt,"key_group":"new_group","success":True}
            existing={}
            if RESULTS_PATH.exists():
                for line in RESULTS_PATH.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        try:
                            old=json.loads(line);existing[old.get("blind_id")]=old
                        except Exception: pass
            if item["blind_id"] not in existing:
                with RESULTS_PATH.open("a",encoding="utf-8") as handle:
                    handle.write(json.dumps(row,ensure_ascii=False)+"\n");handle.flush();os.fsync(handle.fileno())
            return {"status":"SUCCESS","blind_id":item["blind_id"],"attempts":attempts,"latency_seconds":latency,"result_appended":item["blind_id"] not in existing}
        except requests.ReadTimeout:
            attempts.append({"attempt":attempt,"latency_seconds":round(time.perf_counter()-started,3),"http_status":None,"error_type":"ReadTimeout","request_ids":{}})
            if attempt==1: continue
        except Exception as exc:
            attempts.append({"attempt":attempt,"latency_seconds":round(time.perf_counter()-started,3),"http_status":None,"error_type":type(exc).__name__,"request_ids":{}})
            break
    return {"status":"FAILED","blind_id":item["blind_id"],"attempts":attempts}


def choose_light_model(models):
    supported=[]
    for item in models:
        endpoints=item.get("supported_endpoint_types",[])
        if endpoints and "openai" not in endpoints: continue
        name=str(item.get("id", ""))
        if not name or name==TARGET_MODEL: continue
        supported.append(name)
    priorities=("mini","nano","flash","lite","small","haiku")
    for token in priorities:
        matches=sorted(name for name in supported if token in name.lower())
        if matches: return matches[0]
    return sorted(supported)[0] if supported else None


result={"api_base":API_BASE,"key_group":"new_group","target_model":TARGET_MODEL,"started_at":now(),"phase_a":{},"target_model_probes":[],"diagnostic_model":{"executed":False,"diagnostic_only":True},"real_sample_probe":{"status":"NOT_RUN"},"comparison":{},"backend_identity":"BACKEND_IDENTITY_NOT_VERIFIABLE","ready_to_resume_blind_test":False,"final_diagnostic_status":"INCONCLUSIVE"}

started=time.perf_counter()
try:
    response=requests.get(API_BASE+"/models",headers=headers(),timeout=(20,60))
    latency=round(time.perf_counter()-started,3)
    result["phase_a"]["auth"]={"success":response.status_code==200,"http_status":response.status_code,"latency_seconds":latency,"request_ids":safe_headers(response)}
    if response.status_code!=200:
        result["phase_a"]["models"]={"success":False,"error":error_body(response)}
        models=[]
    else:
        models=response.json().get("data",[])
        result["phase_a"]["models"]={"success":True,"count":len(models)}
except requests.RequestException as exc:
    result["phase_a"]["auth"]={"success":False,"http_status":None,"latency_seconds":round(time.perf_counter()-started,3),"error_type":type(exc).__name__}
    result["phase_a"]["models"]={"success":False};models=[]
model_names={item.get("id") for item in models}
result["phase_a"]["gpt_5_4_mini_available"]=TARGET_MODEL in model_names

if result["phase_a"]["auth"]["success"] and TARGET_MODEL in model_names:
    first=probe(TARGET_MODEL,1);result["target_model_probes"].append(first)
    if first["success"]:
        for probe_id in (2,3):
            current=probe(TARGET_MODEL,probe_id);result["target_model_probes"].append(current)
            if not current["success"]: break

target_three_success=len(result["target_model_probes"])==3 and all(item["success"] for item in result["target_model_probes"])
if target_three_success:
    result["final_diagnostic_status"]="NEW_GROUP_GPT54MINI_RECOVERED"
    result["real_sample_probe"]=real_sample_probe(INPUTS[0])
    if result["real_sample_probe"]["status"]=="SUCCESS": result["ready_to_resume_blind_test"]=True
else:
    alternative=choose_light_model(models)
    result["diagnostic_model"]={"executed":False,"diagnostic_only":True,"model":alternative,"probes":[]}
    if alternative:
        result["diagnostic_model"]["executed"]=True
        first_alt=probe(alternative,1);result["diagnostic_model"]["probes"].append(first_alt)
        if first_alt["success"]:
            result["diagnostic_model"]["probes"].append(probe(alternative,2))
        alt_success=any(item["success"] for item in result["diagnostic_model"]["probes"])
        result["final_diagnostic_status"]="GPT_5_4_MINI_ROUTE_ISSUE" if alt_success else "PROVIDER_GENERATION_PATH_ISSUE"

old_path=DIAG/"api_recovery_probe.json"
old=json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
old_probe=(old.get("minimal_probes") or [{}])[0]
result["comparison"]={"old_group":{"auth":"PASS" if old.get("phase_a",{}).get("auth",{}).get("status")=="PASS" else "UNKNOWN","models":"PASS" if old.get("phase_a",{}).get("model",{}).get("available") else "UNKNOWN","gpt_5_4_mini_minimal_generation":f"FAIL HTTP {old_probe.get('http_status')}" if old_probe else "UNKNOWN"},"new_group":{"auth":"PASS" if result["phase_a"]["auth"]["success"] else "FAIL","models":"PASS" if result["phase_a"]["models"]["success"] else "FAIL","gpt_5_4_mini_minimal_generation":"3/3 SUCCESS" if target_three_success else (f"FAIL HTTP {result['target_model_probes'][0].get('http_status')}" if result["target_model_probes"] else "NOT_RUN")}}
result["finished_at"]=now()
OUTPUT_JSON.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")

def probe_lines(items):
    if not items:return "- NOT_RUN"
    return "\n".join(f"- Probe {p['probe_id']}: {'SUCCESS' if p['success'] else 'FAIL'}；latency={p['latency_seconds']}s；HTTP={p['http_status']}；error={p['error_type'] or 'none'}；request-id={json.dumps(p.get('request_ids',{}),ensure_ascii=False)}" for p in items)
alt=result["diagnostic_model"]
report=f"""# API Provider / 模型路由 / 分组隔离诊断

## A. 新Key认证

- KEY_GROUP=`new_group`
- API Base：`{API_BASE}`
- Auth：{'PASS' if result['phase_a']['auth']['success'] else 'FAIL'}；HTTP={result['phase_a']['auth'].get('http_status')}；latency={result['phase_a']['auth'].get('latency_seconds')}s
- `/models`：{'PASS' if result['phase_a']['models']['success'] else 'FAIL'}
- `gpt-5.4-mini available`：{result['phase_a']['gpt_5_4_mini_available']}

## B. 新分组 + gpt-5.4-mini

{probe_lines(result['target_model_probes'])}

## C. 其他模型诊断

- DIAGNOSTIC_ONLY：True
- model：{alt.get('model')}
{probe_lines(alt.get('probes',[]))}

## D. 新旧分组比较

| 测试 | old_group | new_group |
|---|---|---|
| Auth | {result['comparison']['old_group']['auth']} | {result['comparison']['new_group']['auth']} |
| Models | {result['comparison']['old_group']['models']} | {result['comparison']['new_group']['models']} |
| gpt-5.4-mini minimal generation | {result['comparison']['old_group']['gpt_5_4_mini_minimal_generation']} | {result['comparison']['new_group']['gpt_5_4_mini_minimal_generation']} |

## E. 故障定位

- 最终诊断：`{result['final_diagnostic_status']}`
- 真实 BLINDV1-001：`{result['real_sample_probe']['status']}`
- READY_TO_RESUME_BLIND_TEST：`{result['ready_to_resume_blind_test']}`
- Backend identity：`BACKEND_IDENTITY_NOT_VERIFIABLE`
- 未运行50条正式盲测；其他模型仅用于故障隔离。
"""
OUTPUT_MD.write_text(report,encoding="utf-8")
print(json.dumps({"status":result["final_diagnostic_status"],"target_probes":result["target_model_probes"],"diagnostic_model":result["diagnostic_model"],"real_sample":result["real_sample_probe"],"ready":result["ready_to_resume_blind_test"]},ensure_ascii=False))

