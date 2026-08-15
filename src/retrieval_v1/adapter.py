from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUNDLE_ROOT = PROJECT_ROOT / "data" / "03_knowledge_base" / "v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class DenseRetrieverV1:
    """Dense Top-5 retriever that only reads a frozen KB/RAG V1 bundle.

    The adapter intentionally has no web-search, generation, Evidence Sufficiency,
    or citation dependencies.  It validates the freeze status and core artifact
    hashes before serving a request.
    """

    def __init__(self, bundle_root: Path | str = DEFAULT_BUNDLE_ROOT) -> None:
        self.root = Path(bundle_root).resolve()
        self.config = _read_json(self.root / "config" / "retriever_v1.json")
        self._verify_bundle()
        self.chunks = [
            json.loads(line)
            for line in (self.root / self.config["artifacts"]["chunks_path"]).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.embeddings = np.load(
            self.root / self.config["artifacts"]["embeddings_path"], mmap_mode="r", allow_pickle=False
        )
        if len(self.chunks) != len(self.embeddings):
            raise RuntimeError("frozen bundle has different chunk and embedding row counts")
        model_path = self.root / self.config["artifacts"]["model_path"]
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self.model = AutoModel.from_pretrained(model_path, local_files_only=True).eval()

    def _verify_bundle(self) -> None:
        kb_freeze = self.root / "audit" / "knowledge_base_v1_freeze.json"
        rag_freeze = self.root / "audit" / "rag_retrieval_v1_freeze.json"
        for path in (kb_freeze, rag_freeze):
            sidecar = path.with_suffix(path.suffix + ".sha256")
            if not path.is_file() or not sidecar.is_file():
                raise RuntimeError(f"missing frozen bundle manifest: {path}")
            if _sha256(path) != sidecar.read_text(encoding="ascii").strip():
                raise RuntimeError(f"freeze manifest hash mismatch: {path.name}")
        kb = _read_json(kb_freeze)
        rag = _read_json(rag_freeze)
        if kb.get("status") != "KNOWLEDGE_BASE_V1_FROZEN" or rag.get("status") != "RAG_RETRIEVAL_V1_FROZEN":
            raise RuntimeError("bundle is not frozen; refusing runtime retrieval")
        if _sha256(self.root / "config" / "retriever_v1.json") != rag.get("retriever_config_sha256"):
            raise RuntimeError("retriever config differs from the frozen retrieval bundle")
        for key, relative in self.config["artifacts"].items():
            if key.endswith("_path"):
                candidate = self.root / relative
                if not candidate.exists():
                    raise RuntimeError(f"missing configured artifact: {relative}")
        expected = self.config["artifact_sha256"]
        for relative, digest in expected.items():
            if _sha256(self.root / relative) != digest:
                raise RuntimeError(f"artifact hash mismatch: {relative}")

    def _encode_query(self, query: str) -> np.ndarray:
        text = self.config["query_instruction"] + query
        tokens = self.tokenizer(
            [text],
            padding=True,
            truncation=True,
            max_length=int(self.config["max_length"]),
            return_tensors="pt",
        )
        with torch.inference_mode():
            vector = self.model(**tokens).last_hidden_state[:, 0]
            vector = torch.nn.functional.normalize(vector, p=2, dim=1)
        return vector[0].cpu().numpy().astype(np.float32)

    def retrieve(self, query: str, case_id: str) -> dict[str, Any]:
        started = time.perf_counter()
        base: dict[str, Any] = {
            "query": query,
            "case_id": case_id,
            "retriever_version": self.config["retriever_version"],
            "corpus_version": self.config["corpus_version"],
            "ordered_top5_chunks": [],
            "source_ids": [],
            "chunk_ids": [],
            "scores": [],
            "latency_ms": None,
            "error": None,
        }
        if not isinstance(query, str) or not query.strip() or not isinstance(case_id, str) or not case_id.strip():
            base["error"] = "query and case_id must be non-empty strings"
            base["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
            return base
        try:
            scores = np.asarray(self.embeddings @ self._encode_query(query))
            ordered = sorted(range(len(self.chunks)), key=lambda idx: (-float(scores[idx]), self.chunks[idx]["chunk_id"]))[:5]
            rows = []
            for rank, idx in enumerate(ordered, 1):
                chunk = self.chunks[idx]
                rows.append(
                    {
                        "rank": rank,
                        "source_id": chunk["canonical_source_id"],
                        "chunk_id": chunk["chunk_id"],
                        "score": float(scores[idx]),
                        "title": chunk["title"],
                        "url": chunk["url"],
                        "category": chunk["category"],
                        "text": chunk["text"],
                    }
                )
            base["ordered_top5_chunks"] = rows
            base["source_ids"] = [row["source_id"] for row in rows]
            base["chunk_ids"] = [row["chunk_id"] for row in rows]
            base["scores"] = [row["score"] for row in rows]
        except Exception as exc:  # Runtime consumers receive a schema-valid failure.
            base["error"] = f"{type(exc).__name__}: {exc}"
        base["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return base
