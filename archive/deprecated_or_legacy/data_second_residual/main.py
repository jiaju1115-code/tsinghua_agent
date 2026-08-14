from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import yaml
from reviewer.loader import load_candidates,write_candidate_index,read_candidate_index,write_manifest
from reviewer.state import ReviewState
from reviewer.public_llm_reviewer import review_one,append_result,stratified_public
from reviewer.portal_local_reviewer import review_portal
from reviewer.copier import save_review,copy_by_action
from reviewer.schema import validate_review
from reviewer.report_generator import generate_reports
from llm.provider import load_provider
from llm.client import MomoClient,AuthenticationError
from utils.paths import PROJECT_ROOT,SOURCE_ROOT,DATA_DIR,LOG_DIR,ensure_dirs
from utils.logger import get_logger,safe_log
from utils.security import is_portal
from datetime import datetime
from zoneinfo import ZoneInfo

def config():
    c=yaml.safe_load((PROJECT_ROOT/"config.yaml").read_text(encoding="utf-8"))
    if Path(c["source_root"]).resolve()!=SOURCE_ROOT.resolve() or Path(c["project_root"]).resolve()!=PROJECT_ROOT.resolve():raise ValueError("项目路径配置不合法")
    return c
def now():return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

def build_index():
    ensure_dirs()
    if not (DATA_DIR/"source_manifest_before.json").exists():write_manifest()
    candidates,duplicates=load_candidates();write_candidate_index(candidates,duplicates)
    state=ReviewState(DATA_DIR/"review_state.db");state.recover();state.close()
    print(f"Candidate={len(candidates)}，排除历史重复={len(duplicates)}")

def api_test():
    c=config();p=load_provider()
    if not p.api_key or not p.api_base or not p.model:raise SystemExit("请先在.env配置MOMO_API_KEY、MOMO_API_BASE和MOMO_MODEL")
    client=MomoClient(p,c["request_timeout_seconds"],c["max_retries"],c["retry_delay_seconds"])
    fake={"id":"SMOKE_TEST","access_level":"public","source_mode":"public_web"};messages=[{"role":"system","content":"只返回JSON对象。"},{"role":"user","content":"返回 {\"ok\": true}，这是无敏感连通性测试。"}]
    response=client.chat(fake,messages,80,0,True);content=response["choices"][0]["message"]["content"]
    value=json.loads(content);print("Smoke Test成功，JSON模式正常。" if value.get("ok") is True else "Smoke Test返回JSON，但内容不符合预期。")

def review_public(limit):
    c=config();p=load_provider()
    if not p.model:raise SystemExit("MOMO_MODEL尚未确认")
    candidates=[x for x in read_candidate_index() if not is_portal(x)];selected=stratified_public(candidates,min(limit,int(c["public_review_limit"])))
    client=MomoClient(p,c["request_timeout_seconds"],c["max_retries"],c["retry_delay_seconds"]);state=ReviewState(DATA_DIR/"review_state.db");state.recover();logger=get_logger(LOG_DIR/"review.log");done=0
    try:
        for item in selected:
            state.ensure(item,"external_llm",p.model,c["prompt_version"]);row=state.status(item,"external_llm",p.model,c["prompt_version"])
            if row["status"]=="done":continue
            state.processing(item,"external_llm",p.model,c["prompt_version"])
            try:
                result=review_one(item,client,c);stamp=now();append_result(item,result,"external_llm",c["prompt_version"],p.model);save_review(item,result,"public");copy_by_action(item,result["recommended_action"]);state.done(item,"external_llm",p.model,c["prompt_version"],stamp,result["recommended_action"]);done+=1;print(f"[Public审核] {done:02d}/{limit} {item['id']} {result['recommended_action']}")
            except AuthenticationError:state.error(item,"external_llm",p.model,c["prompt_version"],now(),"authentication_failed");raise
            except Exception as exc:state.error(item,"external_llm",p.model,c["prompt_version"],now(),str(exc));safe_log(logger,"error",f"{item['id']} {exc}")
    except AuthenticationError as exc:print(str(exc))
    finally:state.close()
    print(f"本次完成Public AI审核：{done}，已停止。")

def review_portal_local():
    c=config();candidates=[x for x in read_candidate_index() if is_portal(x)];state=ReviewState(DATA_DIR/"review_state.db");state.recover();model="local-rules-v1";manual=[];count=0
    for item in candidates:
        state.ensure(item,"local_portal",model,c["prompt_version"]);row=state.status(item,"local_portal",model,c["prompt_version"])
        if row["status"]=="done":continue
        state.processing(item,"local_portal",model,c["prompt_version"]);markdown=(SOURCE_ROOT/item["source_markdown_path"]).read_text(encoding="utf-8");result=validate_review(review_portal(item,markdown),item["id"]);append_result(item,result,"local_portal",c["prompt_version"],model);save_review(item,result,"portal");copy_by_action(item,result["recommended_action"],True);state.done(item,"local_portal",model,c["prompt_version"],now(),result["recommended_action"]);count+=1
    state.close()
    results=[]
    with (PROJECT_ROOT/"reviews"/"review_results.csv").open(encoding="utf-8-sig") as f:results=[r for r in csv.DictReader(f) if r["review_type"]=="local_portal"]
    fields=["id","title","source_url","category_hint","local_classification","time_sensitivity","source_markdown_path","reason"]
    byid={x["id"]:x for x in candidates}
    with (PROJECT_ROOT/"reports"/"portal_manual_review.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in results:
            candidate=byid[r["id"]];detail=json.loads((PROJECT_ROOT/"knowledge"/"02_ai_reviewed"/"portal"/f"{r['id']}.json").read_text(encoding="utf-8"));w.writerow({"id":r["id"],"title":candidate["title"],"source_url":candidate["source_url"],"category_hint":candidate["category_hint"],"local_classification":detail.get("local_classification",""),"time_sensitivity":r["time_sensitivity"],"source_markdown_path":candidate["source_markdown_path"],"reason":r["reason"]})
    print(f"Portal本地审核新增完成：{count}/{len(candidates)}；未调用外部API。")

def status():
    candidates=read_candidate_index() if (DATA_DIR/"candidate_index.csv").exists() else []
    print(f"Candidates: {len(candidates)}")
    if (DATA_DIR/"review_state.db").exists():
        s=ReviewState(DATA_DIR/"review_state.db")
        for r in s.counts():print(r["review_type"],r["status"],r["n"])
        s.close()

def main(argv=None):
    parser=argparse.ArgumentParser(description="清华校园知识库第二阶段审核工具");sub=parser.add_subparsers(dest="cmd")
    sub.add_parser("build-index");sub.add_parser("api-test");p=sub.add_parser("review-public");p.add_argument("--limit",type=int,default=30);sub.add_parser("review-portal-local");sub.add_parser("report");sub.add_parser("status")
    args=parser.parse_args(argv)
    if not args.cmd:parser.print_help();return 0
    ensure_dirs()
    if args.cmd=="build-index":build_index()
    elif args.cmd=="api-test":api_test()
    elif args.cmd=="review-public":review_public(args.limit)
    elif args.cmd=="review-portal-local":review_portal_local()
    elif args.cmd=="report":generate_reports(config()["sample_report_size"]);print("报告已生成。")
    elif args.cmd=="status":status()
    return 0
if __name__=="__main__":raise SystemExit(main())
