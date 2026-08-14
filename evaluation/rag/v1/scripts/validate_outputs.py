from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
from safetensors import safe_open


V1 = Path(__file__).resolve().parents[1]
EVAL = V1 / "evaluation"
errors: list[str] = []

audit = json.loads((V1 / "audit" / "chunk_integrity_report.json").read_text(encoding="utf-8"))
if audit["status"] != "PASS" or audit["counts"]["chunks"] != 717:
    errors.append("chunk audit failed")

emb = np.load(V1 / "indexes" / "dense" / "document_embeddings.npy", mmap_mode="r")
if emb.shape != (717, 512) or not np.allclose(np.linalg.norm(emb, axis=1), 1.0, atol=1e-4):
    errors.append("dense embedding shape or normalization failed")
mapping = [json.loads(x) for x in (V1 / "indexes" / "dense" / "row_mapping.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
if len(mapping) != 717 or [m["embedding_row"] for m in mapping] != list(range(717)):
    errors.append("dense row mapping failed")

for method in ["tfidf", "dense", "hybrid", "hybrid_rerank"]:
    rows = [json.loads(x) for x in (EVAL / f"results_{method}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(rows) != 38 or len({r["query_id"] for r in rows}) != 38:
        errors.append(f"{method}: result count/uniqueness failed")
    for r in rows:
        if [len(r[f"top_{k}"]) for k in [1, 3, 5, 10]] != [1, 3, 5, 10]:
            errors.append(f"{method}:{r['query_id']}: cutoff lengths failed")
        if method == "hybrid":
            required = {"sparse_rank", "sparse_score", "dense_rank", "dense_score", "rrf_score", "final_rank"}
            if any(not required.issubset(item) for item in r["top_10"]):
                errors.append(f"hybrid:{r['query_id']}: lineage fields failed")

metrics = json.loads((EVAL / "metrics.json").read_text(encoding="utf-8"))
if metrics["reranker"]["status"] != "PASS":
    errors.append("reranker benchmark not PASS")
for method in ["tfidf", "dense", "hybrid", "hybrid_rerank"]:
    path = EVAL / f"results_{method}.jsonl"
    if hashlib.sha256(path.read_bytes()).hexdigest() != metrics["result_file_hashes"][method]:
        errors.append(f"result hash mismatch: {method}")
with safe_open(str(V1 / "indexes" / "reranker" / "model" / "model.safetensors"), framework="pt") as model:
    if len(model.keys()) == 0:
        errors.append("reranker safetensors has no tensors")

for name in ["rag_v1_eval_set.xlsx", "v0_vs_v1_smoke_comparison.xlsx"]:
    path = EVAL / name
    if not path.is_file() or path.stat().st_size < 5_000:
        errors.append(f"workbook missing or too small: {name}")

payload = {"status": "PASS" if not errors else "FAIL", "checks": {
    "chunk_integrity": audit["status"], "dense_shape": list(emb.shape), "dense_rows_traceable": len(mapping),
    "evaluation_methods": 4, "queries_per_method": 38, "reranker": metrics["reranker"]["status"],
    "workbooks": 2,
}, "errors": errors}
(V1 / "audit" / "final_output_validation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
if errors:
    raise SystemExit(2)
