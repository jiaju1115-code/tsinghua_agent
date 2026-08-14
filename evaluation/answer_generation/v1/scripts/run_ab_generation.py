from __future__ import annotations

import json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT.parent; RAG1=DATA/"rag_v1"
sys.path.insert(0,str(DATA/"answer_eval_v0"/"vendor"))
from llama_cpp import Llama  # noqa:E402

MODEL=Path(r"C:\Users\林宇轩\.cache\huggingface\hub\models--Qwen--Qwen2.5-1.5B-Instruct-GGUF\snapshots\91cad51170dc346986eccefdc2dd33a9da36ead9\qwen2.5-1.5b-instruct-q4_k_m.gguf")
CFG=json.loads((ROOT/"config"/"experiment_config.json").read_text(encoding="utf-8"))
PROMPTS={"A":(ROOT/"config"/"prompt_a_v0.md").read_text(encoding="utf-8"),"B":(ROOT/"config"/"prompt_b_strict.md").read_text(encoding="utf-8")}

def read_jsonl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
def context(ev):
    return "\n\n---\n\n".join(f"[C{i}]\nchunk_id: {x['chunk_id']}\nsource_id: {x['source_id']}\ntitle: {x['title']}\ntext:\n{x['text'].strip()}" for i,x in enumerate(ev,1))
def citations(s): return [f"C{x}" for x in sorted(set(re.findall(r"\[C([1-5])\]",s,re.I)),key=int)]

def main():
    q=read_jsonl(RAG1/"evaluation"/"eval_queries.jsonl"); d=read_jsonl(RAG1/"evaluation"/"results_dense.jsonl"); e=read_jsonl(RAG1/"evaluation"/"recommended_dense_evidence.jsonl")
    if not ([x["query_id"] for x in q]==[x["query_id"] for x in d]==[x["query_id"] for x in e]) or len(q)!=38: raise SystemExit("Frozen inputs mismatch")
    c=CFG["generation"]
    llm=Llama(model_path=str(MODEL),n_ctx=c["context_length"],n_threads=c["threads"],n_threads_batch=c["batch_threads"],n_batch=c["prompt_batch_size"],n_ubatch=c["micro_batch_size"],seed=c["seed"],n_gpu_layers=0,verbose=False)
    for group in ("A","B"):
        out=ROOT/"results"/f"generation_{group.lower()}.jsonl"; out.parent.mkdir(parents=True,exist_ok=True)
        existing=read_jsonl(out) if out.exists() else []; done={x["question_id"] for x in existing}
        started_all=time.perf_counter()
        with out.open("a",encoding="utf-8",newline="\n") as fh:
            for idx,(qq,dd,ee) in enumerate(zip(q,d,e),1):
                if qq["query_id"] in done: continue
                ctx=context(ee["evidence"])
                warn="\n本题属于交通/校车/路线/校园出入范围；没有直接证据时必须拒答。" if qq["category"]=="交通服务" else ""
                user=f"资料如下：\n\n{ctx}\n\n问题：{qq['query']}{warn}\n\n只输出不超过120个汉字的回答正文。"
                t=time.perf_counter(); resp=llm.create_chat_completion(messages=[{"role":"system","content":PROMPTS[group]},{"role":"user","content":user}],temperature=c["temperature"],max_tokens=c["max_new_tokens"],seed=c["seed"],repeat_penalty=c["repeat_penalty"])
                sec=time.perf_counter()-t; ans=resp["choices"][0]["message"]["content"].strip(); cites=citations(ans); refused=bool(re.search(r"无法确认|资料不足|无法根据|没有.{0,8}资料",ans))
                row={"group":group,"question_id":qq["query_id"],"question":qq["query"],"eval_status":"CONFIRMED" if qq["eval_status"]=="EXISTING_SMOKE" else "PROVISIONAL_EVAL","source_eval_status":qq["eval_status"],"category":qq["category"],"expected_source_id":qq.get("expected_source_id"),"expected_source_status":qq.get("expected_source_status"),"expected_evidence_keyword":qq.get("expected_evidence_keyword"),"retriever":"BAAI/bge-small-zh-v1.5 frozen RAG V1 Dense Top-5","retrieved_chunk_ids":[x["chunk_id"] for x in dd["top_5"]],"retrieved_document_ids":[x["source_id"] for x in dd["top_5"]],"retrieval_scores":[x["score"] for x in dd["top_5"]],"retrieved_context":[{"context_id":f"C{i}",**x} for i,x in enumerate(ee["evidence"],1)],"generation_prompt":{"system":PROMPTS[group],"user":user},"generated_answer":ans,"answer_citations":cites,"model_insufficient_evidence":refused,"latency":{"generation_seconds":sec,"prompt_tokens":resp.get("usage",{}).get("prompt_tokens"),"completion_tokens":resp.get("usage",{}).get("completion_tokens"),"total_tokens":resp.get("usage",{}).get("total_tokens")},"generation_model":c,"generation_status":"COMPLETED","finish_reason":resp["choices"][0].get("finish_reason"),"generated_utc":datetime.now(timezone.utc).isoformat()}
                fh.write(json.dumps(row,ensure_ascii=False)+"\n"); fh.flush(); print(f"[{group} {idx:02d}/38] {qq['query_id']} {sec:.2f}s citations={cites} refusal={refused}",flush=True)
        rows=read_jsonl(out)
        if len(rows)!=38 or len({x["question_id"] for x in rows})!=38: raise SystemExit(f"Group {group} incomplete")
        log={"group":group,"status":"PASS","completed":38,"run_seconds":time.perf_counter()-started_all,"output":str(out),"model":c}
        (ROOT/"logs").mkdir(exist_ok=True); (ROOT/"logs"/f"generation_{group.lower()}.json").write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__": main()
