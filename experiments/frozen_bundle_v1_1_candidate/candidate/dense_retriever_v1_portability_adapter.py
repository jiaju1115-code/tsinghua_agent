from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
from transformers import AutoModel, AutoTokenizer
from src.retrieval_v1.adapter import DenseRetrieverV1

ROOT=Path(__file__).resolve().parents[3]
LEGACY=ROOT/'data/03_knowledge_base/v1'
def _hash(data): return hashlib.sha256(data).hexdigest()
def _canonical(path):
    text=path.read_bytes().decode('utf-8-sig')
    return text.replace('\r\n','\n').replace('\r','\n').encode('utf-8')
class DenseRetrieverV1PortabilityAdapter(DenseRetrieverV1):
    """Shadow-only, fail-closed V1 loader using CANONICAL_TEXT_V1 for text."""
    def __init__(self,bundle_root=LEGACY):
        self.root=Path(bundle_root).resolve(); self.config=json.loads((self.root/'config/retriever_v1.json').read_text(encoding='utf-8'))
        kb=json.loads((self.root/'audit/knowledge_base_v1_freeze.json').read_text(encoding='utf-8')); rag=json.loads((self.root/'audit/rag_retrieval_v1_freeze.json').read_text(encoding='utf-8'))
        expected_manifest={'knowledge_base_v1_freeze.json':rag['knowledge_base_freeze_sha256'],'rag_retrieval_v1_freeze.json':(self.root/'audit/rag_retrieval_v1_freeze.json.sha256').read_text(encoding='ascii').strip()}
        for name,expected in expected_manifest.items():
            if _hash(_canonical(self.root/'audit'/name))!=expected: raise RuntimeError('canonical freeze manifest hash mismatch: '+name)
        checks={'config/retriever_v1.json':rag['retriever_config_sha256'],'chunks/chunks.jsonl':rag['chunks_sha256'],'index/document_embeddings.npy':rag['index_sha256']}
        for rel,expected in checks.items():
            p=self.root/rel; actual=_hash(p.read_bytes()) if p.suffix=='.npy' else _hash(_canonical(p))
            if actual!=expected: raise RuntimeError('portable artifact hash mismatch: '+rel)
        self.chunks=[json.loads(x) for x in (self.root/self.config['artifacts']['chunks_path']).read_text(encoding='utf-8').splitlines() if x.strip()]
        self.embeddings=np.load(self.root/self.config['artifacts']['embeddings_path'],mmap_mode='r',allow_pickle=False)
        if len(self.chunks)!=len(self.embeddings): raise RuntimeError('chunk/embedding count mismatch')
        model_path=self.root/self.config['artifacts']['model_path']; self.tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True); self.model=AutoModel.from_pretrained(model_path,local_files_only=True).eval()
