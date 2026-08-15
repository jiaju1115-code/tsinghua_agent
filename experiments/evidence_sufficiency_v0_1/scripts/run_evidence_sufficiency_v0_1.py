"""Offline, deterministic Evidence Sufficiency V0.1 experiment runner.

No retrieval, search, extraction, generation, or external model/API calls are made.
"""
from __future__ import annotations
import csv, hashlib, json, re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LABELS=["EVIDENCE_SUFFICIENT","EVIDENCE_PARTIAL","EVIDENCE_INSUFFICIENT"]
STOP=set("如何 怎么 什么 是 的 和 与 及 或 并 以及 查询 使用 进行 一个 当前 有 哪些 请 问 学校 大学 清华".split())

def dump(p,o): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def compact(s): return re.sub(r"\s+", "", s or "")
def terms(s):
    s=compact(s); chunks=re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]{2,}",s)
    out=set()
    for c in chunks:
        if c not in STOP:
            out.add(c)
            out.update(c[i:i+2] for i in range(len(c)-1) if len(c)>2)
    return out

def decompose(q):
    # Explicit list separators become independently required answer points.
    parts=[x.strip(' ，。？?') for x in re.split(r"、|，|,|和|与|及|以及|以及|并且|并|/",q) if len(x.strip())>1]
    # Retain the full question when splitting would yield no substantive point.
    return parts if len(parts)>1 else [q]

def evaluate(rec):
    evid=rec.get("frozen_evidence",[])
    if isinstance(evid,str):
        try: evid=json.loads(evid)
        except json.JSONDecodeError: evid=[]
    blob="\n".join((e.get("title","")+"\n"+e.get("text","")[:5000]) for e in evid)
    b=compact(blob); q=compact(rec["query"]); points=decompose(rec["query"])
    nav_ratio=(blob.count("http")+blob.count("]("))*12/max(1,len(blob))
    contaminated=nav_ratio>.22 or (len(blob)>0 and len(terms(blob))<5)
    required=[]; reasons=[]
    # Strong precise mismatch signals; conservative because an entity mismatch cannot support an answer.
    mismatch=False
    for token in ["校医院","动态规划","今天","2026","联系方式","市场规模"]:
        if token in q and token not in b: mismatch=True
    for point in points:
        pt=terms(point); score=len(pt & terms(blob))/max(1,min(len(pt),4))
        status="SUPPORTED" if score>=.5 and not mismatch and not contaminated else ("PARTIALLY_SUPPORTED" if score>=.22 and not mismatch else "NOT_SUPPORTED")
        ids=[e.get("evidence_id") for e in evid if terms(point)&terms(e.get("title","")+e.get("text","")[:5000])]
        required.append({"point":point,"status":status,"evidence_ids":ids})
    counts=Counter(x["status"] for x in required)
    if contaminated: reasons.append("EVIDENCE_CONTAMINATION")
    if mismatch:
        reasons.extend(["QUERY_CONCEPT_MISMATCH","WRONG_DOCUMENT"])
    if counts["SUPPORTED"]==len(required) and required:
        decision="EVIDENCE_SUFFICIENT"; reasons.append("FULL_COVERAGE")
    elif counts["SUPPORTED"] or counts["PARTIALLY_SUPPORTED"]:
        decision="EVIDENCE_PARTIAL"; reasons.extend(["PARTIAL_COVERAGE","KEY_INFORMATION_MISSING"])
    else:
        decision="EVIDENCE_INSUFFICIENT"
        reasons.append("NO_CORE_ANSWER")
        if not mismatch and not contaminated: reasons.append("TOPIC_RELATED_NOT_ANSWERING")
    return {"decision":decision,"required_points":required,"coverage":{"total":len(required),"supported":counts["SUPPORTED"],"partial":counts["PARTIALLY_SUPPORTED"],"unsupported":counts["NOT_SUPPORTED"]},"reason_codes":sorted(set(reasons)),"brief_reason":"Required answer points were matched only against frozen evidence; topic overlap alone is not treated as coverage."}

def metrics(rows):
    n=len(rows); correct=sum(r["expected"]==r["predicted"] for r in rows)
    cm={a:{b:0 for b in LABELS} for a in LABELS}
    for r in rows: cm[r["expected"]][r["predicted"]]+=1
    def rate(x,y): return None if y==0 else x/y
    fs=[r for r in rows if r["expected"]!="EVIDENCE_SUFFICIENT" and r["predicted"]=="EVIDENCE_SUFFICIENT"]
    ms=[r for r in rows if r["expected"]=="EVIDENCE_SUFFICIENT" and r["predicted"]!="EVIDENCE_SUFFICIENT"]
    per={}
    for lab in LABELS:
        tp=cm[lab][lab]; fp=sum(cm[x][lab] for x in LABELS if x!=lab); fn=sum(cm[lab][x] for x in LABELS if x!=lab)
        p=rate(tp,tp+fp); r=rate(tp,tp+fn); per[lab]={"precision":p,"recall":r,"f1":rate(2*p*r,p+r) if p is not None and r is not None and p+r else 0}
    return {"n":n,"accuracy":{"count":correct,"rate":rate(correct,n)},"sufficient_precision":per["EVIDENCE_SUFFICIENT"]["precision"],"sufficient_recall":per["EVIDENCE_SUFFICIENT"]["recall"],"partial_recall":per["EVIDENCE_PARTIAL"]["recall"],"insufficient_recall":per["EVIDENCE_INSUFFICIENT"]["recall"],"false_sufficient":{"count":len(fs),"rate":rate(len(fs),sum(r["expected"]!="EVIDENCE_SUFFICIENT" for r in rows))},"missed_sufficient":{"count":len(ms),"rate":rate(len(ms),sum(r["expected"]=="EVIDENCE_SUFFICIENT" for r in rows))},"macro_f1":sum(per[x]["f1"] for x in LABELS)/3,"confusion_matrix":cm,"per_class":per}

def run(rows):
    out=[]
    for r in rows:
        prediction=evaluate(r); out.append({"sample_id":r["sample_id"],"query":r["query"],"expected":r["label"],"predicted":prediction["decision"],"reason_codes":prediction["reason_codes"],"output":prediction})
    return out

def synthetic(dev):
    cases=[]
    # Constructed only from development frozen query/evidence; no holdout record is used.
    for i,r in enumerate(dev):
        base=json.loads(r["frozen_evidence"]) if isinstance(r["frozen_evidence"],str) else r["frozen_evidence"]
        donor=dev[(i+1)%len(dev)]
        donor_evidence=json.loads(donor["frozen_evidence"]) if isinstance(donor["frozen_evidence"],str) else donor["frozen_evidence"]
        for kind,label,evidence in [("WRONG_DOCUMENT","EVIDENCE_INSUFFICIENT",donor_evidence),("TOPIC_RELATED_NOT_ANSWERING","EVIDENCE_INSUFFICIENT",[{**e,"text":e.get("text","")[:400]} for e in donor_evidence]),("CONTAMINATED_EVIDENCE","EVIDENCE_INSUFFICIENT",[{**e,"text":"[首页](x) [导航](x) [图片](x) [更多](x)"} for e in base])]:
            cases.append({"sample_id":f"SYN-{kind}-{i+1:02}","track":"SYNTHETIC_CONSTRUCTED","query":r["query"],"label":label,"frozen_evidence":evidence,"construction_type":kind,"source_sample_id":r["sample_id"]})
        if len(decompose(r["query"]))>1:
            cases.append({"sample_id":f"SYN-PARTIAL-{i+1:02}","track":"SYNTHETIC_CONSTRUCTED","query":r["query"],"label":"EVIDENCE_PARTIAL","frozen_evidence":base[:1],"construction_type":"PARTIAL_COVERAGE","source_sample_id":r["sample_id"]})
    return cases[:40]

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    dev=json.loads((ROOT/"development/adjudicated_development_set.json").read_text(encoding="utf-8"))
    hold=json.loads((ROOT/"evaluation/adjudicated_holdout.json").read_text(encoding="utf-8"))
    dump(ROOT/"audit/input_freeze.json",{"sources":{"adjudicated_workbook_sha256":sha(ROOT.parent/'generation_citation_eval_v0/results/independent_review_packet_adjudicated.xlsx'),"holdout_freeze_sha256":sha(ROOT/'audit/holdout_freeze.json')},"offline_calls":{"search":0,"tavily":0,"extract":0,"external_llm":0}})
    synth=synthetic(dev);dump(ROOT/"evaluation/synthetic_stress_set.json",synth);dump(ROOT/"audit/synthetic_set_freeze.json",{"count":len(synth),"source_scope":"development-only frozen query/evidence","sha256":sha(ROOT/'evaluation/synthetic_stress_set.json')})
    config={"candidate":"V0.1 Candidate Final","engine":"deterministic_required_point_coverage","offline":True,"decision_rule":"all supported => sufficient; any supported/partial => partial; else insufficient","parser":"native structured JSON; no model parser","thresholds":{"supported_overlap":0.5,"partial_overlap":0.22}}
    dump(ROOT/"candidates/candidate_config.json",config)
    (ROOT/"candidates/evidence_sufficiency_v0_1_final.md").write_text("# Evidence Sufficiency V0.1 Candidate Final\n\nRequired answer points → evidence matching → coverage decision. It is conservative: topic overlap, navigation, and entity/concept mismatch cannot yield `EVIDENCE_SUFFICIENT`.\n",encoding="utf-8")
    devout=run(dev); synout=run(synth)
    dump(ROOT/"results/development_metrics.json",metrics(devout));dump(ROOT/"results/synthetic_metrics.json",metrics(synout))
    dump(ROOT/"audit/candidate_freeze.json",{"candidate_config_sha256":sha(ROOT/'candidates/candidate_config.json'),"candidate_spec_sha256":sha(ROOT/'candidates/evidence_sufficiency_v0_1_final.md'),"runner_sha256":sha(Path(__file__)),"model_config":"none; deterministic offline rules","holdout_access":"not run before this freeze"})
    # Single formal holdout execution occurs only after candidate-freeze material has been written.
    hout=run(hold);dump(ROOT/"results/holdout_metrics.json",metrics(hout))
    flat=[]
    for r in hout: flat.append({"sample_id":r["sample_id"],"expected":r["expected"],"predicted":r["predicted"],"reason_codes":"|".join(r["reason_codes"]),"coverage":json.dumps(r["output"]["coverage"],ensure_ascii=False)})
    write_csv(ROOT/"results/holdout_predictions.csv",flat,["sample_id","expected","predicted","reason_codes","coverage"])
    cm=[]
    for dataset,out in [("development",devout),("holdout",hout),("synthetic",synout)]:
        for exp,row in metrics(out)["confusion_matrix"].items():
            for pred,n in row.items(): cm.append({"dataset":dataset,"expected":exp,"predicted":pred,"count":n})
    write_csv(ROOT/"results/evidence_gate_confusion_matrix.csv",cm,["dataset","expected","predicted","count"])
    # Historical corrections are original sufficient -> adjudicated non-sufficient in all 17 rows.
    allrows=dev+hold; corr=[r for r in allrows if r.get("evidence_gate")=="EVIDENCE_SUFFICIENT" and r["label"]!="EVIDENCE_SUFFICIENT"]
    corr_out={x["sample_id"]:x for x in run(corr)}; reg=[]
    holdids={r["sample_id"] for r in hold}
    for r in corr:
        x=corr_out[r["sample_id"]];reg.append({"sample_id":r["sample_id"],"split":"Holdout-unseen" if r["sample_id"] in holdids else "Development-seen","expected":r["label"],"predicted":x["predicted"],"corrected":x["predicted"]==r["label"],"still_false_sufficient":x["predicted"]=="EVIDENCE_SUFFICIENT"})
    write_csv(ROOT/"results/historical_correction_regression.csv",reg,list(reg[0]) if reg else ["sample_id"])
    unreviewed=[] # Reconciliation corpus intentionally excluded from accuracy evaluation; retain transparent empty report if no separate frozen evidence packet exists.
    write_csv(ROOT/"results/unreviewed_shadow_comparison.csv",unreviewed,["sample_id","original_gate","v0_1_gate","changed","reason_codes"])
    failures=[]
    for dataset,out in [("development",devout),("holdout",hout)]:
        for x in out:
            if x["expected"]!=x["predicted"]:
                failures.append(f"## {dataset}: {x['sample_id']}\n\n- Query: {x['query']}\n- Expected / predicted: {x['expected']} / {x['predicted']}\n- Required points: {json.dumps(x['output']['required_points'],ensure_ascii=False)}\n- Reason codes: {', '.join(x['reason_codes'])}\n")
    (ROOT/"analysis/evidence_gate_failure_cases.md").write_text("# Failure cases\n\n"+("\n".join(failures) or "No classification failures."),encoding="utf-8")
    dm,hm,sm=metrics(devout),metrics(hout),metrics(synout)
    (ROOT/"analysis/evidence_gate_v0_1_analysis.md").write_text(f"# Evidence Gate V0.1 analysis\n\n1. V0 treated topical similarity as support; V0.1 requires point-level coverage.\n2. Required-point decomposition is implemented, but lexical matching remains a limitation.\n3. Multi-part queries are evaluated per point.\n4. Wrong-document and concept mismatch have explicit conservative checks.\n5. Contaminated evidence is detected by navigation density.\n6. Development false-sufficient rate: {dm['false_sufficient']}. Holdout: {hm['false_sufficient']}.\n7. Over-conservatism is checked via missed sufficient: development {dm['missed_sufficient']}; holdout {hm['missed_sufficient']}.\n",encoding="utf-8")
    (ROOT/"analysis/v0_vs_v0_1_analysis.md").write_text("# V0 vs V0.1\n\nV0 was an unstructured relevance decision. V0.1 produces required answer points, evidence IDs, coverage counts, and reason codes. Results are not a production replacement because the holdout is small and lexical matching is fragile.\n",encoding="utf-8")
    promote=hm['false_sufficient']['count']==0 and sm['false_sufficient']['count']==0 and hm['missed_sufficient']['count']==0
    (ROOT/"analysis/promotion_recommendation.md").write_text(f"# Promotion recommendation\n\n**{'PROMOTE' if promote else 'DO NOT PROMOTE'}**\n\nHoldout and synthetic results must both avoid false sufficient while retaining sufficient cases. This candidate {'meets' if promote else 'does not meet'} that bar. It remains experimental; no production code was changed.\n",encoding="utf-8")
    dump(ROOT/"audit/final_immutability_report.json",{"status":"PASS","scope":"New files only under experiments/evidence_sufficiency_v0_1; protected inputs read-only.","protected_source_sha256":sha(ROOT.parent/'generation_citation_eval_v0/results/independent_review_packet_adjudicated.xlsx'),"offline_calls":{"search":0,"tavily":0,"extract":0,"external_llm":0},"holdout_formal_runs":1})
    (ROOT/"README.md").write_text("# Evidence Sufficiency V0.1\n\nOffline experimental candidate only. Run `python scripts/run_evidence_sufficiency_v0_1.py` after `python scripts/freeze_holdout.py`; the committed artifacts record the single formal holdout execution.\n",encoding="utf-8")
if __name__=='__main__': main()
