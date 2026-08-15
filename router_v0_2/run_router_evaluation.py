from __future__ import annotations
import hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
from src.router_v0_2 import route
ROOT=Path(__file__).resolve().parent
V01=ROOT.parent/"web_search_v0_followup"
def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
def eval_items(items,set_name):
    rows=[]
    for item in items:
        r=route(item["query"]).to_dict();r.update({"evaluation_id":item["id"],"group":item.get("group",set_name),"subject":item.get("subject"),"query":item["query"],"expected_mode":item["expected_mode"],"correct":r["mode"]==item["expected_mode"],"set":set_name});rows.append(r)
    return rows
def metrics(rows):
    academic=[r for r in rows if r["expected_mode"]=="ACADEMIC_RETRIEVAL"];pred=[r for r in rows if r["mode"]=="ACADEMIC_RETRIEVAL"]
    return {"questions":len(rows),"accuracy":round(sum(r["correct"] for r in rows)/len(rows),4),"academic_recall":round(sum(r["mode"]=="ACADEMIC_RETRIEVAL" for r in academic)/len(academic),4) if academic else "N/A","academic_precision":round(sum(r["correct"] and r["mode"]=="ACADEMIC_RETRIEVAL" for r in pred)/len(pred),4) if pred else "N/A","campus_accuracy":round(sum(r["correct"] for r in rows if r["expected_mode"]=="CAMPUS_PUBLIC")/max(1,sum(r["expected_mode"]=="CAMPUS_PUBLIC" for r in rows)),4),"general_accuracy":round(sum(r["correct"] for r in rows if r["expected_mode"]=="GENERAL_WEB")/max(1,sum(r["expected_mode"]=="GENERAL_WEB" for r in rows)),4),"false_academic_count":sum(r["expected_mode"]!="ACADEMIC_RETRIEVAL" and r["mode"]=="ACADEMIC_RETRIEVAL" for r in rows),"missed_academic_count":sum(r["expected_mode"]=="ACADEMIC_RETRIEVAL" and r["mode"]!="ACADEMIC_RETRIEVAL" for r in rows),"confusion_matrix":dict(Counter(f'{r["expected_mode"]}->{r["mode"]}' for r in rows))}
def main():
    blind=json.loads((ROOT/"evaluation"/"router_blind_shadow_set.json").read_text(encoding="utf-8")); freeze=hashlib.sha256(json.dumps(blind,ensure_ascii=False,separators=(",",":" )).encode()).hexdigest()
    (ROOT/"audit").mkdir(exist_ok=True);(ROOT/"audit"/"blind_set_freeze.json").write_text(json.dumps({"status":"FROZEN","question_count":len(blind),"sha256":freeze,"frozen_at":"2026-08-14"},ensure_ascii=False,indent=2),encoding="utf-8")
    dev=json.loads((V01/"evaluation"/"academic_shadow_questions.json").read_text(encoding="utf-8")); v0full=read_jsonl(V01.parent/"web_search_v0"/"results"/"formal_per_question_results.jsonl")
    v0full=[{"id":x["evaluation_id"],"query":x["query"],"expected_mode":x["expected_mode"]} for x in v0full if x["evaluation_id"] not in {y.get("id") for y in v0full[:0]}]
    results={"development_24":eval_items(dev,"DEVELOPMENT_SET"),"frozen_full30":eval_items(v0full,"FROZEN_FULL30"),"blind_42":eval_items(blind,"BLIND_SHADOW")}
    (ROOT/"results").mkdir(exist_ok=True)
    for name,rows in results.items():
        (ROOT/"results"/(name+"_results.jsonl")).write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")
    out={"development_24":metrics(results["development_24"]),"frozen_full30":metrics(results["frozen_full30"]),"blind_42":metrics(results["blind_42"])}
    blind_rows=results["blind_42"];out["blind_42"]["academic_by_subject"]={}
    for subject in sorted({r.get("subject") for r in blind_rows if r.get("subject")}):
        subset=[r for r in blind_rows if r.get("subject")==subject];out["blind_42"]["academic_by_subject"][subject]=round(sum(r["correct"] for r in subset)/len(subset),4)
    (ROOT/"results"/"router_metrics.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
