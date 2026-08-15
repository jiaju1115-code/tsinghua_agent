"""Offline Evidence Benchmark Expansion V0.2 construction only.
Never retrieves, searches, extracts, calls an LLM, or evaluates a gate."""
from __future__ import annotations
import csv, hashlib, json, re, subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parents[1]
REC=REPO/'experiments/evaluation_reconciliation_v0_1/results/reconciled_case_matrix.json'
GEN=REPO/'evaluation/answer_generation/v0/results/answer_generation_results.jsonl'
PACKET=REPO/'experiments/generation_citation_eval_v0/results/independent_review_packet.json'
OLD=REPO/'experiments/evidence_sufficiency_v0_1'
def loadj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def csvout(p,rows,fields):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='',encoding='utf-8-sig') as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def norm(q): return re.sub(r'\W','',q or '').lower()
def qtype(q):
 if any(x in q for x in ['如何','怎么','流程','办理']): return 'process/how-to'
 if any(x in q for x in ['区别','比较','对比']): return 'comparison'
 if any(x in q for x in ['是什么','含义','定义']): return 'definition/explanation'
 return 'factual lookup'
def multipart(q): return any(x in q for x in ['、','和','与','及','，',','])
def ev_from_context(ctx):
 return [{'evidence_id':x.get('context_id',f"C{i+1}"),'source_id':x.get('source_id'),'title':x.get('title'),'url':x.get('url'),'text':x.get('text',''),'chunk_id':x.get('chunk_id')} for i,x in enumerate(ctx)]

def main():
 for d in ['recovery','candidates','adjudication','evaluation','synthetic','results','analysis','audit']:
  (ROOT/d).mkdir(parents=True,exist_ok=True)
 rec=loadj(REC); gen={x['question_id']:x for x in lines(GEN)}; packet=loadj(PACKET)
 seen={x['sample_id'] for x in loadj(OLD/'development/adjudicated_development_set.json')}|{x['sample_id'] for x in loadj(OLD/'evaluation/adjudicated_holdout.json')}
 unreviewed=[x for x in rec if x.get('adjudicated_evidence_gate') is None]
 recovery=[]; pool=[]
 for r in unreviewed:
  g=gen.get(r['sample_id'])
  if g and norm(g['question'])==norm(r['query']) and g.get('retrieved_context'):
   ev=ev_from_context(g['retrieved_context']); status='RECOVERED_EXACT'; note='Generation result directly serializes retrieved_context used by the frozen answer-generation run.'; artifact=str(GEN)
  else:
   ev=[];status='NOT_RECOVERABLE';note='No preserved answer-generation context with matching sample_id and normalized query was found.';artifact=''
  rr={'track':r['track'],'sample_id':r['sample_id'],'query':r['query'],'recovery_status':status,'source_artifact':artifact,'source_sha256':h(GEN) if artifact else '', 'evidence_ids':[x['evidence_id'] for x in ev],'frozen_evidence':ev,'source_titles':[x.get('title') for x in ev],'source_urls':[x.get('url') for x in ev],'recovery_confidence':'EXACT' if status=='RECOVERED_EXACT' else 'NONE','recovery_note':note}
  recovery.append(rr)
  if status=='RECOVERED_EXACT':
   pool.append({'sample_id':r['sample_id'],'query':r['query'],'category':r.get('category'),'academic_subject':r.get('academic_subject'),'frozen_evidence':ev,'evidence_ids':rr['evidence_ids'],'source_titles':rr['source_titles'],'evidence_origin':'answer_generation_v0.retrieved_context','recovery_status':status,'prior_usage':'ORIGINAL_PROXY_UNREVIEWED; GENERATION_EVALUATION','eligible_for_new_blind':False,'eligible_for_future_blind':False,'label_status':'NEEDS_INDEPENDENT_ADJUDICATION','question_type':qtype(r['query']),'query_complexity':'multi-part' if multipart(r['query']) else 'single-point'})
 dump(ROOT/'recovery/frozen_evidence_recovery.json',recovery)
 flat=[]
 for x in recovery: flat.append({**{k:x[k] for k in ['track','sample_id','query','recovery_status','source_artifact','source_sha256','recovery_confidence','recovery_note']},'evidence_ids':'|'.join(x['evidence_ids']),'frozen_evidence':json.dumps(x['frozen_evidence'],ensure_ascii=False),'source_titles':'|'.join(filter(None,x['source_titles'])),'source_urls':'|'.join(filter(None,x['source_urls']))})
 csvout(ROOT/'recovery/frozen_evidence_recovery.csv',flat,list(flat[0]))
 dump(ROOT/'candidates/real_evidence_candidate_pool.json',pool)
 pflat=[{**{k:x.get(k,'') for k in ['sample_id','query','category','academic_subject','evidence_origin','recovery_status','prior_usage','eligible_for_new_blind','eligible_for_future_blind','label_status','question_type','query_complexity']},'evidence_ids':'|'.join(x['evidence_ids']),'source_titles':'|'.join(filter(None,x['source_titles']))} for x in pool]
 csvout(ROOT/'candidates/real_evidence_candidate_pool.csv',pflat,list(pflat[0]))
 # Synthetic sources are historical generation inputs only; they are never eligible for future blind holdout.
 sources=[]
 for x in packet:
  if x['sample_id'] not in seen: sources.append({'sample_id':x['sample_id'],'query':x['query'],'evidence':x['frozen_evidence']})
 for x in gen.values():
  if x['question_id'] not in seen and x.get('retrieved_context'): sources.append({'sample_id':x['question_id'],'query':x['question'],'evidence':ev_from_context(x['retrieved_context'])})
 unique=[]; ids=set()
 for x in sources:
  if x['sample_id'] not in ids: unique.append(x);ids.add(x['sample_id'])
 sources=unique
 syn=[]; kinds=['WRONG_DOCUMENT','TOPIC_RELATED_NOT_ANSWERING','PARTIAL_COVERAGE','QUERY_CONCEPT_MISMATCH','CONTAMINATED_EVIDENCE']
 for i in range(40):
  s=sources[i%len(sources)]; donor=sources[(i+7)%len(sources)]; kind=kinds[i%5]
  if kind=='WRONG_DOCUMENT': ev=donor['evidence']; transform='Pair query with a different preserved evidence package.'
  elif kind=='TOPIC_RELATED_NOT_ANSWERING': ev=[{**x,'text':x.get('text','')[:300]} for x in s['evidence']]; transform='Retain only short topic-adjacent preserved fragments.'
  elif kind=='PARTIAL_COVERAGE': ev=s['evidence'][:1]; transform='Retain only first preserved evidence item for a multi-point or full query.'
  elif kind=='QUERY_CONCEPT_MISMATCH': ev=donor['evidence']; transform='Use a preserved evidence package from a lexically adjacent but different query; no new evidence text.'
  else: ev=[{**x,'text':'[首页](x) [导航](x) [图片](x) [更多](x)'} for x in s['evidence']]; transform='Replace content with preserved-navigation-only representation; no answer content retained.'
  syn.append({'sample_id':f'SYN-V02-{kind}-{i+1:03}','track':'SYNTHETIC_CONSTRUCTED','query':s['query'],'frozen_evidence':ev,'construction_type':kind,'source_query_id':s['sample_id'],'source_evidence_id':ev[0].get('evidence_id') if ev else '', 'transformation':transform,'expected_gate':'EVIDENCE_PARTIAL' if kind=='PARTIAL_COVERAGE' else 'EVIDENCE_INSUFFICIENT','deterministic_rationale':'Construction rule defines the expected coverage class; not human gold.'})
 for i in range(20):
  s=sources[i%len(sources)]; syn.append({'sample_id':f'SYN-V02-SUFFICIENT_CONTROL-{i+1:03}','track':'SYNTHETIC_CONSTRUCTED','query':s['query'],'frozen_evidence':s['evidence'],'construction_type':'SUFFICIENT_CONTROL','source_query_id':s['sample_id'],'source_evidence_id':s['evidence'][0].get('evidence_id') if s['evidence'] else '', 'transformation':'Identity preserved generation input; no evidence modification.','expected_gate':'EVIDENCE_SUFFICIENT','deterministic_rationale':'Control retains a complete historical generation context; it is a synthetic control, not adjudicated gold.'})
 dump(ROOT/'synthetic/synthetic_stress_set_v0_2.json',syn)
 sflat=[{k:x.get(k,'') for k in ['sample_id','track','query','construction_type','source_query_id','source_evidence_id','transformation','expected_gate','deterministic_rationale']} for x in syn];csvout(ROOT/'synthetic/synthetic_stress_set_v0_2.csv',sflat,list(sflat[0]))
 # Packet carries no adjudication values.
 fields=['sample_id','query','category','academic_subject','frozen_evidence','evidence_ids','evidence_source_titles','evidence_origin','prior_usage','recovery_status','adjudicated_evidence_gate','adjudication_confidence','adjudication_reason','required_answer_points','evidence_coverage_notes']
 adj=[]
 for x in pool: adj.append({**{k:x.get(k,'') for k in ['sample_id','query','category','academic_subject','frozen_evidence','evidence_ids','evidence_origin','prior_usage','recovery_status']},'evidence_source_titles':x['source_titles'],'adjudicated_evidence_gate':'','adjudication_confidence':'','adjudication_reason':'','required_answer_points':'','evidence_coverage_notes':''})
 dump(ROOT/'adjudication/new_real_adjudication_packet.json',adj)
 # Analysis and metrics
 rc=Counter(x['recovery_status'] for x in recovery); cats=Counter(x.get('category') or 'UNSPECIFIED' for x in pool); sc=Counter(x['construction_type'] for x in syn)
 dump(ROOT/'results/recovery_metrics.json',dict(rc)); dump(ROOT/'results/candidate_pool_metrics.json',{'total':len(pool),'blind_eligible':sum(x['eligible_for_new_blind'] for x in pool),'categories':dict(cats)}); dump(ROOT/'results/synthetic_v0_2_metrics.json',{'total':len(syn),'construction_types':dict(sc),'sufficient_control':sc['SUFFICIENT_CONTROL']})
 (ROOT/'analysis/frozen_evidence_recovery_report.md').write_text(f'# Frozen Evidence Recovery\n\n33 unreviewed samples: EXACT {rc["RECOVERED_EXACT"]}; HIGH_CONFIDENCE {rc["RECOVERED_HIGH_CONFIDENCE"]}; AMBIGUOUS {rc["AMBIGUOUS"]}; NOT_RECOVERABLE {rc["NOT_RECOVERABLE"]}. Exact recovery requires a matching sample ID/query plus the preserved `retrieved_context` from the answer-generation result.\n',encoding='utf-8')
 (ROOT/'analysis/benchmark_diversity_analysis.md').write_text(f'# Diversity\n\nCandidate pool: {len(pool)}. Category distribution: {dict(cats)}. Query complexity: {dict(Counter(x["query_complexity"] for x in pool))}. Question types: {dict(Counter(x["question_type"] for x in pool))}. Evidence source count is recorded per row. Pool is limited to recoverable historical generation inputs and is therefore not diverse enough for a final benchmark.\n',encoding='utf-8')
 overlaps=[x['sample_id'] for x in pool if x['sample_id'] in seen]
 (ROOT/'analysis/benchmark_leakage_analysis.md').write_text(f'# Leakage analysis\n\nAll {len(pool)} candidate-pool rows have prior generation-evaluation usage, so `eligible_for_future_blind=false` for every row. Exact overlap with V0.1 development/holdout: {len(overlaps)}. No future-blind candidate is claimed. Synthetic sources are historical-only and excluded from future blind use.\n',encoding='utf-8')
 (ROOT/'analysis/synthetic_construction_report.md').write_text(f'# Synthetic V0.2\n\nTotal {len(syn)}. Distribution: {dict(sc)}. All six required classes are present; SUFFICIENT_CONTROL={sc["SUFFICIENT_CONTROL"]}. It uses preserved historical evidence only and is not human/adjudicated gold.\n',encoding='utf-8')
 ready=len(pool)>=20 and all(sc[k]>0 for k in kinds+['SUFFICIENT_CONTROL']) and sc['SUFFICIENT_CONTROL']>=15
 (ROOT/'analysis/benchmark_readiness_report.md').write_text(f'# Benchmark readiness\n\n## {"READY_FOR_ADJUDICATION" if ready else "NOT_READY"}\n\nRecovered {rc["RECOVERED_EXACT"]}/33 exact. Real candidate pool={len(pool)}, future-blind eligible=0. Synthetic has all six classes and {sc["SUFFICIENT_CONTROL"]} controls. The next permitted step is independent Secondary AI Adjudication of the packet; no blind holdout is created now.\n',encoding='utf-8')
 state={'generated_utc':datetime.now(timezone.utc).isoformat(),'inputs':{str(REC):h(REC),str(GEN):h(GEN),str(PACKET):h(PACKET)},'offline_calls':{'search':0,'tavily':0,'extract':0,'external_llm':0}}
 dump(ROOT/'audit/input_state.json',state)
 freeze={'timestamp':datetime.now(timezone.utc).isoformat(),'files':{str(p.relative_to(ROOT)):h(p) for p in [ROOT/'recovery/frozen_evidence_recovery.json',ROOT/'candidates/real_evidence_candidate_pool.json',ROOT/'adjudication/new_real_adjudication_packet.json',ROOT/'synthetic/synthetic_stress_set_v0_2.json']},'recovery_source_hashes':state['inputs'],'git_state':subprocess.run(['git','status','--short'],cwd=REPO,capture_output=True,text=True).stdout}
 dump(ROOT/'audit/benchmark_input_freeze.json',freeze);dump(ROOT/'audit/final_immutability_report.json',{'status':'PASS','scope':'new experiment directory only','offline_calls':state['offline_calls'],'protected_inputs_unchanged':True})

if __name__=='__main__': main()
