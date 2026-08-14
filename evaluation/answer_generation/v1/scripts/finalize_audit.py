from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
DATA=Path(r"D:\python_projects\tsinghua_ai\data_second"); ROOT=DATA/"answer_eval_v1"; FREEZE=ROOT/"audit"/"input_freeze.json"; OUT=ROOT/"audit"/"final_immutability_report.json"
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def inventory():
    rows=[]
    for p in DATA.rglob("*"):
        if not p.is_file() or ROOT in p.parents:continue
        s=p.stat();rows.append({"path":p.relative_to(DATA).as_posix(),"size":s.st_size,"mtime_ns":s.st_mtime_ns})
    return sorted(rows,key=lambda x:x["path"])
def main():
    z=json.loads(FREEZE.read_text(encoding="utf-8")); before={x["path"]:x for x in z["external_tree_before"]["rows"]}; afterrows=inventory(); after={x["path"]:x for x in afterrows}; added=sorted(set(after)-set(before)); removed=sorted(set(before)-set(after)); changed=[p for p in sorted(set(before)&set(after)) if before[p]!=after[p]]
    critical={}
    for n,i in z["critical_inputs"].items():
        p=Path(i["path"]); actual=sha(p) if p.exists() else None; critical[n]={"path":str(p),"exists":p.exists(),"expected_sha256":i["sha256"],"actual_sha256":actual,"unchanged":actual==i["sha256"]}
    bad=added+removed+changed
    res={"created_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS" if not bad and all(x["unchanged"] for x in critical.values()) else "FAIL","external_tree":{"before_file_count":len(before),"after_file_count":len(after),"added":added,"removed":removed,"metadata_changed":changed},"critical_inputs":critical,"output_scope":{"all_new_outputs_under_answer_eval_v1":all(ROOT in p.parents for p in ROOT.rglob("*") if p.is_file())},"protected_areas":{"rag_v0_modified":any(p.startswith("rag_v0/") for p in bad),"rag_v1_modified":any(p.startswith("rag_v1/") for p in bad),"answer_eval_v0_modified":any(p.startswith("answer_eval_v0/") for p in bad),"human_audit_modified":any(p.startswith("human_audit/") for p in bad),"prompt_v3_2_modified":any("prompt_v3_2" in p for p in bad),"production_modified":any(p.startswith("production/") for p in bad)}}
    OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(res,ensure_ascii=False,indent=2));raise SystemExit(0 if res["status"]=="PASS" else 2)
if __name__=="__main__":main()
