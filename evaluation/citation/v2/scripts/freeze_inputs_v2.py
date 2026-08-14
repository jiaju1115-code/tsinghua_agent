from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
PROJECT = DATA.parent
V1 = DATA / "citation_pipeline_v1"
RAG1 = DATA / "rag_v1"
AE0 = DATA / "answer_eval_v0"
AE1 = DATA / "answer_eval_v1"

CRITICAL = {
    "v1_claims": V1 / "results" / "claims.jsonl",
    "v1_claims_classified": V1 / "results" / "claims_classified.jsonl",
    "v1_claim_mapping": V1 / "results" / "claim_evidence_mapping.jsonl",
    "v1_claim_embeddings": V1 / "results" / "claim_embeddings.npy",
    "v1_assignments": V1 / "results" / "citation_assignments.jsonl",
    "v1_per_question": V1 / "results" / "per_question_results.jsonl",
    "v1_metrics": V1 / "results" / "citation_metrics.json",
    "rag_v0_chunks": DATA / "rag_v0" / "chunks" / "chunks.jsonl",
    "rag_v1_dense_results": RAG1 / "evaluation" / "results_dense.jsonl",
    "rag_v1_doc_embeddings": RAG1 / "indexes" / "dense" / "document_embeddings.npy",
    "rag_v1_row_mapping": RAG1 / "indexes" / "dense" / "row_mapping.jsonl",
    "bge_embedding_weights": RAG1 / "indexes" / "dense" / "model" / "model.safetensors",
    "bge_reranker_weights": RAG1 / "indexes" / "reranker" / "model" / "model.safetensors",
    "ae0_answers": AE0 / "results" / "answer_generation_results.jsonl",
    "ae1_group_a": AE1 / "results" / "generation_a.jsonl"
}


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def inventory():
    rows = []
    for base, dirs, files in os.walk(PROJECT):
        bp = Path(base)
        if bp == ROOT or ROOT in bp.parents:
            dirs[:] = []
            continue
        if ".git" in bp.parts or "node_modules" in bp.parts or "__pycache__" in bp.parts:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__"}]
        for name in sorted(files):
            p = bp / name
            try:
                s = p.stat()
            except FileNotFoundError:
                continue
            rows.append({"path": p.relative_to(PROJECT).as_posix(), "size": s.st_size, "mtime_ns": s.st_mtime_ns})
    rows.sort(key=lambda x: x["path"])
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"file_count": len(rows), "metadata_sha256": digest, "rows": rows}


def main():
    missing = [name for name, path in CRITICAL.items() if not path.is_file()]
    if missing:
        raise SystemExit(f"INPUT_INVARIANCE_FAILURE missing={missing}")
    claims = jsonl(CRITICAL["v1_claims"])
    classified = jsonl(CRITICAL["v1_claims_classified"])
    mapping = jsonl(CRITICAL["v1_claim_mapping"])
    assignments = jsonl(CRITICAL["v1_assignments"])
    per = jsonl(CRITICAL["v1_per_question"])
    dense = jsonl(CRITICAL["rag_v1_dense_results"])
    a = jsonl(CRITICAL["ae1_group_a"])
    v0 = jsonl(CRITICAL["ae0_answers"])
    factual_types = {"FACTUAL", "PROCEDURAL", "TEMPORAL", "NUMERIC", "LOCATION", "ENTITY", "UNCERTAIN"}
    checks = {
        "questions_38": len(per) == len(a) == len(v0) == len(dense) == 38,
        "answers_exact_38": sum(x["generated_answer"] == y["generated_answer"] for x, y in zip(a, v0)) == 38,
        "claims_120": len(claims) == len(classified) == len(mapping) == 120,
        "factual_claims_104": sum(x["claim_type"] in factual_types for x in classified) == 104,
        "claim_ids_exact": [x["claim_id"] for x in claims] == [x["claim_id"] for x in classified] == [x["claim_id"] for x in mapping],
        "question_ids_exact": [x["question_id"] for x in per] == [x["question_id"] for x in a] == [x["query_id"] for x in dense],
        "dense_top5_exact": all(x["retrieved_chunk_ids"] == [z["chunk_id"] for z in y["top_5"]] for x, y in zip(a, dense)),
        "v1_assignments_complete": len(assignments) == 12 and all(x["claim_id"] in {c["claim_id"] for c in claims} for x in assignments)
    }
    status = "PASS" if all(checks.values()) else "INPUT_INVARIANCE_FAILURE"
    inv = inventory()
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "counts": {"questions": len(per), "claims": len(claims), "factual_claims": sum(x["claim_type"] in factual_types for x in classified), "v1_assignments": len(assignments)},
        "critical_inputs": {name: {"path": str(path), "size": path.stat().st_size, "sha256": sha(path)} for name, path in CRITICAL.items()},
        "external_tree_before": inv,
        "policy": {"answers_regenerated": False, "claims_resegmented": False, "top5_rerun": False, "training": False, "web_search": False}
    }
    (ROOT / "audit").mkdir(parents=True, exist_ok=True)
    (ROOT / "audit" / "input_invariance_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "checks": checks, "external_files": inv["file_count"], "inventory_sha256": inv["metadata_sha256"]}, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
