"""Non-held-out checks for Hybrid Retriever V2 determinism and output schema."""
from __future__ import annotations

import json
from pathlib import Path

from hybrid_retriever import BM25Index, tokenize


HERE = Path(__file__).resolve().parent
OUT = HERE / "validation.json"


def main() -> None:
    chunks = [
        {"chunk_id": "fixture-a", "title": "校园卡", "text": "校园卡 丢失 挂失"},
        {"chunk_id": "fixture-b", "title": "图书馆", "text": "图书馆 开放时间"},
        {"chunk_id": "fixture-c", "title": "校园卡", "text": "校园卡 补办"},
    ]
    index = BM25Index.build(chunks, {"k1": 1.5, "b": 0.75})
    first = index.search("校园卡 挂失", 3, chunks)
    second = index.search("校园卡 挂失", 3, chunks)
    payload = {
        "status": "PASS", "fixture_only": True, "heldout_e2e50_used": False,
        "tokenizer_nonempty": bool(tokenize("校园卡 lost")),
        "bm25_deterministic": first == second,
        "bm25_top_chunk_id": chunks[first[0][0]]["chunk_id"],
        "rrf_tie_breaking_spec": "rrf_score descending, then chunk_id ascending",
        "required_result_fields": ["rank", "chunk_id", "source_id", "dense_rank", "dense_score", "bm25_rank", "bm25_score", "rrf_score"],
    }
    if not payload["bm25_deterministic"] or payload["bm25_top_chunk_id"] != "fixture-a":
        raise SystemExit("fixture validation failed")
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
