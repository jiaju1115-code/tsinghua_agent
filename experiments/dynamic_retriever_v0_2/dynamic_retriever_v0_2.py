import json, pickle
from pathlib import Path
import numpy as np, torch
from transformers import AutoTokenizer, AutoModel

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'experiments/dynamic_retriever_v0_2'
CH=[json.loads(x) for x in open(BASE/'dense/dynamic_chunks_v0_2.jsonl',encoding='utf-8')]
EMB=np.load(BASE/'embeddings/dynamic_embeddings_v0_2.npy')
V=pickle.load(open(ROOT/'experiments/dynamic_retriever_v0/bm25/vectorizer.pkl','rb'))
LEX=np.load(ROOT/'experiments/dynamic_retriever_v0/bm25/matrix.npy')
TOK=AutoTokenizer.from_pretrained(ROOT/'data/03_knowledge_base/v1/index/model',local_files_only=True)
MODEL=AutoModel.from_pretrained(ROOT/'data/03_knowledge_base/v1/index/model',local_files_only=True); MODEL.eval()
def _dense_vector(query):
    with torch.no_grad():
        e=TOK([query],padding=True,truncation=True,max_length=512,return_tensors='pt')
        return torch.nn.functional.normalize(MODEL(**e).last_hidden_state[:,0,:],p=2,dim=1).numpy()[0]
def retrieve_dynamic_dense(query,top_k=20):
    scores=EMB@_dense_vector(query); order=sorted(range(len(CH)),key=lambda i:(-float(scores[i]),CH[i]['chunk_id']))[:top_k]
    return [{'rank':r+1,'chunk_id':CH[i]['chunk_id'],'candidate_id':CH[i]['candidate_id'],'title':CH[i]['title'],'dense_score':float(scores[i]),'category':CH[i]['category'],'temporal_status':CH[i]['temporal_status'],'source_url':CH[i]['canonical_url']} for r,i in enumerate(order)]
def retrieve_dynamic_hybrid(query,top_k=20,rrf_k=60):
    lexical=LEX@V.transform([query]).toarray()[0]; dense=EMB@_dense_vector(query)
    li=sorted(range(len(CH)),key=lambda i:(-float(lexical[i]),CH[i]['chunk_id']))[:top_k]; di=sorted(range(len(CH)),key=lambda i:(-float(dense[i]),CH[i]['chunk_id']))[:top_k]; lr={i:r+1 for r,i in enumerate(li)}; dr={i:r+1 for r,i in enumerate(di)}; out=[]
    for i in set(li)|set(di): out.append({'chunk_id':CH[i]['chunk_id'],'candidate_id':CH[i]['candidate_id'],'title':CH[i]['title'],'bm25_rank':lr.get(i),'bm25_score':float(lexical[i]),'dense_rank':dr.get(i),'dense_score':float(dense[i]),'rrf_contribution':(1/(rrf_k+lr[i]) if i in lr else 0)+(1/(rrf_k+dr[i]) if i in dr else 0)})
    out.sort(key=lambda x:(-x['rrf_contribution'],x['chunk_id'])); return [dict(x,final_rank=i+1) for i,x in enumerate(out[:top_k])]
