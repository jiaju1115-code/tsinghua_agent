from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
DATA = BASE.parent
RAG1 = DATA / "rag_v1"
VENDOR = BASE / "vendor"
sys.path.insert(0, str(VENDOR))

from llama_cpp import Llama  # noqa: E402


MODEL = Path(r"C:\Users\林宇轩\.cache\huggingface\hub\models--Qwen--Qwen2.5-1.5B-Instruct-GGUF\snapshots\91cad51170dc346986eccefdc2dd33a9da36ead9\qwen2.5-1.5b-instruct-q4_k_m.gguf")
CONFIG = json.loads((BASE / "config" / "generation_config.json").read_text(encoding="utf-8"))
SYSTEM_PROMPT = (BASE / "config" / "grounded_generation_prompt.md").read_text(encoding="utf-8")
OUT = BASE / "results" / "answer_generation_results.jsonl"
LOG = BASE / "logs" / "generation_run.json"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def format_context(evidence: list[dict]) -> str:
    blocks = []
    for i, item in enumerate(evidence, 1):
        blocks.append(
            f"[C{i}]\n"
            f"chunk_id: {item['chunk_id']}\nsource_id: {item['source_id']}\ntitle: {item['title']}\n"
            f"text:\n{item['text'].strip()}"
        )
    return "\n\n---\n\n".join(blocks)


def parse_citations(answer: str) -> list[str]:
    found = re.findall(r"\[C([1-5])\]", answer, flags=re.I)
    return [f"C{i}" for i in sorted(set(found), key=int)]


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string", "enum": ["C1", "C2", "C3", "C4", "C5"]}, "uniqueItems": True},
        "insufficient_evidence": {"type": "boolean"},
    },
    "required": ["answer", "citations", "insufficient_evidence"],
    "additionalProperties": False,
}


def main() -> None:
    queries = load_jsonl(RAG1 / "evaluation" / "eval_queries.jsonl")
    dense = load_jsonl(RAG1 / "evaluation" / "results_dense.jsonl")
    evidence_rows = load_jsonl(RAG1 / "evaluation" / "recommended_dense_evidence.jsonl")
    if not ([r["query_id"] for r in queries] == [r["query_id"] for r in dense] == [r["query_id"] for r in evidence_rows]):
        raise SystemExit("Frozen input question ordering mismatch")
    if len(queries) != 38:
        raise SystemExit("Expected 38 frozen questions")

    existing = load_jsonl(OUT) if OUT.is_file() else []
    completed = {r["question_id"] for r in existing if r.get("generation_status") == "COMPLETED"}
    cfg = CONFIG["generation"]
    load_started = time.perf_counter()
    llm = Llama(model_path=str(MODEL), n_ctx=cfg["context_length"], n_threads=cfg["threads"],
                n_threads_batch=cfg["batch_threads"], n_batch=cfg["prompt_batch_size"],
                n_ubatch=cfg["micro_batch_size"], seed=cfg["seed"], verbose=False)
    model_load_seconds = time.perf_counter() - load_started

    OUT.parent.mkdir(parents=True, exist_ok=True)
    run_started = time.perf_counter()
    generated_now = 0
    with OUT.open("a", encoding="utf-8") as stream:
        for query, retrieval, evidence_row in zip(queries, dense, evidence_rows):
            qid = query["query_id"]
            if qid in completed:
                continue
            context = format_context(evidence_row["evidence"])
            transport_warning = "\n本题属于交通/校车/路线/校园出入范围；没有直接证据时必须拒答。" if query["category"] == "交通服务" else ""
            user_prompt = f"资料如下：\n\n{context}\n\n问题：{query['query']}{transport_warning}\n\n只输出不超过120个汉字的回答正文。"
            started = time.perf_counter()
            response = llm.create_chat_completion(
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
                temperature=cfg["temperature"], max_tokens=cfg["max_new_tokens"], seed=cfg["seed"],
                repeat_penalty=1.05,
            )
            latency = time.perf_counter() - started
            raw_output = response["choices"][0]["message"]["content"].strip()
            answer = raw_output
            inline_citations = parse_citations(answer)
            citations = inline_citations
            insufficient = bool(re.search(r"无法确认|资料不足|未提供|无法根据|没有.{0,8}资料", answer))
            record = {
                "question_id": qid,
                "question": query["query"],
                "eval_status": "CONFIRMED" if query["eval_status"] == "EXISTING_SMOKE" else "PROVISIONAL_EVAL",
                "source_eval_status": query["eval_status"],
                "category": query["category"],
                "expected_source_id": query.get("expected_source_id"),
                "expected_source_status": query.get("expected_source_status"),
                "expected_evidence_keyword": query.get("expected_evidence_keyword"),
                "retriever": "BAAI/bge-small-zh-v1.5 frozen RAG V1 Dense Top-5",
                "retrieved_chunk_ids": [r["chunk_id"] for r in retrieval["top_5"]],
                "retrieved_document_ids": [r["source_id"] for r in retrieval["top_5"]],
                "retrieval_scores": [r["score"] for r in retrieval["top_5"]],
                "retrieved_context": [{"context_id": f"C{i}", **item} for i, item in enumerate(evidence_row["evidence"], 1)],
                "generation_prompt": {"system": SYSTEM_PROMPT, "user": user_prompt},
                "generated_answer": answer,
                "answer_citations": citations,
                "inline_answer_citations": inline_citations,
                "citation_inline_compliance": bool(citations) or insufficient,
                "model_insufficient_evidence": insufficient,
                "raw_model_output": raw_output,
                "latency": {
                    "generation_seconds": latency,
                    "prompt_tokens": response.get("usage", {}).get("prompt_tokens"),
                    "completion_tokens": response.get("usage", {}).get("completion_tokens"),
                    "total_tokens": response.get("usage", {}).get("total_tokens"),
                    "tokens_per_second": (response.get("usage", {}).get("completion_tokens") or 0) / latency,
                },
                "generation_model": CONFIG["generation"],
                "generation_status": "COMPLETED",
                "finish_reason": response["choices"][0].get("finish_reason"),
                "generated_utc": datetime.now(timezone.utc).isoformat(),
            }
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            generated_now += 1
            print(json.dumps({"question_id": qid, "status": "COMPLETED", "seconds": round(latency, 3),
                              "citations": citations, "answer_preview": answer[:100]}, ensure_ascii=False), flush=True)

    all_rows = load_jsonl(OUT)
    ids = [r["question_id"] for r in all_rows]
    if len(ids) != 38 or len(set(ids)) != 38:
        raise SystemExit(f"Generation output is not 38 unique questions: rows={len(ids)} unique={len(set(ids))}")
    payload = {
        "status": "PASS", "model_load_seconds": model_load_seconds,
        "run_seconds": time.perf_counter() - run_started, "generated_now": generated_now,
        "completed_total": len(all_rows), "model": CONFIG["generation"], "output": str(OUT),
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
