from __future__ import annotations
import csv,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from reviewer.prompt_builder import build_messages
from reviewer.validator import parse_and_validate
from reviewer.duplicate_analyzer import duplicate_ids
from reviewer.copier import save_review,copy_by_action
from utils.paths import SOURCE_ROOT,REVIEWS_DIR,RAW_OUTPUT_DIR
from utils.security import redact
from llm.client import AuthenticationError

RESULT_FIELDS=["id","title","relevance_score","knowledge_value","category","subcategory","content_type","authority","freshness","time_sensitivity","contains_actionable_information","personal_data_risk","possible_duplicate","possible_conflict","recommended_action","reason","review_type","prompt_version","model_name","reviewed_at","source_markdown_path"]
def now():return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

def append_result(candidate,result,review_type,prompt_version,model):
    path=REVIEWS_DIR/"review_results.csv";row={**result,"title":candidate["title"],"review_type":review_type,"prompt_version":prompt_version,"model_name":model,"reviewed_at":now(),"source_markdown_path":candidate["source_markdown_path"]}
    exists=path.exists()
    with path.open("a",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=RESULT_FIELDS,extrasaction="ignore");
        if not exists:w.writeheader()
        w.writerow(row)
    with (REVIEWS_DIR/"review_results.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return row

def append_usage(id_,model,usage,stamp):
    path=REVIEWS_DIR/"usage.csv";fields=["id","model","prompt_tokens","completion_tokens","total_tokens","reviewed_at"];exists=path.exists()
    with path.open("a",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        if not exists:w.writeheader()
        w.writerow({"id":id_,"model":model,"prompt_tokens":usage.get("prompt_tokens","") if usage else "","completion_tokens":usage.get("completion_tokens","") if usage else "","total_tokens":usage.get("total_tokens","") if usage else "","reviewed_at":stamp})

def review_one(candidate,client,config):
    markdown=(SOURCE_ROOT/candidate["source_markdown_path"]).read_text(encoding="utf-8");messages=build_messages(candidate,markdown,int(config["max_input_chars"]));last=None
    for repair in range(3):
        use_messages=messages if repair==0 else messages+[{"role":"system","content":"上次输出未通过JSON Schema验证。只返回修正后的JSON对象，字段和枚举必须完全符合要求。"}]
        response=client.chat(candidate,use_messages,int(config["max_completion_tokens"]),float(config["temperature"]),True)
        content=response["choices"][0]["message"]["content"];(RAW_OUTPUT_DIR/f"{candidate['id']}_attempt{repair+1}.txt").write_text(content,encoding="utf-8")
        try:
            result=parse_and_validate(content,candidate["id"]);result["possible_duplicate"]=result["possible_duplicate"] or candidate["id"] in duplicate_ids();append_usage(candidate["id"],client.p.model,response.get("usage"),now());return result
        except Exception as exc:last=exc
    raise ValueError(f"模型输出连续3次无效: {redact(last)}")

def stratified_public(candidates,limit):
    buckets={"service":[],"life":[],"notice":[],"new":[],"low":[],"other":[]}
    for c in candidates:
        text=c["title"]+" "+c.get("category_hint","")
        title=c["title"]
        if any(x in title for x in ("人物","科研","学术","新闻","校友","标兵","成果","论文")):key="low"
        elif any(x in title for x in ("通知","活动","讲座","会议")):key="notice"
        elif any(x in title for x in ("食堂","宿舍","医院","体育","交通","校园生活","图书馆")):key="life"
        elif any(x in title for x in ("办事","服务","指南","校园卡","网络","注册","证明")):key="service"
        elif "新生" in title or "入学" in title or c.get("category_hint")=="新生入校":key="new"
        else:key="other"
        buckets[key].append(c)
    # 每组先交替选择V1.1与legacy独立候选，避免历史层完全缺席。
    for key,items in buckets.items():
        current=[x for x in items if x["dataset_origin"]=="public"];legacy=[x for x in items if x["dataset_origin"]=="legacy_public"];mixed=[]
        while current or legacy:
            if current:mixed.append(current.pop(0))
            if legacy:mixed.append(legacy.pop(0))
        buckets[key]=mixed
    quotas={"service":6,"life":5,"notice":4,"new":4,"low":6,"other":5};result=[]
    for key in ("service","life","notice","new","low","other"):
        take=min(quotas[key],len(buckets[key]),limit-len(result));result.extend(buckets[key][:take]);buckets[key]=buckets[key][take:]
    while len(result)<limit and any(buckets.values()):
        for key in ("service","life","notice","new","low","other"):
            if buckets[key] and len(result)<limit:result.append(buckets[key].pop(0))
    return result
