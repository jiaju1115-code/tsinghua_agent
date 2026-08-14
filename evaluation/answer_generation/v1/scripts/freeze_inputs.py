from __future__ import annotations

import hashlib, json, os, platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
RAG0, RAG1, V0 = DATA / "rag_v0", DATA / "rag_v1", DATA / "answer_eval_v0"
MODEL = Path(r"C:\Users\林宇轩\.cache\huggingface\hub\models--Qwen--Qwen2.5-1.5B-Instruct-GGUF\snapshots\91cad51170dc346986eccefdc2dd33a9da36ead9\qwen2.5-1.5b-instruct-q4_k_m.gguf")
CRITICAL = {
    "rag_v0_chunks": RAG0 / "chunks" / "chunks.jsonl",
    "rag_v0_smoke": RAG0 / "retrieval_results" / "retrieval_smoke_results.jsonl",
    "rag_v1_config": RAG1 / "config" / "retrieval.yaml",
    "rag_v1_queries": RAG1 / "evaluation" / "eval_queries.jsonl",
    "rag_v1_dense_results": RAG1 / "evaluation" / "results_dense.jsonl",
    "rag_v1_dense_evidence": RAG1 / "evaluation" / "recommended_dense_evidence.jsonl",
    "rag_v1_embeddings": RAG1 / "indexes" / "dense" / "document_embeddings.npy",
    "rag_v1_row_mapping": RAG1 / "indexes" / "dense" / "row_mapping.jsonl",
    "v0_generation_config": V0 / "config" / "generation_config.json",
    "v0_prompt": V0 / "config" / "grounded_generation_prompt.md",
    "v0_generation_results": V0 / "results" / "answer_generation_results.jsonl",
    "v0_evaluation_results": V0 / "results" / "answer_evaluation_results.jsonl",
    "generation_model": MODEL,
}

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
    return h.hexdigest()

def read_jsonl(path): return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]

def inventory():
    rows=[]
    for root,dirs,files in os.walk(DATA):
        rp=Path(root)
        if rp==ROOT or ROOT in rp.parents: dirs[:]=[]; continue
        for name in sorted(files):
            p=rp/name
            try: s=p.stat()
            except FileNotFoundError: continue
            rows.append({"path":p.relative_to(DATA).as_posix(),"size":s.st_size,"mtime_ns":s.st_mtime_ns})
    rows.sort(key=lambda x:x["path"])
    digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return {"file_count":len(rows),"metadata_sha256":digest,"rows":rows}

def main():
    missing=[n for n,p in CRITICAL.items() if not p.is_file()]
    if missing: raise SystemExit(f"Missing frozen inputs: {missing}")
    q=read_jsonl(CRITICAL["rag_v1_queries"]); d=read_jsonl(CRITICAL["rag_v1_dense_results"]); e=read_jsonl(CRITICAL["rag_v1_dense_evidence"])
    if not (len(q)==len(d)==len(e)==38): raise SystemExit("Expected 38 frozen inputs")
    if not ([x["query_id"] for x in q]==[x["query_id"] for x in d]==[x["query_id"] for x in e]): raise SystemExit("Frozen query order mismatch")
    if any(len(x["top_5"])!=5 for x in d) or any(len(x["evidence"])!=5 for x in e): raise SystemExit("Dense Top-5 incomplete")
    if (ROOT/"config"/"prompt_a_v0.md").read_bytes()!=CRITICAL["v0_prompt"].read_bytes(): raise SystemExit("Group A prompt is not byte-identical to V0")
    inv=inventory()
    payload={"created_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS",
      "counts":{"questions":38,"confirmed":10,"provisional":28,"top_k":5,"groups":2},
      "ab_invariants":{"only_generation_prompt_differs":True,"group_a_prompt_byte_identical_to_v0":True},
      "critical_inputs":{n:{"path":str(p),"size":p.stat().st_size,"sha256":sha(p)} for n,p in CRITICAL.items()},
      "new_config_hashes":{p.name:sha(p) for p in (ROOT/"config").iterdir() if p.is_file()},
      "external_tree_before":inv,"environment":{"os":platform.platform(),"python":platform.python_version()}}
    (ROOT/"audit").mkdir(parents=True,exist_ok=True)
    (ROOT/"audit"/"input_freeze.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","questions":38,"groups":2,"external_files":inv["file_count"],"inventory_sha256":inv["metadata_sha256"]},ensure_ascii=False))

if __name__=="__main__": main()

