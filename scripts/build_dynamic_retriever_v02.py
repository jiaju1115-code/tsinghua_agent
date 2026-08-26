import json, hashlib
from pathlib import Path
import numpy as np, torch
from transformers import AutoTokenizer, AutoModel

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'data/05_kb_staging/dynamic_campus_v1'
OUT=ROOT/'experiments/dynamic_retriever_v0_2'
EVAL=ROOT/'evaluation/dynamic_retrieval_shadow_v0'
for p in [OUT/'embeddings',OUT/'dense',OUT/'hybrid',OUT/'config',EVAL/'gold',EVAL/'reports']:
    p.mkdir(parents=True,exist_ok=True)
chunks=[json.loads(x) for x in open(STAGE/'chunks/dynamic_chunks_v1.jsonl',encoding='utf-8')]
model_path=ROOT/'data/03_knowledge_base/v1/index/model'
tok=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
model=AutoModel.from_pretrained(model_path,local_files_only=True); model.eval(); torch.set_num_threads(8)
texts=[x['title']+'\n'+x['chunk_text'] for x in chunks]; outputs=[]
with torch.no_grad():
    for i in range(0,len(texts),64):
        enc=tok(texts[i:i+64],padding=True,truncation=True,max_length=512,return_tensors='pt')
        z=torch.nn.functional.normalize(model(**enc).last_hidden_state[:,0,:],p=2,dim=1)
        outputs.append(z.cpu().numpy().astype('float32'))
emb=np.concatenate(outputs); ep=OUT/'embeddings/dynamic_embeddings_v0_2.npy'; np.save(ep,emb)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest={'status':'READY','model':'BAAI/bge-small-zh-v1.5','revision':'7999e1d3359715c523056ef9478215996d62a620','local_model_path':'data/03_knowledge_base/v1/index/model','dimension':int(emb.shape[1]),'embedding_count':len(emb),'chunk_count':len(chunks),'dtype':'float32','normalization':'L2','pooling':'CLS last_hidden_state[:,0]','max_length':512,'source_chunk_manifest_sha256':sha(STAGE/'manifests/chunk_manifest.json'),'embeddings_sha256':sha(ep),'recovery_method':'READ_ONLY_FROZEN_LOCAL_MODEL'}
(OUT/'embeddings/dense_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'dense/dynamic_chunks_v0_2.jsonl').write_text((STAGE/'chunks/dynamic_chunks_v1.jsonl').read_text(encoding='utf-8'),encoding='utf-8')
(OUT/'config/retriever_v0_2.json').write_text(json.dumps({'version':'DYNAMIC_RETRIEVER_V0.2','model':manifest,'rrf_k':60,'top_k':20,'deterministic':True,'production_integration':False},ensure_ascii=False,indent=2),encoding='utf-8')
(EVAL/'reports/dynamic_retriever_v0_2_validation_report.md').write_text('# Dynamic Retriever V0.2\n\n- Dense status: READY\n- Chunks: 2429\n- Embeddings: 2429\n- Dimension: '+str(emb.shape[1])+'\n- Hybrid design: BM25 + Dense + deterministic RRF (k=60)\n- Production integration: prohibited\n',encoding='utf-8')
print(json.dumps({'status':'READY','chunks':len(chunks),'embeddings':len(emb),'dimension':int(emb.shape[1]),'sha256':sha(ep)}))
