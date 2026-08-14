from __future__ import annotations

import json
from pathlib import Path


V1 = Path(__file__).resolve().parents[1]
ROOT = V1.parent
chunks = {r["chunk_id"]: r for r in (json.loads(x) for x in (ROOT / "rag_v0" / "chunks" / "chunks.jsonl").read_text(encoding="utf-8-sig").splitlines() if x.strip())}
results = [json.loads(x) for x in (V1 / "evaluation" / "results_dense.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
out = V1 / "evaluation" / "recommended_dense_evidence.jsonl"

records = []
for result in results:
    evidence = []
    for item in result["top_5"]:
        chunk = chunks[item["chunk_id"]]
        evidence.append({
            "rank": item["rank"], "score": item["score"], "chunk_id": chunk["chunk_id"],
            "source_id": chunk["source_id"], "title": chunk["title"], "category": chunk["category"],
            "url": chunk["url"], "source_type": chunk["source_type"], "original_file": chunk["original_file"],
            "chunk_index": chunk["chunk_index"], "text": chunk["text"],
        })
    records.append({"query_id": result["query_id"], "query": result["query"], "retriever": "dense",
                    "assembly_status": "EVIDENCE_ONLY_NO_GENERATED_ANSWER", "evidence": evidence})

out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
print(json.dumps({"status": "PASS", "queries": len(records), "evidence_items": sum(len(r["evidence"]) for r in records),
                  "output": str(out)}, ensure_ascii=False))
