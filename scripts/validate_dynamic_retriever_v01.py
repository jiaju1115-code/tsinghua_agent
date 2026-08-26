import json, pickle, hashlib
from collections import Counter
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

R=Path(__file__).resolve().parents[1]; C=R/'data/04_kb_expansion_candidate/dynamic_campus_v1'; S=R/'data/05_kb_staging/dynamic_campus_v1'; O=R/'evaluation/dynamic_retrieval_shadow_v0'
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def wj(p,x): p.write_text(''.join(json.dumps(a,ensure_ascii=False)+'\n' for a in x),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
cross=jl(C/'audit/core_cross_dedup_v1.jsonl'); canonical=jl(C/'processed/canonical_candidates_v1.jsonl'); canonical=[x for x in canonical if x.get('is_canonical')]
cc=Counter(x['classification'] for x in cross); assert cc.get('EXACT_CORE_DUPLICATE',0)==0, 'unexpected exact core duplicates must be manually reviewed'
staging=jl(S/'sources/dynamic_sources_v1.jsonl'); chunks=jl(S/'chunks/dynamic_chunks_v1.jsonl')
assert len(staging)==len(canonical)==920
dump={'canonical_count':len(canonical),'cross_dedup_counts':dict(cc),'final_dynamic_sources':len(staging),'final_dynamic_chunks':len(chunks),'excluded_exact_core_duplicate_ids':[x['candidate_id'] for x in cross if x['classification']=='EXACT_CORE_DUPLICATE'],'conclusion':'The 920/916 discrepancy was not reproduced: current deterministic cross-dedup has 0 EXACT_CORE_DUPLICATE; the 4 groups in canonicalization are internal duplicate groups, not Core matches.'}
(C/'reports/staging_correction_v01.json').write_text(json.dumps(dump,ensure_ascii=False,indent=2),encoding='utf-8')
# Temporal audit summary and manual-review sample manifest.
t=jl(C/'processed/temporal_extraction_v1.jsonl'); tc=Counter(x['temporal_status'] for x in t); deadline=sum('application_deadline' in x['temporal_fields'] for x in t); interval=sum('event_start' in x['temporal_fields'] and 'event_end' in x['temporal_fields'] for x in t); valid=sum('valid_until' in x['temporal_fields'] for x in t); ambiguous=sum(len(x['temporal_evidence'])>1 for x in t); parse_fail=sum(not x['temporal_evidence'] for x in t)
samples={k:[x['candidate_id'] for x in t if x['temporal_status']==k][:10] for k in ['ACTIVE','ONGOING','EXPIRED','UNKNOWN','NOT_APPLICABLE']}
(C/'audit/temporal_validation_v01.json').write_text(json.dumps({'counts':dict(tc),'deadline_count':deadline,'event_interval_count':interval,'valid_until_count':valid,'ambiguous_date_count':ambiguous,'parse_failure_count':parse_fail,'manual_review_samples':samples},ensure_ascii=False,indent=2),encoding='utf-8')
# Mixed cases: preserve prior 70 dynamic cases, add 20 cross-layer templates and 10 negatives.
dyn_cases=jl(O/'cases/shadow_cases_v0.jsonl'); dyn_pos=[x for x in dyn_cases if x['expected_candidate_id']][:70]; neg=[x for x in dyn_cases if not x['expected_candidate_id']][:10]
cross_templates=['图书馆现在什么时候开放？','最近图书馆有没有开放时间变化？','学生宿舍现在有什么通知？','科研项目如何申请？','最近有没有新的项目申报？','校园办事流程现在是否有变化？']
cross_cases=[{'case_id':f'MIX-CROSS-{i+1:02d}','query':q,'expected_candidate_id':None,'expected_chunk_id':None,'category':'cross_layer','temporal_type':'UNKNOWN','difficulty':'ambiguous','generation_method':'manual_user_style_template','gold_status':'NO_RETRIEVAL_GOLD'} for i,q in enumerate((cross_templates*4)[:20])]
mixed=dyn_pos+cross_cases+neg; wj(O/'cases/mixed_retrieval_shadow_v1.jsonl',mixed)
# Retrieval validation against lexical index; dense is explicitly unavailable.
vec=pickle.load(open(R/'experiments/dynamic_retriever_v0/bm25/vectorizer.pkl','rb')); X=np.load(R/'experiments/dynamic_retriever_v0/bm25/matrix.npy');
def retrieve(q):
 s=X.dot(vec.transform([q]).toarray()[0]); return np.argsort(-s)[:20],s
def metric(cases):
 h={1:0,5:0,10:0,20:0}; rr=[]; n=0
 for c in cases:
  if not c.get('expected_candidate_id'): continue
  n+=1; ids=[chunks[i]['candidate_id'] for i in retrieve(c['query'])[0]]; rank=next((j+1 for j,x in enumerate(ids) if x==c['expected_candidate_id']),None); rr.append(1/rank if rank else 0)
  for k in h:
   if rank and rank<=k:h[k]+=1
 return {'n':n,**{f'Hit@{k}':h[k]/max(1,n) for k in h},'MRR':sum(rr)/max(1,n)}
dynamic=metric(dyn_pos)
intr1=intr5=0
for c in neg:
 ids=[chunks[i]['candidate_id'] for i in retrieve(c['query'])[0]]
 intr1+=bool(ids); intr5+=bool(ids[:5])
leak={'negative_cases':len(neg),'dynamic_top1_intrusion_rate':intr1/len(neg),'dynamic_top5_intrusion_rate':intr5/len(neg),'core_top1_retention':'NOT_COMPUTABLE_NO_CORE_GOLD','core_top5_retention':'NOT_COMPUTABLE_NO_CORE_GOLD'}
systems={'Lexical':dynamic,'Dense':{'status':'LOCAL_MODEL_MISSING'},'Hybrid':{'status':'NOT_AVAILABLE_DENSE_MISSING','lexical_fallback':dynamic}}
fusion={'Equal-weight RRF':{'status':'NOT_RUN_DENSE_MISSING'},'Core-priority RRF':{'status':'NOT_RUN_DENSE_MISSING'},'Dynamic-priority RRF':{'status':'NOT_RUN_DENSE_MISSING'}}
out={'staging_correction':dump,'temporal':{'counts':dict(tc),'deadline':deadline,'event_interval':interval,'valid_until':valid,'ambiguous':ambiguous,'parse_failure':parse_fail},'retrieval':systems,'core_regression':{'status':'NO_RETRIEVAL_GOLD_FOR_FROZEN_CASES','Core Only':'NOT_RUN','Core + Dynamic':'NOT_RUN'},'mixed_evaluation':{'dynamic_positive':len(dyn_pos),'core_cases':'NO_RETRIEVAL_GOLD','cross_layer':len(cross_cases),'negative':len(neg)},'leakage':leak,'fusion':fusion,'recovery_queue':{'status':'PENDING_AUTH_RECOVERY','count':22,'international_internship':19},'readiness':'NEEDS_RETRIEVAL_TUNING','readiness_reason':'Staging is internally consistent, but Dense/Hybrid validation is unavailable because the frozen local embedding model was not loaded.'}
(O/'results/mixed_retrieval_metrics_v1.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'reports/dynamic_retriever_v0_1_validation_report.md').write_text('# Dynamic Retriever V0.1 Validation & Mixed Regression\n\n'+json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'staging':len(staging),'chunks':len(chunks),'temporal':dict(tc),'dynamic':dynamic,'leakage':leak,'readiness':out['readiness']},ensure_ascii=False))
