from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import threading
import time
from pathlib import Path

import joblib
import numpy as np
import psutil
import torch
import yaml
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import AutoModel, AutoTokenizer


V1 = Path(__file__).resolve().parents[1]
ROOT = V1.parent
CONFIG = yaml.safe_load((V1 / "config" / "retrieval.yaml").read_text(encoding="utf-8"))
AUDIT = V1 / "audit" / "chunk_integrity_report.json"
CHUNKS_PATH = ROOT / "rag_v0" / "chunks" / "chunks.jsonl"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class MemorySampler:
    def __init__(self) -> None:
        self.process = psutil.Process(os.getpid())
        self.baseline = self.process.memory_info().rss
        self.peak = self.baseline
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self.stop_event.wait(0.05):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.peak = max(self.peak, self.process.memory_info().rss)
        self.stop_event.set()
        self.thread.join()

    @property
    def peak_mb(self) -> float:
        return self.peak / 1024**2

    @property
    def delta_mb(self) -> float:
        return (self.peak - self.baseline) / 1024**2


def load_chunks() -> list[dict]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS":
        raise SystemExit("Frozen chunk audit is not PASS; refusing to build indexes.")
    rows = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(rows) != CONFIG["corpus"]["expected_chunks"]:
        raise SystemExit("Chunk count changed after audit; refusing to build indexes.")
    return rows


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def build_tfidf(chunks: list[dict]) -> dict:
    out = V1 / "indexes" / "tfidf"
    out.mkdir(parents=True, exist_ok=True)
    cfg = CONFIG["tfidf"]
    vectorizer = TfidfVectorizer(
        analyzer=cfg["analyzer"], ngram_range=tuple(cfg["ngram_range"]),
        max_features=cfg["max_features"], sublinear_tf=cfg["sublinear_tf"], norm=cfg["norm"]
    )
    documents = [f'{r["title"]}\n{r["text"]}' for r in chunks]
    started = time.perf_counter()
    with MemorySampler() as mem:
        matrix = vectorizer.fit_transform(documents).astype(np.float32)
    elapsed = time.perf_counter() - started
    matrix_path = out / "tfidf_matrix.npz"
    vectorizer_path = out / "tfidf_vectorizer.joblib"
    sparse.save_npz(matrix_path, matrix)
    joblib.dump(vectorizer, vectorizer_path)
    atomic_json(out / "chunk_ids.json", [r["chunk_id"] for r in chunks])
    report = {
        "status": "PASS", "method": "TF-IDF exact cosine on L2-normalized vectors",
        "input": "title + newline + text", "shape": list(matrix.shape), "nonzero": int(matrix.nnz),
        "build_seconds": elapsed, "peak_rss_mb": mem.peak_mb, "incremental_peak_mb": mem.delta_mb,
        "matrix_sha256": sha256(matrix_path), "vectorizer_sha256": sha256(vectorizer_path),
        "source_chunks_sha256": sha256(CHUNKS_PATH), "config": cfg,
    }
    atomic_json(out / "index_report.json", report)
    return report


def mean_pool_cls(model_output: torch.Tensor) -> torch.Tensor:
    return model_output.last_hidden_state[:, 0]


def encode(model, tokenizer, texts: list[str], batch_size: int, max_length: int) -> np.ndarray:
    batches = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            tokens = tokenizer(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
            vectors = mean_pool_cls(model(**tokens))
            vectors = torch.nn.functional.normalize(vectors, p=2, dim=1)
            batches.append(vectors.cpu().numpy().astype(np.float32))
    return np.concatenate(batches, axis=0)


def build_dense(chunks: list[dict]) -> dict:
    out = V1 / "indexes" / "dense"
    out.mkdir(parents=True, exist_ok=True)
    cfg = CONFIG["dense"]
    model_path = V1 / cfg["local_model_path"]
    weights = model_path / "model.safetensors"
    if not weights.is_file():
        raise SystemExit(f"Dense weights missing: {weights}")
    started_load = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModel.from_pretrained(model_path, local_files_only=True)
    load_seconds = time.perf_counter() - started_load
    texts = [f'{r["title"]}\n{r["text"]}' for r in chunks]
    started = time.perf_counter()
    with MemorySampler() as mem:
        embeddings = encode(model, tokenizer, texts, cfg["batch_size"], cfg["max_length"])
    elapsed = time.perf_counter() - started
    emb_path = out / "document_embeddings.npy"
    np.save(emb_path, embeddings, allow_pickle=False)
    mapping_path = out / "row_mapping.jsonl"
    mapping_path.write_text("".join(json.dumps({
        "embedding_row": i, "chunk_id": r["chunk_id"], "source_id": r["source_id"],
        "title": r["title"], "url": r["url"], "category": r["category"],
        "original_file": r["original_file"], "chunk_index": r["chunk_index"],
    }, ensure_ascii=False) + "\n" for i, r in enumerate(chunks)), encoding="utf-8")
    norms = np.linalg.norm(embeddings, axis=1)
    report = {
        "status": "PASS", "model_name": cfg["model_name"], "revision": cfg["revision"],
        "local_model_path": str(model_path), "weights_sha256": sha256(weights),
        "embedding_dimension": int(embeddings.shape[1]), "rows": int(embeddings.shape[0]),
        "encoding_batch_size": cfg["batch_size"], "max_length": cfg["max_length"],
        "document_encoding_seconds": elapsed, "documents_per_second": len(chunks) / elapsed,
        "model_load_seconds": load_seconds, "peak_rss_mb": mem.peak_mb, "incremental_peak_mb": mem.delta_mb,
        "embedding_file_sha256": sha256(emb_path), "mapping_file_sha256": sha256(mapping_path),
        "embedding_file_bytes": emb_path.stat().st_size,
        "normalization": "L2", "cosine_ready": bool(np.allclose(norms, 1.0, atol=1e-4)),
        "norm_min": float(norms.min()), "norm_max": float(norms.max()),
        "pooling": "CLS last_hidden_state[:,0]", "input": "title + newline + text",
        "query_instruction": cfg["query_instruction"],
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "device": "cpu"},
    }
    atomic_json(out / "index_report.json", report)
    (V1 / "reports").mkdir(parents=True, exist_ok=True)
    (V1 / "reports" / "dense_index_report.md").write_text(f"""# Dense Index Report

- Status: **PASS**
- Model: `{cfg['model_name']}`
- Revision: `{cfg['revision']}`
- Local weights SHA-256: `{report['weights_sha256']}`
- Embedding rows × dimension: `{report['rows']} × {report['embedding_dimension']}`
- Batch size / max length: `{cfg['batch_size']} / {cfg['max_length']}`
- Document encoding time: `{elapsed:.3f} s` ({report['documents_per_second']:.2f} chunks/s)
- Model load time: `{load_seconds:.3f} s`
- Peak process RSS: `{mem.peak_mb:.2f} MiB` (incremental `{mem.delta_mb:.2f} MiB`)
- Normalization: L2; cosine-ready validation: `{report['cosine_ready']}`
- Embedding file SHA-256: `{report['embedding_file_sha256']}`
- Row traceability: `row_mapping.jsonl` maps every embedding row to chunk, source, URL, original file, and chunk index.
- Encoding: documents use `title + newline + text`; queries use the configured BGE Chinese retrieval instruction.
""", encoding="utf-8")
    del model
    return report


def main() -> None:
    chunks = load_chunks()
    tfidf = build_tfidf(chunks)
    dense = build_dense(chunks)
    print(json.dumps({"status": "PASS", "chunks": len(chunks), "tfidf_shape": tfidf["shape"],
                      "dense_shape": [dense["rows"], dense["embedding_dimension"]],
                      "dense_sha256": dense["embedding_file_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
