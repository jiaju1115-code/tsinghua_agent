from __future__ import annotations
import json, pickle, time
from pathlib import Path
import numpy as np
from src.retrieval_v1 import DenseRetrieverV1

ROOT=Path(__file__).resolve().parents[2]
CHUNKS=[json.loads(x) for x in open(ROOT/'data/05_kb_staging/dynamic_campus_v1/chunks/dynamic_chunks_v1.jsonl',encoding='utf-8')]
DE=np.load(ROOT/'experiments/dynamic_retriever_v0_2/embeddings/dynamic_embeddings_v0_2.npy')
VEC=pickle.load(open(ROOT/'experiments/dynamic_retriever_v0/bm25/vectorizer.pkl','rb'))
LEX=np.load(ROOT/'experiments/dynamic_retriever_v0/bm25/matrix.npy')

class ShadowRetrieverV1:
    def __init__(self,strategy='equal_rrf'):
        self.core=DenseRetrieverV1(); self.strategy=strategy; self.sidecars={}
    def retrieve(self,query,case_id):
        started=time.perf_counter(); core=self.core.retrieve(query,case_id); q=self.core._encode_query(query)
        dense=DE@q; lexical=LEX@VEC.transform([query]).toarray()[0]
        di=sorted(range(len(CHUNKS)),key=lambda i:(-float(dense[i]),CHUNKS[i]['chunk_id']))[:20]
        li=sorted(range(len(CHUNKS)),key=lambda i:(-float(lexical[i]),CHUNKS[i]['chunk_id']))[:20]
        lr={i:r+1 for r,i in enumerate(li)}; dr={i:r+1 for r,i in enumerate(di)}
        weights={'equal_rrf':(1.0,1.0),'core_priority':(1.25,1.0),'dynamic_priority':(1.0,1.25)}[self.strategy]
        rows=[]
        for r,x in enumerate(core['ordered_top5_chunks'],1): rows.append((weights[0]/(60+r),'core',x,{'original_rank':r}))
        for i in set(li)|set(di):
            x=CHUNKS[i]; score=weights[1]*((1/(60+lr[i]) if i in lr else 0)+(1/(60+dr[i]) if i in dr else 0))
            frozen={'source_id':x['candidate_id'],'chunk_id':x['chunk_id'],'score':float(score),'title':x['title'],'url':x.get('canonical_url') or '','category':x['category'],'text':x['chunk_text']}
            rows.append((score,'dynamic',frozen,{'candidate_id':x['candidate_id'],'source_xxid':x['source_xxid'],'source_department':x['department'],'published_at':x['published_at'],'temporal_status':x['temporal_status'],'deadline':x['deadline'],'valid_until':x['valid_until'],'canonical_url':x['canonical_url'],'provenance':x['source_provenance'],'lexical_rank':lr.get(i),'dense_rank':dr.get(i)}))
        rows.sort(key=lambda x:(-x[0],x[2]['chunk_id'])); top=rows[:5]; out=[]; side=[]
        for rank,(_,layer,x,meta) in enumerate(top,1):
            row=dict(x); row['rank']=rank; out.append(row); side.append({'rank':rank,'layer':layer,'chunk_id':row['chunk_id'],'source_id':row['source_id'],**meta})
        self.sidecars[case_id]=side
        return {'query':query,'case_id':case_id,'retriever_version':'RAG_RETRIEVAL_V1','corpus_version':'KNOWLEDGE_BASE_V1','ordered_top5_chunks':out,'source_ids':[x['source_id'] for x in out],'chunk_ids':[x['chunk_id'] for x in out],'scores':[x['score'] for x in out],'latency_ms':round((time.perf_counter()-started)*1000,3),'error':None}
