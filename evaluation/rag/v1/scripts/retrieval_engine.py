from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import torch
import yaml
from scipy import sparse
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer


V1 = Path(__file__).resolve().parents[1]
ROOT = V1.parent
CONFIG = yaml.safe_load((V1 / "config" / "retrieval.yaml").read_text(encoding="utf-8"))
CHUNKS = [json.loads(x) for x in (ROOT / "rag_v0" / "chunks" / "chunks.jsonl").read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def result_base(row: dict) -> dict:
    return {
        "chunk_id": row["chunk_id"], "source_id": row["source_id"], "category": row["category"],
        "title": row["title"], "url": row["url"], "original_file": row["original_file"],
        "chunk_index": row["chunk_index"], "text_preview": row["text"][:500],
    }


def top_indices(scores: np.ndarray, n: int) -> np.ndarray:
    n = min(n, scores.shape[0])
    part = np.argpartition(-scores, n - 1)[:n]
    return part[np.argsort(-scores[part], kind="stable")]


class TfidfRetriever:
    def __init__(self) -> None:
        base = V1 / "indexes" / "tfidf"
        self.vectorizer = joblib.load(base / "tfidf_vectorizer.joblib")
        self.matrix = sparse.load_npz(base / "tfidf_matrix.npz")

    def search(self, query: str, n: int = 10) -> list[dict]:
        q = self.vectorizer.transform([query])
        scores = (self.matrix @ q.T).toarray().ravel()
        out = []
        for rank, idx in enumerate(top_indices(scores, n), 1):
            item = result_base(CHUNKS[int(idx)])
            item.update({"rank": rank, "score": float(scores[idx]), "tfidf_score": float(scores[idx])})
            out.append(item)
        return out


class DenseRetriever:
    def __init__(self) -> None:
        cfg = CONFIG["dense"]
        model_path = V1 / cfg["local_model_path"]
        self.cfg = cfg
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self.model = AutoModel.from_pretrained(model_path, local_files_only=True).eval()
        self.embeddings = np.load(V1 / "indexes" / "dense" / "document_embeddings.npy", mmap_mode="r")

    def encode_query(self, query: str) -> np.ndarray:
        text = self.cfg["query_instruction"] + query
        tokens = self.tokenizer([text], padding=True, truncation=True, max_length=self.cfg["max_length"], return_tensors="pt")
        with torch.inference_mode():
            vector = self.model(**tokens).last_hidden_state[:, 0]
            vector = torch.nn.functional.normalize(vector, p=2, dim=1)
        return vector[0].cpu().numpy().astype(np.float32)

    def search(self, query: str, n: int = 10) -> list[dict]:
        q = self.encode_query(query)
        scores = np.asarray(self.embeddings @ q)
        out = []
        for rank, idx in enumerate(top_indices(scores, n), 1):
            item = result_base(CHUNKS[int(idx)])
            item.update({"rank": rank, "score": float(scores[idx]), "dense_score": float(scores[idx])})
            out.append(item)
        return out


class HybridRetriever:
    def __init__(self, sparse_retriever: TfidfRetriever, dense_retriever: DenseRetriever) -> None:
        self.sparse = sparse_retriever
        self.dense = dense_retriever
        self.cfg = CONFIG["hybrid"]

    def search(self, query: str, n: int = 10, candidate_n: int | None = None) -> list[dict]:
        candidate_n = candidate_n or max(self.cfg["sparse_top_n"], self.cfg["dense_top_n"])
        sparse_rows = self.sparse.search(query, max(candidate_n, self.cfg["sparse_top_n"]))
        dense_rows = self.dense.search(query, max(candidate_n, self.cfg["dense_top_n"]))
        fused: dict[str, dict] = {}
        k = self.cfg["rrf_k"]
        for method, rows in (("sparse", sparse_rows), ("dense", dense_rows)):
            for row in rows:
                cid = row["chunk_id"]
                item = fused.setdefault(cid, {**result_base(CHUNKS[next(i for i, c in enumerate(CHUNKS) if c["chunk_id"] == cid)]),
                                              "sparse_rank": None, "sparse_score": None,
                                              "dense_rank": None, "dense_score": None, "rrf_score": 0.0})
                item[f"{method}_rank"] = row["rank"]
                item[f"{method}_score"] = row["score"]
                item["rrf_score"] += 1.0 / (k + row["rank"])
        ordered = sorted(fused.values(), key=lambda x: (-x["rrf_score"], x["chunk_id"]))[:n]
        for rank, item in enumerate(ordered, 1):
            item["final_rank"] = rank
            item["rank"] = rank
            item["score"] = item["rrf_score"]
        return ordered


class Reranker:
    def __init__(self) -> None:
        cfg = CONFIG["reranker"]
        self.cfg = cfg
        model_path = V1 / cfg["local_model_path"]
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True).eval()

    def rerank(self, query: str, rows: list[dict], n: int = 10) -> list[dict]:
        scores: list[float] = []
        texts = [next(c["text"] for c in CHUNKS if c["chunk_id"] == r["chunk_id"]) for r in rows]
        with torch.inference_mode():
            for start in range(0, len(rows), self.cfg["batch_size"]):
                pairs_q = [query] * len(texts[start:start + self.cfg["batch_size"]])
                pairs_t = texts[start:start + self.cfg["batch_size"]]
                inputs = self.tokenizer(pairs_q, pairs_t, padding=True, truncation=True,
                                        max_length=self.cfg["max_length"], return_tensors="pt")
                logits = self.model(**inputs).logits.reshape(-1)
                scores.extend(float(x) for x in logits.cpu())
        output = []
        for row, score in zip(rows, scores):
            item = dict(row)
            item["hybrid_rank"] = row["rank"]
            item["reranker_score"] = score
            output.append(item)
        output.sort(key=lambda x: (-x["reranker_score"], x["hybrid_rank"]))
        output = output[:n]
        for rank, item in enumerate(output, 1):
            item["final_rank"] = rank
            item["rank"] = rank
            item["score"] = item["reranker_score"]
        return output

