"""Experimental Dense V1 + independently-built BM25 + deterministic RRF.

This module only reads the frozen V1 bundle.  It is intentionally not imported
by production or E2E code.  The generated BM25 index lives beside this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieval_v1 import DenseRetrieverV1

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
INDEX_PATH = HERE / "artifacts" / "bm25_index.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\u3400-\u9fff]|[A-Za-z0-9_]+", text.lower())


class BM25Index:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.doc_lengths = payload["doc_lengths"]
        self.avg_doc_length = payload["avg_doc_length"]
        self.postings = payload["postings"]
        self.document_count = payload["document_count"]
        self.k1 = payload["k1"]
        self.b = payload["b"]

    @classmethod
    def build(cls, chunks: list[dict[str, Any]], config: dict[str, Any]) -> "BM25Index":
        postings: dict[str, list[list[int]]] = defaultdict(list)
        lengths: list[int] = []
        for index, chunk in enumerate(chunks):
            terms = tokenize(f"{chunk['title']}\n{chunk['text']}")
            lengths.append(len(terms))
            for term, count in sorted(Counter(terms).items()):
                postings[term].append([index, count])
        return cls({
            "format": "BM25_V2_INDEPENDENT_INDEX_V1", "document_count": len(chunks),
            "doc_lengths": lengths, "avg_doc_length": sum(lengths) / len(lengths) if lengths else 0.0,
            "postings": dict(sorted(postings.items())), "k1": config["k1"], "b": config["b"],
        })

    def search(self, query: str, limit: int, chunks: list[dict[str, Any]]) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term, query_tf in Counter(tokenize(query)).items():
            posting = self.postings.get(term, [])
            if not posting:
                continue
            idf = math.log(1.0 + (self.document_count - len(posting) + 0.5) / (len(posting) + 0.5))
            for index, doc_tf in posting:
                norm = self.k1 * (1.0 - self.b + self.b * self.doc_lengths[index] / self.avg_doc_length)
                scores[index] += query_tf * idf * doc_tf * (self.k1 + 1.0) / (doc_tf + norm)
        ordered = sorted(scores.items(), key=lambda item: (-item[1], chunks[item[0]]["chunk_id"]))
        return ordered[:limit]


class HybridRetrieverV2:
    def __init__(self, index_path: Path = INDEX_PATH) -> None:
        self.dense_v1 = DenseRetrieverV1()
        self.chunks = self.dense_v1.chunks
        self.index_path = index_path
        if not self.index_path.is_file():
            raise RuntimeError(f"BM25 index missing; run build-index first: {self.index_path}")
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        if payload.get("source_chunks_sha256") != sha256(self.dense_v1.root / self.dense_v1.config["artifacts"]["chunks_path"]):
            raise RuntimeError("BM25 index chunk hash does not match frozen bundle")
        self.bm25 = BM25Index(payload)

    def retrieve(self, query: str, case_id: str, top_k: int = 5) -> dict[str, Any]:
        if top_k not in CONFIG["candidate_top_k_allowed"]:
            raise ValueError(f"top_k must be one of {CONFIG['candidate_top_k_allowed']}")
        if not query.strip() or not case_id.strip():
            raise ValueError("query and case_id must be non-empty")
        return self._retrieve_from_query_vector(query, case_id, top_k, self.dense_v1._encode_query(query))

    def _retrieve_from_query_vector(self, query: str, case_id: str, top_k: int, query_vector: np.ndarray) -> dict[str, Any]:
        """Internal benchmark hook; preserves the public retrieve computation."""
        pool = CONFIG["candidate_pool_per_retriever"]
        dense_scores = np.asarray(self.dense_v1.embeddings @ query_vector)
        dense = sorted(range(len(self.chunks)), key=lambda i: (-float(dense_scores[i]), self.chunks[i]["chunk_id"]))[:pool]
        sparse = self.bm25.search(query, pool, self.chunks)
        fused: dict[int, dict[str, Any]] = {}
        for method, results in (("dense", [(i, float(dense_scores[i])) for i in dense]), ("bm25", sparse)):
            for rank, (index, score) in enumerate(results, 1):
                item = fused.setdefault(index, {"dense_rank": None, "dense_score": None, "bm25_rank": None, "bm25_score": None, "rrf_score": 0.0})
                item[f"{method}_rank"] = rank
                item[f"{method}_score"] = score
                item["rrf_score"] += 1.0 / (CONFIG["rrf"]["k"] + rank)
        rows = []
        for index, item in sorted(fused.items(), key=lambda x: (-x[1]["rrf_score"], self.chunks[x[0]]["chunk_id"]))[:top_k]:
            chunk = self.chunks[index]
            rows.append({"chunk_id": chunk["chunk_id"], "source_id": chunk["canonical_source_id"], "title": chunk["title"], "url": chunk["url"], **item})
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
        return {"case_id": case_id, "query": query, "retriever_version": CONFIG["prototype"], "candidate_top_k": top_k, "results": rows}


def build_index() -> None:
    dense = DenseRetrieverV1()
    index = BM25Index.build(dense.chunks, CONFIG["bm25"])
    payload = {**index.payload, "source_chunks_sha256": sha256(dense.root / dense.config["artifacts"]["chunks_path"])}
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if INDEX_PATH.exists():
        raise SystemExit(f"refusing to overwrite index: {INDEX_PATH}")
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"status": "BUILT", "documents": len(dense.chunks), "index": str(INDEX_PATH)}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("build-index")
    query_parser = command.add_parser("query")
    query_parser.add_argument("--query", required=True)
    query_parser.add_argument("--case-id", default="SYNTHETIC-001")
    query_parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.command == "build-index":
        build_index()
    else:
        print(json.dumps(HybridRetrieverV2().retrieve(args.query, args.case_id, args.top_k), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
