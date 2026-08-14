from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import joblib
from scipy import sparse


RAG_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = RAG_DIR / "config" / "rag_v0.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class Retriever:
    def __init__(self, config_path: Path = DEFAULT_CONFIG):
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.chunks = load_jsonl(RAG_DIR / "chunks" / "chunks.jsonl")
        self.matrix = sparse.load_npz(RAG_DIR / "vector_index" / "embeddings.npz").tocsr()
        self.vectorizer = joblib.load(RAG_DIR / "vector_index" / "tfidf_vectorizer.joblib")
        chunk_ids = json.loads((RAG_DIR / "vector_index" / "chunk_ids.json").read_text(encoding="utf-8"))
        if chunk_ids != [row["chunk_id"] for row in self.chunks]:
            raise RuntimeError("Vector rows and chunk metadata are not aligned")
    def embed_query(self, query: str):
        return self.vectorizer.transform([query]).tocsr()

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        k = int(top_k or self.config["retrieval"]["top_k"])
        query_vector = self.embed_query(query)
        scores = (self.matrix @ query_vector.T).toarray().ravel()
        indices = np.argsort(-scores, kind="stable")[:k]
        results: list[dict[str, Any]] = []
        for rank, index in enumerate(indices, start=1):
            row = self.chunks[int(index)]
            results.append(
                {
                    "rank": rank,
                    "chunk_id": row["chunk_id"],
                    "source_id": row["source_id"],
                    "title": row["title"],
                    "url": row["url"],
                    "category": row["category"],
                    "source_type": row["source_type"],
                    "original_file": row["original_file"],
                    "chunk_index": row["chunk_index"],
                    "similarity_score": round(float(scores[int(index)]), 8),
                    "text": row["text"],
                }
            )
        return results


def assemble_evidence(query: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    blocks: list[str] = []
    sources: list[dict[str, Any]] = []
    for row in results:
        blocks.append(
            f"[{row['rank']}] {row['title']} (source_id={row['source_id']}, chunk_id={row['chunk_id']})\n"
            f"URL: {row['url']}\n{row['text']}"
        )
        sources.append({k: row[k] for k in ["rank", "source_id", "chunk_id", "title", "url", "category", "similarity_score"]})
    return {"query": query, "evidence": "\n\n---\n\n".join(blocks), "sources": sources}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve evidence from PROVISIONAL_KB_V0 without a generator model.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    retriever = Retriever(args.config.resolve())
    print(json.dumps(assemble_evidence(args.query, retriever.search(args.query, args.top_k)), ensure_ascii=False, indent=2))
