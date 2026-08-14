from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from src.academic_search import AcademicRetriever
from src.router_v0_1 import route_v0_1
ROOT=Path(__file__).resolve().parent
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def frozen_questions():
    """Read immutable V0 formal records; never modify its frozen evaluation set."""
    path=ROOT.parent/"web_search_v0"/"results"/"formal_per_question_results.jsonl"
    seen={}
    for line in path.read_text(encoding="utf-8").splitlines():
        row=json.loads(line)
        seen.setdefault(row["evaluation_id"],{"id":row["evaluation_id"],"query":row["query"],"expected_mode":row["expected_mode"]})
    return [seen[k] for k in sorted(seen)]
def append(path,item):
    path.parent.mkdir(exist_ok=True)
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(item,ensure_ascii=False)+"\n")
def existing(path): return {json.loads(x)["evaluation_id"] for x in path.read_text(encoding="utf-8").splitlines() if x} if path.exists() else set()
def router_rows(items,label):
    out=[]
    for item in items:
        r=route_v0_1(item["query"]).to_dict(); r.update({"evaluation_id":item["id"],"query":item["query"],"expected_mode":item["expected_mode"],"set":label,"correct":r["mode"]==item["expected_mode"]});out.append(r)
    return out
def run_academic(items,label):
    path=ROOT/"results"/f"{label}_per_question_results.jsonl"; done=existing(path); retriever=AcademicRetriever(); all_rows=[]
    for item in items:
        if item["id"] in done: continue
        before=(retriever.new_search,retriever.new_extract,retriever.cache_hits); route=route_v0_1(item["query"]).to_dict(); result=retriever.retrieve_academic_context(item["query"])
        result.update({"evaluation_id":item["id"],"expected_mode":item["expected_mode"],"actual_mode":route["mode"],"router":route,"set":label,"subject_expected":item.get("subject"),"new_search_requests":retriever.new_search-before[0],"new_extract_requests":retriever.new_extract-before[1],"cache_hits":retriever.cache_hits-before[2]})
        append(path,result); print(item["id"],result["knowledge_sufficiency"])
    rows=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    routed=[r for r in rows if r["actual_mode"]=="ACADEMIC_RETRIEVAL"]
    metrics={"questions":len(rows),"router_accuracy":round(len(routed)/len(rows),4),"retrieval_knowledge_sufficiency":round(sum(r["knowledge_sufficiency"] for r in rows)/len(rows),4),"knowledge_sufficiency":round(sum(r["knowledge_sufficiency"] for r in routed)/len(rows),4),"direct_answer_leakage":round(sum(r["direct_answer_risk"] for r in rows)/len(rows),4),"new_search_requests":sum(r["new_search_requests"] for r in rows),"new_extract_requests":sum(r["new_extract_requests"] for r in rows),"cache_hits":sum(r["cache_hits"] for r in rows),"stage2_triggered_questions":sum(r["stage2_triggered"] for r in rows),"average_latency_seconds":round(sum(r["total_latency_seconds"] for r in rows)/len(rows),3),"knowledge_atoms":sum(len(r["plan"]["knowledge_atoms"]) for r in rows),"covered_atoms":sum(len(r["covered_atoms"]) for r in routed),"missing_atoms":sum(len(r["missing_atoms"]) for r in rows)}
    (ROOT/"results"/f"{label}_metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    return rows,metrics
def main():
 p=argparse.ArgumentParser();p.add_argument("--phase",choices=["dry","full-router","shadow"],required=True);a=p.parse_args(); frozen=frozen_questions()
 if a.phase=="dry": run_academic([x for x in frozen if x["expected_mode"]=="ACADEMIC_RETRIEVAL"],"frozen_academic_10_v0_1")
 elif a.phase=="full-router":
  rows=router_rows(frozen,"frozen_full30"); neg=router_rows(load(ROOT/"evaluation"/"router_negative_cases.json"),"router_negatives"); path=ROOT/"results"/"router_results.jsonl"; path.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows+neg)+"\n",encoding="utf-8")
  (ROOT/"results"/"full_router_metrics.json").write_text(json.dumps({"questions":30,"router_accuracy":round(sum(x["correct"] for x in rows)/30,4),"negative_cases":len(neg),"negative_accuracy":round(sum(x["correct"] for x in neg)/len(neg),4),"confusion_matrix":dict(Counter(f'{x["expected_mode"]}->{x["mode"]}' for x in rows))},ensure_ascii=False,indent=2),encoding="utf-8")
 else: run_academic(load(ROOT/"evaluation"/"academic_shadow_questions.json"),"academic_shadow_24")
if __name__=="__main__":main()
