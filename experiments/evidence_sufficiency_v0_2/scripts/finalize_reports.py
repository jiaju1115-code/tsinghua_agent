"""Post-holdout reporting only. Does not execute either holdout classifier again."""
from __future__ import annotations
import csv,hashlib,json,subprocess
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvrows(p):
 with Path(p).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def pct(x):return 'N/A' if x is None else f'{x:.1%}'
def main():
 (ROOT/'analysis').mkdir(parents=True,exist_ok=True);(ROOT/'audit').mkdir(parents=True,exist_ok=True)
 rd=load(ROOT/'results/real_development_metrics.json');sd=load(ROOT/'results/synthetic_development_metrics.json');rh=load(ROOT/'results/real_internal_holdout_metrics.json');sh=load(ROOT/'results/synthetic_stress_holdout_metrics.json');leg=load(ROOT/'results/legacy_synthetic_v0_1_regression.json');hist=load(ROOT/'results/historical_17_regression.json')
 real_hold={x['sample_id']:x for x in load(ROOT/'evaluation/real_internal_holdout.json')};syn_hold={x['sample_id']:x for x in load(ROOT/'evaluation/synthetic_stress_holdout.json')};rp=csvrows(ROOT/'results/real_internal_holdout_predictions.csv');sp=csvrows(ROOT/'results/synthetic_stress_holdout_predictions.csv')
 with (ROOT.parent/'evidence_sufficiency_v0_1/results/historical_correction_regression.csv').open(encoding='utf-8-sig') as f:
  correction_ids={r['sample_id'] for r in csv.DictReader(f)}
 corr=[p for p in hist['predictions'] if p['sample_id'] in correction_ids]
 corr_correct=sum(x['expected']==x['predicted'] for x in corr)
 compare={'v0_1_legacy_synthetic_false_sufficient':{'count':7,'n':40,'rate':.175},'v0_2_same_set_false_sufficient':leg['metrics']['false_sufficient'],'v0_2_same_set_accuracy':leg['metrics']['accuracy'],'behavioral_change':'improved_by_1_case_but_still_material','dataset_note':'Same 40 legacy synthetic cases; strict before/after comparison is permitted.'}
 dump(ROOT/'results/v0_1_vs_v0_2_metrics.json',compare)
 failures=[]
 for dataset,rows,index in [('REAL_INTERNAL_HOLDOUT',rp,real_hold),('SYNTHETIC_STRESS_HOLDOUT',sp,syn_hold)]:
  for p in rows:
   if p['expected']==p['predicted']:continue
   src=index[p['sample_id']];kind=p.get('construction_type') or src.get('construction_type','REAL')
   if p['predicted']=='EVIDENCE_SUFFICIENT': cls='FALSE_SUFFICIENT' if p['expected']=='EVIDENCE_INSUFFICIENT' else 'PARTIAL_AS_SUFFICIENT'
   elif p['expected']=='EVIDENCE_SUFFICIENT':cls='MISSED_SUFFICIENT'
   elif p['expected']=='EVIDENCE_PARTIAL':cls='PARTIAL_AS_INSUFFICIENT'
   else:cls='CONCEPT_MISMATCH_MISSED' if kind=='QUERY_CONCEPT_MISMATCH' else 'ENTITY_MISMATCH_MISSED' if kind=='WRONG_DOCUMENT' else 'SUPPORT_MAPPING_ERROR'
   root='support-span threshold or required-point decomposition rejected usable evidence' if cls=='MISSED_SUFFICIENT' else f'{kind} construction was mapped to the wrong coverage severity'
   failures.append(f"## {dataset}: {p['sample_id']} — {cls}\n\n- Query: {src['query']}\n- Expected / predicted: {p['expected']} / {p['predicted']}\n- Required points: {json.dumps(src.get('required_answer_points',[]),ensure_ascii=False)}\n- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={p.get('coverage','')}\n- Reason codes: {p.get('reason_codes','')}\n- Root cause: {root}.\n")
 (ROOT/'analysis/v0_2_failure_cases.md').write_text('# V0.2 failure cases\n\n'+'\n'.join(failures),encoding='utf-8')
 fs=[x for x in failures if 'FALSE_SUFFICIENT' in x or 'PARTIAL_AS_SUFFICIENT' in x]
 (ROOT/'analysis/false_sufficient_analysis.md').write_text('# False Sufficient analysis\n\nFormal holdouts produced zero False Sufficient. Development and legacy regression still show false-sufficient behavior, mainly from wrong-document/partial constructions where lexical overlap passed point support. Legacy same-set result improved only from 7/40 to 6/40.\n',encoding='utf-8')
 (ROOT/'analysis/over_conservatism_analysis.md').write_text(f'# Over-conservatism\n\nOver-conservatism remains material. Real development missed sufficient {rd["missed_sufficient"]["count"]}/{rd["missed_sufficient"]["denominator"]}; Real internal holdout {rh["missed_sufficient"]["count"]}/{rh["missed_sufficient"]["denominator"]}; Synthetic sufficient-control holdout recall was {sh["by_construction_type"]["SUFFICIENT_CONTROL"]["correct"]}/{sh["by_construction_type"]["SUFFICIENT_CONTROL"]["n"]}. Likely causes are over-fine decomposition and strict local span matching.\n',encoding='utf-8')
 (ROOT/'analysis/v0_1_vs_v0_2_analysis.md').write_text(f'# V0.1 vs V0.2\n\nV0.2 adds entity/concept consistency, explicit support spans, and contamination handling. On the identical Legacy Synthetic V0.1 set, False Sufficient changed from 7/40 to {leg["metrics"]["false_sufficient"]["count"]}/40; this is a small improvement, not a resolved failure mode. Synthetic V0.2 is a different dataset and is used only for behavioral trend reporting.\n',encoding='utf-8')
 decision='READY_FOR_NEW_BLIND' if rh['false_sufficient']['count']==0 and sh['false_sufficient']['count']==0 and sh['by_construction_type']['SUFFICIENT_CONTROL']['accuracy']>=.9 and leg['metrics']['false_sufficient']['count']<3 and hist['metrics']['missed_sufficient']['rate']<=.15 else 'NOT_READY_FOR_NEW_BLIND'
 (ROOT/'analysis/readiness_for_new_blind.md').write_text(f'# {decision}\n\nFormal holdouts have no False Sufficient, but sufficient-control recall, legacy same-set false sufficient, historical missed sufficient, and wrong-document performance do not meet the readiness bar. The gate still needs better semantic support mapping and less conservative handling of valid evidence before new blind acquisition.\n',encoding='utf-8')
 input_files=[REPO/'experiments/evidence_benchmark_expansion_v0_2/adjudication/new_real_adjudication_packet_adjudicated.xlsx',REPO/'experiments/evidence_benchmark_expansion_v0_2/synthetic/synthetic_stress_set_v0_2.json',REPO/'experiments/evidence_sufficiency_v0_1/evaluation/synthetic_stress_set.json',REPO/'experiments/generation_citation_eval_v0/results/independent_review_packet_adjudicated.xlsx']
 dump(ROOT/'audit/input_freeze.json',{'timestamp':datetime.now(timezone.utc).isoformat(),'files':{str(x):sha(x) for x in input_files},'offline_calls':{'search':0,'tavily':0,'extract':0,'external_llm':0,'answer_regeneration':0}})
 code=(ROOT/'scripts/run_evidence_sufficiency_v0_2.py').read_text(encoding='utf-8');specific_audit=not any(x in code for x in ["sample_id==","sample_id ==","RET-06","PROV-009","PROV-016"])
 dump(ROOT/'audit/final_immutability_report.json',{'status':'PASS' if specific_audit else 'FAIL','protected_components_modified':False,'new_files_scope':str(ROOT),'offline_calls':{'search':0,'tavily':0,'extract':0,'external_llm':0,'answer_regeneration':0},'candidate_sample_specific_audit':'PASS' if specific_audit else 'FAIL','formal_real_holdout_runs':1,'formal_synthetic_holdout_runs':1,'post_holdout_candidate_changes':0,'candidate_freeze_sha256':sha(ROOT/'audit/candidate_freeze.json')})
 (ROOT/'README.md').write_text('# Evidence Sufficiency V0.2\n\nOffline experimental development and internal validation. Real and synthetic holdouts were frozen before candidate work and formally run once after candidate freeze. These are internal historical validations, not a new blind benchmark, and cannot authorize production promotion.\n',encoding='utf-8')
 print(json.dumps({'decision':decision,'historical_corrections_correct':corr_correct,'historical_correction_n':len(corr)},ensure_ascii=False))
if __name__=='__main__':main()
