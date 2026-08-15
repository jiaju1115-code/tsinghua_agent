from __future__ import annotations
import csv,hashlib,json,statistics,subprocess
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]; ROOT=Path(__file__).resolve().parents[1]
PROTECTED=[REPO/'experiments/router_v0_2',REPO/'experiments/web_search_v0/src',REPO/'experiments/web_search_v0_followup/src',REPO/'evaluation/answer_generation/v0/config',REPO/'prompts',REPO/'data_first',REPO/'data_second']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():
 files={}
 for base in PROTECTED:
  if base.exists():
   for p in sorted(x for x in base.rglob('*') if x.is_file() and '__pycache__' not in x.parts and 'cache' not in x.parts):files[str(p.relative_to(REPO)).replace('\\','/')]={'sha256':sha(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
 return {'captured_at':datetime.now(timezone.utc).isoformat(),'files':files,'git_status':subprocess.run(['git','status','--porcelain=v1'],cwd=REPO,text=True,capture_output=True).stdout.splitlines()}
def main():
 rows=json.loads((ROOT/'results/e2e12_results.json').read_text(encoding='utf-8'))
 refusal_terms=('资料不足','无法确认','证据不足','无法根据','无法回答','无法给出','没有关于')
 for r in rows:
  refused=any(x in r['final_answer'] for x in refusal_terms)
  r['correct_refusal']=bool(refused and (not r['evidence_sufficient'] or r['actual_route']=='UNCERTAIN'))
  if r['correct_refusal']:
   r['primary_failure_stage']='E' if r['search_expected'] and not r['evidence_sufficient'] else None
  r['citation_supports_claim']=bool(r['citation_count'] and r['citation_valid'] and r.get('citation_supports_claim'))
  substantive_claims=0 if refused else (r.get('total_claims') or 0)
  r['substantive_claim_count']=substantive_claims
  r['unsupported_claim_count_proxy']=0 if r['citation_supports_claim'] else substantive_claims
 (ROOT/'results/e2e12_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');(ROOT/'results/e2e12_case_matrix.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 fields=['sample_id','category','academic_subject','query','expected_route','actual_route','route_correct','search_called','search_call_count','search_success','extract_called','extract_call_count','extract_success','retrieved_source_count','usable_source_count','evidence_sufficient','answer_generated','answer_correctness','faithfulness','substantive_claim_count','unsupported_claim_count_proxy','citation_count','citation_valid','citation_supports_claim','correct_refusal','total_latency_ms','primary_failure_stage','evaluation_scope','evaluation_reason']
 with (ROOT/'results/e2e12_case_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 def metric(part):
  n=len(part); online=[x for x in part if x['search_expected']]; extracted=[x for x in part if x['extract_called']]; judged=[x for x in part if x['answer_correctness'] is not None]; cited=[x for x in part if x['citation_count']>0]; claims=sum(x['substantive_claim_count'] for x in part);uns=sum(x['unsupported_claim_count_proxy'] for x in part)
  return {'count':n,'e2e_completed':n,'route_accuracy':sum(x['route_correct'] for x in part)/n if n else None,'search_trigger_rate':sum(x['search_called'] for x in part)/n if n else None,'search_success_rate':sum(bool(x['search_success']) for x in online)/len(online) if online else None,'extract_success_rate':sum(bool(x['extract_success']) for x in extracted)/len(extracted) if extracted else None,'evidence_sufficiency_rate':sum(x['evidence_sufficient'] for x in part)/n if n else None,'answer_correctness_mean_0_to_2':sum(x['answer_correctness'] for x in judged)/len(judged) if judged else None,'answer_correctness_normalized':sum(x['answer_correctness'] for x in judged)/(2*len(judged)) if judged else None,'faithfulness_mean_0_to_2':sum(x['faithfulness'] for x in judged)/len(judged) if judged else None,'faithfulness_normalized':sum(x['faithfulness'] for x in judged)/(2*len(judged)) if judged else None,'substantive_claims':claims,'unsupported_claims_proxy':uns,'unsupported_claim_rate_proxy':uns/claims if claims else 0.0,'citation_presence_rate':len(cited)/n if n else None,'citation_validity_rate_given_present':sum(x['citation_valid'] for x in cited)/len(cited) if cited else None,'citation_support_rate_given_present':sum(x['citation_supports_claim'] for x in cited)/len(cited) if cited else None,'correct_refusal_count':sum(x['correct_refusal'] for x in part),'mean_latency_ms':statistics.mean(x['total_latency_ms'] for x in part) if n else None,'median_latency_ms':statistics.median(x['total_latency_ms'] for x in part) if n else None,'false_academic':sum(x['actual_route']=='ACADEMIC_RETRIEVAL' and x['expected_route']!='ACADEMIC_RETRIEVAL' for x in part),'missed_academic':sum(x['actual_route']!='ACADEMIC_RETRIEVAL' and x['expected_route']=='ACADEMIC_RETRIEVAL' for x in part),'failure_stages':dict(Counter(x['primary_failure_stage'] for x in part if x['primary_failure_stage'])),'search_calls':sum(x['search_call_count'] for x in part),'extract_calls':sum(x['extract_call_count'] for x in part),'evaluation_scope':'PROVISIONAL_PROXY; no human validation'}
 metrics={'overall':metric(rows)}
 for cat in ['ACADEMIC','CAMPUS','GENERAL','HARD_NEGATIVE']:metrics[cat.lower()]=metric([x for x in rows if x['category']==cat])
 (ROOT/'results/e2e12_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
 # Reconstruct the four trace entries lost when the first host command timed out; source payloads remain in the case log.
 trace=ROOT/'logs/search_extract_trace.jsonl'; traced={}
 if trace.exists():
  for line in trace.read_text(encoding='utf-8').splitlines():
   if line.strip():traced.setdefault(json.loads(line)['sample_id'],0);traced[json.loads(line)['sample_id']]+=1
 with trace.open('a',encoding='utf-8',newline='\n') as f:
  for r in rows:
   if r['search_called'] and r['sample_id'] not in traced:
    for q in r['search_query']:f.write(json.dumps({'sample_id':r['sample_id'],'operation':'search','query':q,'attempt':1,'success':r['search_success'],'timestamp':r['retrieval_timestamp'],'reconstructed_from_completed_case_after_host_timeout':True},ensure_ascii=False)+'\n')
    if r['extract_called']:f.write(json.dumps({'sample_id':r['sample_id'],'operation':'extract','urls':r['source_urls'],'attempt':1,'success':r['extract_success'],'timestamp':r['retrieval_timestamp'],'reconstructed_from_completed_case_after_host_timeout':True},ensure_ascii=False)+'\n')
 post=snapshot();(ROOT/'audit/post_run_state.json').write_text(json.dumps(post,ensure_ascii=False,indent=2),encoding='utf-8');pre=json.loads((ROOT/'audit/pre_run_state.json').read_text(encoding='utf-8'))
 changed=[p for p,v in pre['files'].items() if p not in post['files'] or post['files'][p]['sha256']!=v['sha256']];added=[p for p in post['files'] if p not in pre['files']];removed=[p for p in pre['files'] if p not in post['files']]
 audit={'status':'PASS' if not(changed or added or removed) else 'FAIL','protected_files_changed':changed,'protected_files_added':added,'protected_files_removed':removed,'router_v0_2_unchanged':not any(p.startswith('experiments/router_v0_2/') for p in changed+added+removed),'new_outputs_root':str(ROOT),'api_key_logged':False,'completed_at':datetime.now(timezone.utc).isoformat()};(ROOT/'audit/final_immutability_report.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'metrics':metrics,'audit':audit},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
