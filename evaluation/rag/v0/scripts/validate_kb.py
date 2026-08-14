from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import sparse


RAG_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = RAG_DIR.parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate() -> dict:
    manifest = load_jsonl(RAG_DIR / "knowledge_base_manifest" / "knowledge_base_manifest.jsonl")
    chunks = load_jsonl(RAG_DIR / "chunks" / "chunks.jsonl")
    metadata = json.loads((RAG_DIR / "vector_index" / "index_metadata.json").read_text(encoding="utf-8"))
    chunk_ids = json.loads((RAG_DIR / "vector_index" / "chunk_ids.json").read_text(encoding="utf-8"))
    matrix = sparse.load_npz(RAG_DIR / "vector_index" / "embeddings.npz")
    accepted = [row for row in manifest if row["validation_status"] == "accepted"]
    checks = {
        "all_manifest_rows_accepted": len(accepted) == len(manifest),
        "all_source_files_still_exist": all((DATA_ROOT / row["original_file"]).is_file() for row in accepted),
        "all_normalized_files_exist": all((RAG_DIR / row["normalized_text_path"]).is_file() for row in accepted),
        "all_chunks_have_required_fields": all(
            all(field in row and row[field] not in (None, "") for field in [
                "chunk_id", "source_id", "title", "url", "category", "source_type",
                "original_file", "text", "chunk_index"
            ]) for row in chunks
        ),
        "all_chunk_urls_preserved": all(str(row["url"]).startswith(("http://", "https://")) for row in chunks),
        "chunk_id_order_matches_index": chunk_ids == [row["chunk_id"] for row in chunks],
        "vector_rows_match_chunks": matrix.shape[0] == len(chunks),
        "vector_columns_match_metadata": matrix.shape[1] == metadata["dimension"],
        "chunks_hash_matches_metadata": digest(RAG_DIR / "chunks" / "chunks.jsonl") == metadata["chunks_sha256"],
        "embeddings_hash_matches_metadata": digest(RAG_DIR / "vector_index" / "embeddings.npz") == metadata["embeddings_sha256"],
        "vectorizer_hash_matches_metadata": digest(RAG_DIR / "vector_index" / "tfidf_vectorizer.joblib") == metadata["vectorizer_sha256"],
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source_rows": len(manifest),
        "accepted_sources": len(accepted),
        "chunk_rows": len(chunks),
        "vector_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "checks": checks,
    }
    out = RAG_DIR / "knowledge_base_manifest" / "post_build_validation.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
