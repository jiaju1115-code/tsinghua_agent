from __future__ import annotations

import math
import re
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .metadata import DEFAULT_CATALOG, SHADOW_ROOT, V1_ROOT, jsonl, load_catalog, load_v1_catalog, temporal_status
from .query_planner import QueryPlan


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for segment in re.findall(r"[\u3400-\u9fff]+|[a-z0-9_]+", text.lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", segment):
            tokens.extend(segment)
            tokens.extend(segment[index:index + 2] for index in range(len(segment) - 1))
            tokens.extend(segment[index:index + 3] for index in range(len(segment) - 2))
        else:
            tokens.append(segment)
    return tokens


class BM25Index:
    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.lengths: list[int] = []
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for index, chunk in enumerate(chunks):
            terms = tokenize(f"{chunk.get('title', '')}\n{chunk.get('text', '')}")
            self.lengths.append(len(terms))
            for term, count in Counter(terms).items():
                self.postings[term].append((index, count))
        self.count = len(chunks)
        self.average_length = sum(self.lengths) / self.count if self.count else 0.0

    def search(self, query: str, limit: int) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term, query_tf in Counter(tokenize(query)).items():
            posting = self.postings.get(term, [])
            if not posting:
                continue
            idf = math.log(1.0 + (self.count - len(posting) + 0.5) / (len(posting) + 0.5))
            for index, doc_tf in posting:
                norm = self.k1 * (1.0 - self.b + self.b * self.lengths[index] / self.average_length)
                scores[index] += query_tf * idf * doc_tf * (self.k1 + 1.0) / (doc_tf + norm)
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]


class TrustedHybridRetrieverV2:
    """Fast lexical path plus lazy Dense/BM25 fusion and metadata-aware reranking."""

    def __init__(
        self,
        bundle_root: Path | str = V1_ROOT,
        catalog_path: Path | str = DEFAULT_CATALOG,
        dense_factory: Callable[[], Any] | None = None,
        chunks: list[dict[str, Any]] | None = None,
        metadata: dict[str, dict[str, Any]] | None = None,
        allowed_access_levels: tuple[str, ...] = ("public",),
    ) -> None:
        self.bundle_root = Path(bundle_root)
        self.chunks = chunks if chunks is not None else jsonl(self.bundle_root / "chunks" / "chunks.jsonl")
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = load_catalog(catalog_path)
            if not self.metadata and self.bundle_root.resolve() == V1_ROOT.resolve():
                self.metadata = load_v1_catalog()
        self.allowed_access_levels = set(allowed_access_levels)
        self.bm25 = BM25Index(self.chunks)
        self._dense_factory = dense_factory
        self._dense: Any | None = None

    def _get_dense(self) -> Any:
        if self._dense is None:
            if self._dense_factory is not None:
                self._dense = self._dense_factory()
            else:
                if self.bundle_root.resolve() != V1_ROOT.resolve():
                    embeddings_path = self.bundle_root / "index" / "document_embeddings.npy"
                    if not embeddings_path.is_file():
                        raise RuntimeError("shadow dense index has not been built")
                    from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1
                    base = build_dense_retriever_v1()
                    base.embeddings = np.load(embeddings_path, mmap_mode="r", allow_pickle=False)
                    if len(base.embeddings) != len(self.chunks):
                        raise RuntimeError("shadow chunk and embedding row counts differ")
                    self._dense = base
                else:
                    from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1
                    self._dense = build_dense_retriever_v1()
            from .hardware import place_dense_encoder
            place_dense_encoder(self._dense)
        return self._dense

    @staticmethod
    def _authority_score(level: str) -> float:
        return {"official_internal": 1.0, "official": 1.0, "authoritative_external": 0.72, "unverified": 0.2}.get(level, 0.35)

    def _metadata_match(self, meta: dict[str, Any], plan: QueryPlan, as_of: date) -> tuple[bool, float, str]:
        status = temporal_status(meta, as_of)
        if plan.metadata_filters.get("current_only") and status in {"expired", "upcoming"}:
            return False, 0.0, status
        topics = set(plan.metadata_filters.get("topics", []))
        source_topics = set(meta.get("topics") or [meta.get("topic")])
        topic_score = 1.0 if not topics or topics & source_topics else 0.15
        wanted_audience = set(plan.metadata_filters.get("audience", []))
        source_audience = set(meta.get("audience", []))
        audience_score = 1.0 if not wanted_audience or wanted_audience & source_audience or "全校学生" in source_audience else 0.3
        return True, (topic_score + audience_score) / 2.0, status

    @staticmethod
    def _encode_subqueries(dense: Any, subqueries: tuple[str, ...]) -> list[np.ndarray]:
        if not all(hasattr(dense, name) for name in ("tokenizer", "model", "config")):
            return [dense._encode_query(query) for query in subqueries]
        import torch

        texts = [dense.config["query_instruction"] + query for query in subqueries]
        tokens = dense.tokenizer(
            texts, padding=True, truncation=True,
            max_length=int(dense.config["max_length"]), return_tensors="pt",
        )
        from .hardware import move_batch_to_dense_device
        tokens = move_batch_to_dense_device(dense, tokens)
        with torch.inference_mode():
            vectors = dense.model(**tokens).last_hidden_state[:, 0]
            vectors = torch.nn.functional.normalize(vectors, p=2, dim=1)
        return [row.cpu().numpy().astype(np.float32) for row in vectors]

    def retrieve(self, plan: QueryPlan, top_k: int = 8, as_of: date | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        as_of = as_of or date.today()
        pool_size = max(30, top_k * 5)
        fused: dict[int, dict[str, Any]] = {}
        dense_error = None
        try:
            dense = self._get_dense() if plan.path == "FULL" else None
        except Exception as exc:
            dense = None
            dense_error = f"{type(exc).__name__}: {exc}"[:240]
        method_count = 1 + int(dense is not None)
        dense_vectors = self._encode_subqueries(dense, plan.subqueries) if dense is not None else None

        for subquery_index, subquery in enumerate(plan.subqueries):
            sparse = self.bm25.search(subquery, pool_size)
            for rank, (index, raw_score) in enumerate(sparse, 1):
                item = fused.setdefault(index, {"rrf": 0.0, "bm25_score": None, "dense_score": None, "subquery_indices": set(), "retrieval_methods": set()})
                item["rrf"] += 1.0 / (60 + rank)
                item["bm25_score"] = max(float(raw_score), item["bm25_score"] or float("-inf"))
                item["subquery_indices"].add(subquery_index)
                item["retrieval_methods"].add("bm25")
            if dense is not None:
                vector = dense_vectors[subquery_index]
                dense_scores = np.asarray(dense.embeddings @ vector)
                indices = sorted(range(len(self.chunks)), key=lambda i: (-float(dense_scores[i]), self.chunks[i]["chunk_id"]))[:pool_size]
                for rank, index in enumerate(indices, 1):
                    item = fused.setdefault(index, {"rrf": 0.0, "bm25_score": None, "dense_score": None, "subquery_indices": set(), "retrieval_methods": set()})
                    item["rrf"] += 1.0 / (60 + rank)
                    item["dense_score"] = max(float(dense_scores[index]), item["dense_score"] or float("-inf"))
                    item["subquery_indices"].add(subquery_index)
                    item["retrieval_methods"].add("dense")

        max_rrf = max((item["rrf"] for item in fused.values()), default=1.0)
        query_terms = set(tokenize(f"{plan.original_query} {' '.join(plan.canonical_terms)}"))
        rows = []
        for index, item in fused.items():
            chunk = self.chunks[index]
            source_id = chunk["canonical_source_id"]
            meta = self.metadata.get(source_id, {})
            if meta.get("admission_status", "serving") != "serving":
                continue
            if meta.get("access_level", "public") not in self.allowed_access_levels:
                continue
            allowed, metadata_score, current_status = self._metadata_match(meta, plan, as_of)
            if not allowed:
                continue
            title_terms = set(tokenize(chunk.get("title", "")))
            body_terms = set(tokenize(chunk.get("text", "")))
            title_lexical = len(query_terms & title_terms) / max(1, len(query_terms))
            body_lexical = len(query_terms & body_terms) / max(1, len(query_terms))
            authority = self._authority_score(meta.get("authority_level", "unverified"))
            recency = {"active": 1.0, "unknown": 0.62, "upcoming": 0.45, "expired": 0.1}[current_status]
            retrieval_score = item["rrf"] / max_rrf
            score = 0.42 * retrieval_score + 0.24 * title_lexical + 0.10 * body_lexical + 0.10 * authority + 0.07 * recency + 0.07 * metadata_score
            from .security import sanitize_untrusted_text
            safe_text, injection_warnings = sanitize_untrusted_text(chunk.get("text", ""))
            rows.append({
                "chunk_id": chunk["chunk_id"], "source_id": source_id,
                "title": chunk.get("title", ""), "url": chunk.get("url", ""),
                "category": chunk.get("category", ""), "text": safe_text,
                "score": round(score, 6), "rrf_score": round(item["rrf"], 8),
                "dense_score": item["dense_score"], "bm25_score": item["bm25_score"],
                "retrieval_methods": sorted(item["retrieval_methods"]),
                "subquery_indices": sorted(item["subquery_indices"]),
                "metadata": meta, "temporal_status": current_status,
                "security_warnings": injection_warnings,
            })
        ordered = sorted(rows, key=lambda row: (-row["score"], row["chunk_id"]))
        selected: list[dict[str, Any]] = []
        source_counts: Counter[str] = Counter()
        for row in ordered:
            if source_counts[row["source_id"]] >= 2:
                continue
            source_counts[row["source_id"]] += 1
            selected.append(row)
            if len(selected) == top_k:
                break
        for rank, row in enumerate(selected, 1):
            row["rank"] = rank
        return {
            "retriever_version": "TRUSTED_HYBRID_RETRIEVER_V2_CANDIDATE",
            "corpus_version": "KB_V1_READ_ONLY_PLUS_REVIEWED_V2_EXPANSION",
            "path": plan.path, "dense_enabled": dense is not None,
            "method_count": method_count, "degraded": dense_error is not None,
            "degradation_reason": dense_error, "results": selected,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def build_shadow_retriever_v2() -> TrustedHybridRetrieverV2:
    """Explicit opt-in loader for the local, unpublished V2 shadow bundle."""
    return TrustedHybridRetrieverV2(bundle_root=SHADOW_ROOT, catalog_path=SHADOW_ROOT / "metadata_catalog.jsonl")


def build_public_retriever_v2() -> TrustedHybridRetrieverV2:
    """Load the independently built, public-only serving bundle when available."""
    root = Path(__file__).resolve().parents[2] / "data" / "05_trusted_campus_kb_v2_public"
    if not (root / "chunks" / "chunks.jsonl").is_file():
        return TrustedHybridRetrieverV2()
    return TrustedHybridRetrieverV2(bundle_root=root, catalog_path=root / "metadata_catalog.jsonl")
