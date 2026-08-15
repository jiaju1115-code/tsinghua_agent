from __future__ import annotations
import csv,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
QUEUE=ROOT/'results/human_review_queue.csv'
TRACK_A=REPO/'evaluation/answer_generation/v0/results/answer_eval_merged.jsonl'
TRACK_B=REPO/'experiments/e2e12_router_v0_2/results/e2e12_results.json'
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def safe(v):return '' if v is None else v
def main():
 queue=list(csv.DictReader(QUEUE.open(encoding='utf-8-sig')))
 a={x['question_id']:x for x in jl(TRACK_A)}; b={x['sample_id']:x for x in json.loads(TRACK_B.read_text(encoding='utf-8'))}
 out=[]
 for q in queue:
  track,sid=q['track'],q['sample_id']; src=a.get(sid) if track=='A' else b.get(sid); recoverable=bool(src)
  if recoverable and track=='A':
   evidence=src.get('retrieved_context') or []; answer=src.get('generated_answer',''); citations=src.get('answer_citations') or src.get('inline_answer_citations') or []
  elif recoverable:
   evidence=src.get('evidence') or []; answer=src.get('final_answer',''); citations=[]
   import re
   citations=[f'C{x}' for x in re.findall(r'\[C(\d+)\]',answer)]
  else:evidence=[];answer='';citations=[]
  source_ids=[];titles=[];blocks=[]
  for i,e in enumerate(evidence,1):
   eid=e.get('context_id') or e.get('evidence_id') or f'C{i}'; sid2=e.get('source_id') or e.get('source_url') or ''; title=e.get('title') or e.get('source_title') or ''
   source_ids.append(sid2);titles.append(title);blocks.append({'evidence_id':eid,'source_id':sid2,'title':title,'url':e.get('url') or e.get('source_url') or '','text':e.get('text') or e.get('span_text') or ''})
  row={'track':track,'sample_id':sid,'query':q.get('query',''),'category':q.get('category',''),'academic_subject':q.get('academic_subject',''),'evidence_gate':q.get('evidence_gate',''),'frozen_evidence':blocks if recoverable and blocks else ('EVIDENCE_NOT_RECOVERABLE' if not recoverable else []),'evidence_source_ids':source_ids if recoverable else 'EVIDENCE_NOT_RECOVERABLE','evidence_source_titles':titles if recoverable else 'EVIDENCE_NOT_RECOVERABLE','generated_answer':answer if recoverable else 'EVIDENCE_NOT_RECOVERABLE','generated_citations':citations if recoverable else 'EVIDENCE_NOT_RECOVERABLE','original_correctness_proxy':q.get('correctness_0_to_2',''),'original_faithfulness_proxy':q.get('faithfulness_0_to_2',''),'original_completeness_proxy':q.get('completeness_ratio_proxy',''),'original_unsupported_proxy':q.get('unsupported_claims_proxy',''),'original_failure_labels':q.get('failure_labels',''),'original_primary_failure_type':q.get('primary_failure_type','')}
  out.append(row)
 (ROOT/'results/independent_review_packet.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'rows':len(out),'recoverable':sum(x['frozen_evidence']!='EVIDENCE_NOT_RECOVERABLE' for x in out),'not_recoverable':sum(x['frozen_evidence']=='EVIDENCE_NOT_RECOVERABLE' for x in out)},ensure_ascii=False))
if __name__=='__main__':main()
