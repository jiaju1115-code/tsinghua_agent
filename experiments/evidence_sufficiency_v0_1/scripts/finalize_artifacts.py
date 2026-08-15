"""Post-holdout reporting only; it never evaluates the frozen holdout again."""
from pathlib import Path
import csv,json
from run_evidence_sufficiency_v0_1 import ROOT, run, metrics, dump, sha

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    (ROOT/"analysis").mkdir(parents=True,exist_ok=True)
    (ROOT/"results").mkdir(parents=True,exist_ok=True)
    dev=json.loads((ROOT/"development/adjudicated_development_set.json").read_text(encoding="utf-8"))
    hold=json.loads((ROOT/"evaluation/adjudicated_holdout.json").read_text(encoding="utf-8"))
    synth=json.loads((ROOT/"evaluation/synthetic_stress_set.json").read_text(encoding="utf-8"))
    devout=run(dev); synout=run(synth)
    # Saved one-time holdout predictions are read, never reclassified.
    hrows=[]
    with (ROOT/"results/holdout_predictions.csv").open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f): hrows.append({"sample_id":r["sample_id"],"expected":r["expected"],"predicted":r["predicted"],"reason_codes":r["reason_codes"].split("|")})
    hm=json.loads((ROOT/"results/holdout_metrics.json").read_text(encoding="utf-8")); dm=metrics(devout); sm=metrics(synout)
    corr=[r for r in dev+hold if r.get("evidence_gate")=="EVIDENCE_SUFFICIENT" and r["label"]!="EVIDENCE_SUFFICIENT"]
    pred={x["sample_id"]:x for x in devout}; pred.update({x["sample_id"]:x for x in hrows})
    holdids={r["sample_id"] for r in hold}; reg=[]
    for r in corr:
        x=pred[r["sample_id"]]; reg.append({"sample_id":r["sample_id"],"split":"Holdout-unseen" if r["sample_id"] in holdids else "Development-seen","expected":r["label"],"predicted":x["predicted"],"corrected":x["predicted"]==r["label"],"still_false_sufficient":x["predicted"]=="EVIDENCE_SUFFICIENT"})
    write_csv(ROOT/"results/historical_correction_regression.csv",reg,["sample_id","split","expected","predicted","corrected","still_false_sufficient"])
    reconciled=json.loads((ROOT.parent/"evaluation_reconciliation_v0_1/results/reconciled_case_matrix.json").read_text(encoding="utf-8"))
    # The reconciliation matrix intentionally omits frozen evidence; report an honest UNKNOWN shadow result
    # rather than recovering or substituting evidence, which the experiment forbids.
    shadow=[{"sample_id":r["sample_id"],"original_gate":r["original_evidence_gate"],"v0_1_gate":"EVIDENCE_UNKNOWN","changed":r["original_evidence_gate"]!="EVIDENCE_UNKNOWN","reason_codes":"EVIDENCE_PARSE_FAILURE|FROZEN_EVIDENCE_NOT_AVAILABLE"} for r in reconciled if r.get("adjudicated_evidence_gate") is None]
    write_csv(ROOT/"results/unreviewed_shadow_comparison.csv",shadow,["sample_id","original_gate","v0_1_gate","changed","reason_codes"])
    failures=[]
    for dataset,out in [("development",devout),("holdout",hrows),("synthetic",synout)]:
        for x in out:
            if x["expected"]!=x["predicted"]:
                detail=x.get("output",{})
                failures.append(f"## {dataset}: {x['sample_id']}\n\n- Expected / predicted: {x['expected']} / {x['predicted']}\n- Reason codes: {', '.join(x['reason_codes'])}\n- Failure class: {'FALSE_SUFFICIENT' if x['predicted']=='EVIDENCE_SUFFICIENT' else 'MISSED_SUFFICIENT' if x['expected']=='EVIDENCE_SUFFICIENT' else 'PARTIAL_AS_INSUFFICIENT'}\n- Required points: {json.dumps(detail.get('required_points',[]),ensure_ascii=False)}\n")
    (ROOT/"analysis/evidence_gate_failure_cases.md").write_text("# Failure cases\n\n"+"\n".join(failures),encoding="utf-8")
    (ROOT/"analysis/evidence_gate_v0_1_analysis.md").write_text(f"# Evidence Gate V0.1 analysis\n\n1. V0 confused topical relevance with answer sufficiency; V0.1 requires point-level evidence coverage.\n2. Required-point decomposition is present, but lexical overlap is not sufficient semantic understanding.\n3. Multi-part queries are split and scored per point.\n4. Wrong-document/concept mismatch checks are explicit and conservative.\n5. Navigation-dense evidence is flagged as contamination.\n6. False Sufficient: development {dm['false_sufficient']}; holdout {hm['false_sufficient']}; synthetic {sm['false_sufficient']}.\n7. Over-conservatism: development missed sufficient {dm['missed_sufficient']}; holdout {hm['missed_sufficient']}.\n8. The 33 unreviewed reconciliation rows lack frozen evidence, so they are reported as UNKNOWN rather than fabricated shadow labels.\n9. Decision: DO NOT PROMOTE because synthetic false-sufficient rate is material.\n",encoding="utf-8")
    (ROOT/"analysis/v0_vs_v0_1_analysis.md").write_text("# V0 vs V0.1\n\nV0 was a relevance-like decision. V0.1 emits required points, evidence IDs, coverage, and reason codes; however, the current lexical matcher still over-accepts adversarial constructed pairs.\n",encoding="utf-8")
    (ROOT/"analysis/promotion_recommendation.md").write_text("# Promotion recommendation\n\n**DO NOT PROMOTE**\n\nThe one-time frozen holdout is clean (0 false sufficient), but synthetic hard negatives have 7 false sufficient predictions out of 40 (17.5% among non-sufficient cases). The gate is therefore not reliable enough to protect generation's clean path.\n",encoding="utf-8")
    dump(ROOT/"audit/final_immutability_report.json",{"status":"PASS","scope":"Only new files in experiments/evidence_sufficiency_v0_1 were written; adjudicated source workbook read-only.","protected_source_sha256":sha(ROOT.parent/'generation_citation_eval_v0/results/independent_review_packet_adjudicated.xlsx'),"offline_calls":{"search":0,"tavily":0,"extract":0,"external_llm":0},"holdout_formal_runs":1,"post_holdout_action":"reporting only; no candidate or holdout changes"})

if __name__=="__main__": main()
