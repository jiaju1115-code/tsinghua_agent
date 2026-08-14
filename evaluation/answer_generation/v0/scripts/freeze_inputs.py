from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path


OUT = Path(__file__).resolve().parents[1]
DATA = OUT.parent
RAG1 = DATA / "rag_v1"
RAG0 = DATA / "rag_v0"
MODEL = Path(r"C:\Users\林宇轩\.cache\huggingface\hub\models--Qwen--Qwen2.5-1.5B-Instruct-GGUF\snapshots\91cad51170dc346986eccefdc2dd33a9da36ead9\qwen2.5-1.5b-instruct-q4_k_m.gguf")

CRITICAL = {
    "rag_v0_chunks": RAG0 / "chunks" / "chunks.jsonl",
    "rag_v0_smoke_results": RAG0 / "retrieval_results" / "retrieval_smoke_results.jsonl",
    "rag_v1_config": RAG1 / "config" / "retrieval.yaml",
    "rag_v1_eval_queries": RAG1 / "evaluation" / "eval_queries.jsonl",
    "rag_v1_dense_results": RAG1 / "evaluation" / "results_dense.jsonl",
    "rag_v1_dense_evidence": RAG1 / "evaluation" / "recommended_dense_evidence.jsonl",
    "rag_v1_dense_embeddings": RAG1 / "indexes" / "dense" / "document_embeddings.npy",
    "rag_v1_dense_row_mapping": RAG1 / "indexes" / "dense" / "row_mapping.jsonl",
    "rag_v1_dense_report": RAG1 / "indexes" / "dense" / "index_report.json",
    "generation_model": MODEL,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def external_tree_inventory() -> dict:
    rows = []
    for root, dirs, files in os.walk(DATA):
        root_path = Path(root)
        if root_path == OUT or OUT in root_path.parents:
            dirs[:] = []
            continue
        for name in sorted(files):
            path = root_path / name
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            rows.append({"path": path.relative_to(DATA).as_posix(), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    rows.sort(key=lambda r: r["path"])
    encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"file_count": len(rows), "metadata_sha256": hashlib.sha256(encoded).hexdigest(), "rows": rows}


def main() -> None:
    missing = [name for name, path in CRITICAL.items() if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing frozen inputs: {missing}")
    eval_queries = [json.loads(x) for x in CRITICAL["rag_v1_eval_queries"].read_text(encoding="utf-8").splitlines() if x.strip()]
    dense = [json.loads(x) for x in CRITICAL["rag_v1_dense_results"].read_text(encoding="utf-8").splitlines() if x.strip()]
    evidence = [json.loads(x) for x in CRITICAL["rag_v1_dense_evidence"].read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(eval_queries) != 38 or len(dense) != 38 or len(evidence) != 38:
        raise SystemExit("Frozen evaluation input count is not 38")
    if [r["query_id"] for r in eval_queries] != [r["query_id"] for r in dense] or [r["query_id"] for r in dense] != [r["query_id"] for r in evidence]:
        raise SystemExit("Question ordering differs across frozen RAG V1 inputs")
    if any(len(r["top_5"]) != 5 for r in dense) or any(len(r["evidence"]) != 5 for r in evidence):
        raise SystemExit("Dense Top-5 input incomplete")
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "policy": "Read-only reuse; no embedding retraining and no RAG V1 writes",
        "counts": {"questions": 38, "confirmed_smoke": 10, "provisional_eval": 28, "dense_top_k": 5},
        "critical_inputs": {name: {"path": str(path), "size": path.stat().st_size, "sha256": sha256(path)} for name, path in CRITICAL.items()},
        "external_tree_before": external_tree_inventory(),
        "environment": {"os": platform.platform(), "python": platform.python_version()},
    }
    audit = OUT / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "input_freeze.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "questions": 38, "dense_top_k": 5,
                      "external_files": payload["external_tree_before"]["file_count"],
                      "inventory_sha256": payload["external_tree_before"]["metadata_sha256"],
                      "model_sha256": payload["critical_inputs"]["generation_model"]["sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
