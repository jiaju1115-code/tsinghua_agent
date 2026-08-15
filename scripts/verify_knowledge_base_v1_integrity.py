"""Verify the frozen KB/RAG V1 bundle and historical-input invariance without rebuilding it."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_knowledge_base_v1 import canonical_json, historical_snapshot, sha256_bytes, sha256_file  # noqa: E402


KB = ROOT / "data" / "03_knowledge_base" / "v1"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    failures: list[str] = []
    kb_freeze = KB / "audit" / "knowledge_base_v1_freeze.json"
    rag_freeze = KB / "audit" / "rag_retrieval_v1_freeze.json"
    for manifest in (kb_freeze, rag_freeze):
        sidecar = manifest.with_suffix(manifest.suffix + ".sha256")
        if not sidecar.is_file() or sha256_file(manifest) != sidecar.read_text(encoding="ascii").strip():
            failures.append(f"freeze_sidecar_mismatch:{manifest.name}")
    freeze = read_json(kb_freeze)
    rag = read_json(rag_freeze)
    config = read_json(KB / "config" / "retriever_v1.json")
    source_rows = read_jsonl(KB / "manifests" / "source_manifest.jsonl")
    chunks = read_jsonl(KB / "chunks" / "chunks.jsonl")
    mapping = read_jsonl(KB / "index" / "row_mapping.jsonl")
    if len(source_rows) != freeze["source_count"]:
        failures.append("source_count_mismatch")
    if len(chunks) != freeze["chunks_count"] or len(mapping) != len(chunks):
        failures.append("chunk_or_mapping_count_mismatch")
    if sha256_file(KB / "manifests" / "source_manifest.jsonl") != freeze["source_manifest_sha256"]:
        failures.append("source_manifest_hash_mismatch")
    if sha256_file(KB / "chunks" / "chunks.jsonl") != freeze["chunks_sha256"]:
        failures.append("chunks_hash_mismatch")
    if sha256_file(KB / "config" / "retriever_v1.json") != freeze["retriever_config_sha256"] or sha256_file(KB / "config" / "retriever_v1.json") != rag["retriever_config_sha256"]:
        failures.append("retriever_config_hash_mismatch")
    for source in source_rows:
        canonical = ROOT / source["canonical_file_path"]
        original = ROOT / source["original_file_path"]
        if not canonical.is_file() or not original.is_file():
            failures.append(f"missing_source_file:{source['canonical_source_id']}")
            continue
        if sha256_file(canonical) != source["source_sha256"] or sha256_file(original) != source["original_file_sha256"]:
            failures.append(f"source_hash_mismatch:{source['canonical_source_id']}")
        if source["review_status"] != "approve" or source["time_status"] != "evergreen":
            failures.append(f"noneligible_source_in_runtime:{source['canonical_source_id']}")
    chunk_ids = [row["chunk_id"] for row in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        failures.append("duplicate_chunk_ids")
    if any(hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != row["chunk_sha256"] for row in chunks):
        failures.append("chunk_text_hash_mismatch")
    if [row["chunk_id"] for row in mapping] != chunk_ids:
        failures.append("row_mapping_order_mismatch")
    embeddings = np.load(KB / "index" / "document_embeddings.npy", mmap_mode="r", allow_pickle=False)
    if embeddings.shape[0] != len(chunks) or sha256_file(KB / "index" / "document_embeddings.npy") != freeze["index_sha256"]:
        failures.append("embedding_index_mismatch")
    norms = np.linalg.norm(embeddings, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-4):
        failures.append("embedding_norm_mismatch")
    invariance = read_json(KB / "audit" / "input_invariance_report.json")
    current_snapshot = historical_snapshot()
    current_snapshot_hash = sha256_bytes(canonical_json(current_snapshot))
    if invariance.get("status") != "PASS" or current_snapshot_hash != invariance.get("pre_snapshot_sha256"):
        failures.append("historical_input_invariance_mismatch")
    report = {
        "artifact": "Knowledge Base V1 final integrity verification",
        "status": "PASS" if not failures else "FAIL",
        "knowledge_base_status": freeze.get("status"),
        "rag_retrieval_status": rag.get("status"),
        "source_count": len(source_rows),
        "chunk_count": len(chunks),
        "embedding_shape": list(embeddings.shape),
        "historical_files_checked": len(current_snapshot),
        "historical_snapshot_sha256": current_snapshot_hash,
        "failures": failures,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    destination = KB / "audit" / "final_integrity_report.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "sources": len(source_rows), "chunks": len(chunks), "historical_files": len(current_snapshot), "failures": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
