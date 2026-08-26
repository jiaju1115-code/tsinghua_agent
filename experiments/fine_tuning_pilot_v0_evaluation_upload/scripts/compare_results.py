from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def mean(rows,key):
 vals=[r['score'][key] for r in rows if r['score'].get(key) is not None];return sum(vals)/len(vals) if vals else None
def main():
 general_base=ROOT/'results/base/general_per_case.jsonl';general_pilot=ROOT/'results/pilot_v0/general_per_case.jsonl'
 if general_base.exists() and general_pilot.exists():
  from build_general_comparison import main as build_general
  build_general()
 base=read(ROOT/'results/base/campus_per_case.jsonl');pilot=read(ROOT/'results/pilot_v0/campus_per_case.jsonl')
 keys=['groundedness_proxy','correct_refusal_proxy','unsupported_claim_proxy','citation_presence','citation_compatibility']
 metrics=[]
 for k in keys:
  b=mean(base,k);p=mean(pilot,k);metrics.append({'metric':k,'base':b,'pilot_v0':p,'delta':None if b is None or p is None else p-b,'result':'PROVISIONAL'})
 regress=[];improve=[]; paired=[]
 for b,p in zip(base,pilot):
  if b['score']['groundedness_proxy']>p['score']['groundedness_proxy'] or b['score']['unsupported_claim_proxy']<p['score']['unsupported_claim_proxy']:regress.append(p['case_id'])
  if b['score']['groundedness_proxy']<p['score']['groundedness_proxy'] or b['score']['unsupported_claim_proxy']>p['score']['unsupported_claim_proxy']:improve.append(p['case_id'])
  paired.append({'case_id':p['case_id'],'task_family':p['task_family'],'category':p['category'],'prompt_input_hash':p['prompt_input_hash'],'base_raw_output':b['raw_output'],'pilot_v0_raw_output':p['raw_output'],'base_parsed_result':b['parsed_result'],'pilot_v0_parsed_result':p['parsed_result'],'base_score':b['score'],'pilot_v0_score':p['score'],'evaluator_decision':'PROVISIONAL_RULE_BASED','reason':p['reason'],'evidence_references':p['evidence_references'],'base_latency_ms':b['latency_ms'],'pilot_v0_latency_ms':p['latency_ms'],'base_token_count':b['token_count'],'pilot_v0_token_count':p['token_count']})
 result={'status':'PROVISIONAL','campus_metrics':metrics,'regression_cases':regress,'improvement_cases':improve,'decision':'EVALUATION_INSUFFICIENT','reason':'Campus correctness labels are not present, so Campus proxy metrics cannot determine the final decision. General deterministic results, when present, are reported separately in general_comparison.json.'}
 out=ROOT/'results/comparison/comparison.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 with (ROOT/'results/comparison/campus_paired_per_case.jsonl').open('w',encoding='utf-8') as f:
  for row in paired:f.write(json.dumps(row,ensure_ascii=False)+'\\n')
if __name__=='__main__':main()
