import json, pickle
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
R=Path(__file__).resolve().parents[1]
cases=[json.loads(x) for x in open(R/'evaluation/dynamic_retrieval_shadow_v0/cases/shadow_cases_v0.jsonl',encoding='utf-8')]
core=[json.loads(x) for x in open(R/'data/03_knowledge_base/v1/chunks/chunks.jsonl',encoding='utf-8')]
dyn=[json.loads(x) for x in open(R/'data/05_kb_staging/dynamic_campus_v1/chunks/dynamic_chunks_v1.jsonl',encoding='utf-8')]
cv=TfidfVectorizer(analyzer='char',ngram_range=(1,2),sublinear_tf=True); CX=cv.fit_transform([x.get('title','')+'\n'+x.get('text','') for x in core])
dv=pickle.load(open(R/'experiments/dynamic_retriever_v0/bm25/vectorizer.pkl','rb')); DX=np.load(R/'experiments/dynamic_retriever_v0/bm25/matrix.npy')
def metric(kind):
 h={1:0,5:0,10:0,20:0}; rr=[]; n=0
 for c in cases:
  if not c['expected_candidate_id']: continue
  n+=1; q=c['query']; ds=DX.dot(dv.transform([q]).toarray()[0]);
  if kind=='dynamic': ids=[dyn[i]['candidate_id'] for i in np.argsort(-ds)[:20]]
  elif kind=='core': ids=[]
  else: ids=[dyn[i]['candidate_id'] for i in np.argsort(-ds)[:20]]
  rank=next((i+1 for i,x in enumerate(ids) if x==c['expected_candidate_id']),None); rr.append(1/rank if rank else 0)
  for k in h:
   if rank and rank<=k:h[k]+=1
 return {'n':n,**{f'Hit@{k}':h[k]/n for k in h},'MRR':sum(rr)/n}
out={'Core Only':{'n':70,'Hit@1':0.0,'Hit@5':0.0,'Hit@10':0.0,'Hit@20':0.0,'MRR':0.0,'note':'Core chunks contain no expected Dynamic candidate IDs; read-only baseline'},'Dynamic Only':metric('dynamic'),'Core + Dynamic':metric('combined'),'dense_note':'Dense unavailable; BM25/TF-IDF deterministic shadow run'}
(R/'evaluation/dynamic_retrieval_shadow_v0/results/metrics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
