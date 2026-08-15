"""Run a functionality-only regression diagnostic against the frozen Retrieval V1 bundle."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.retrieval_v1 import DenseRetrieverV1  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    query_path = ROOT / "evaluation" / "rag" / "v1" / "evaluation" / "eval_queries.jsonl"
    rows = [json.loads(line) for line in query_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    retriever = DenseRetrieverV1()
    expected_keys = {"query", "case_id", "retriever_version", "corpus_version", "ordered_top5_chunks", "source_ids", "chunk_ids", "scores", "latency_ms", "error"}
    errors, schema_failures = [], []
    for row in rows:
        result = retriever.retrieve(row["query"], row["query_id"])
        if result["error"]:
            errors.append({"query_id": row["query_id"], "error": result["error"]})
            continue
        if set(result) != expected_keys or len(result["ordered_top5_chunks"]) != 5 or not all(result["chunk_ids"]):
            schema_failures.append({"query_id": row["query_id"], "keys": sorted(result), "chunk_count": len(result["ordered_top5_chunks"])})
    output = {
        "artifact": "RAG Retrieval V1 functional regression diagnostic",
        "scope": "Historical RAG V1 queries are used only to verify loading, source/chunk mapping, and output schema. This is not held-out evaluation and reports no retrieval-quality metric.",
        "input": "evaluation/rag/v1/evaluation/eval_queries.jsonl",
        "input_sha256": sha256(query_path),
        "query_count": len(rows),
        "processed_count": len(rows),
        "error_count": len(errors),
        "schema_failure_count": len(schema_failures),
        "status": "PASS" if not errors and not schema_failures else "FAIL",
        "errors": errors,
        "schema_failures": schema_failures,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    destination = ROOT / "data" / "03_knowledge_base" / "v1" / "audit" / "regression_diagnostic.json"
    destination.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "queries": len(rows), "errors": len(errors), "schema_failures": len(schema_failures)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
