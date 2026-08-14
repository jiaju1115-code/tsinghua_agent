from __future__ import annotations
import hashlib,json,os,platform
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT.parent
RAG0=DATA/"rag_v0";RAG1=DATA/"rag_v1";AE0=DATA/"answer_eval_v0";AE1=DATA/"answer_eval_v1"
MODEL=RAG1/"indexes"/"dense"/"model"/"model.safetensors"
CRITICAL={
 "rag_v0_chunks":RAG0/"chunks"/"chunks.jsonl",
 "rag_v1_queries":RAG1/"evaluation"/"eval_queries.jsonl",
 "rag_v1_dense_results":RAG1/"evaluation"/"results_dense.jsonl",
 "rag_v1_dense_evidence":RAG1/"evaluation"/"recommended_dense_evidence.jsonl",
 "rag_v1_doc_embeddings":RAG1/"indexes"/"dense"/"document_embeddings.npy",
 "rag_v1_row_mapping":RAG1/"indexes"/"dense"/"row_mapping.jsonl",
 "rag_v1_dense_report":RAG1/"indexes"/"dense"/"index_report.json",
 "ae0_answers":AE0/"results"/"answer_generation_results.jsonl",
 "ae1_group_a":AE1/"results"/"generation_a.jsonl",
 "ae1_group_b":AE1/"results"/"generation_b.jsonl",
 "ae1_ab_metrics":AE1/"results"/"ab_metrics.json",
 "bge_weights":MODEL,
}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
 return h.hexdigest()
def jl(p):return[json.loads(x) for x in p.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
def inventory():
 rows=[]
 for base,dirs,files in os.walk(DATA):
  bp=Path(base)
  if bp==ROOT or ROOT in bp.parents:dirs[:]=[];continue
  for n in sorted(files):
   p=bp/n
   try:s=p.stat()
   except FileNotFoundError:continue
   rows.append({"path":p.relative_to(DATA).as_posix(),"size":s.st_size,"mtime_ns":s.st_mtime_ns})
 rows.sort(key=lambda x:x["path"]);digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(",",":")).encode()).hexdigest();return{"file_count":len(rows),"metadata_sha256":digest,"rows":rows}
def main():
 missing=[n for n,p in CRITICAL.items() if not p.is_file()]
 if missing:raise SystemExit(f"Missing frozen inputs: {missing}")
 a=jl(CRITICAL["ae1_group_a"]);v0=jl(CRITICAL["ae0_answers"]);q=jl(CRITICAL["rag_v1_queries"]);d=jl(CRITICAL["rag_v1_dense_results"])
 if not(len(a)==len(v0)==len(q)==len(d)==38):raise SystemExit("INPUT_INVARIANCE_FAILURE: count")
 if [x["question_id"] for x in a]!=[x["question_id"] for x in v0] or [x["question_id"] for x in a]!=[x["query_id"] for x in q]:raise SystemExit("INPUT_INVARIANCE_FAILURE: order/text IDs")
 bad=[x["question_id"] for x,y in zip(a,v0) if x["generated_answer"]!=y["generated_answer"]]
 if bad:raise SystemExit(f"INPUT_INVARIANCE_FAILURE: answers {bad}")
 for x,y in zip(a,d):
  if x["question"]!=y["query"] or x["retrieved_chunk_ids"]!=[z["chunk_id"] for z in y["top_5"]] or any(abs(s-z["score"])>1e-12 for s,z in zip(x["retrieval_scores"],y["top_5"])):raise SystemExit(f"INPUT_INVARIANCE_FAILURE: {x['question_id']}")
 inv=inventory();payload={"created_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS","counts":{"questions":38,"answers_exact_match":38,"top_k":5},"policy":{"regenerated_answers":False,"retrieval_expanded":False,"trained_model":False},"critical_inputs":{n:{"path":str(p),"size":p.stat().st_size,"sha256":sha(p)} for n,p in CRITICAL.items()},"external_tree_before":inv,"environment":{"os":platform.platform(),"python":platform.python_version()}}
 (ROOT/"audit").mkdir(parents=True,exist_ok=True);(ROOT/"audit"/"input_freeze.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps({"status":"PASS","questions":38,"answers_exact_match":38,"top_k":5,"external_files":inv["file_count"],"inventory_sha256":inv["metadata_sha256"]},ensure_ascii=False))
if __name__=="__main__":main()
