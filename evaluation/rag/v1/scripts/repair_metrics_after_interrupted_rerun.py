from __future__ import annotations

import hashlib
import json
from pathlib import Path


V1 = Path(__file__).resolve().parents[1]
EVAL = V1 / "evaluation"


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


payload = json.loads((EVAL / "metrics.json").read_text(encoding="utf-8"))
for method in ["tfidf", "dense", "hybrid", "hybrid_rerank"]:
    path = EVAL / f"results_{method}.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    latencies = [r["query_latency_ms"] for r in rows]
    if method != "hybrid_rerank":
        perf = payload["performance"][method]
        perf.update({"avg_query_latency_ms": sum(latencies) / len(latencies),
                     "p50_query_latency_ms": percentile(latencies, .5),
                     "p95_query_latency_ms": percentile(latencies, .95),
                     "max_query_latency_ms": max(latencies)})
    payload["result_file_hashes"][method] = hashlib.sha256(path.read_bytes()).hexdigest()
(EVAL / "metrics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "result_file_hashes": payload["result_file_hashes"],
                  "performance": payload["performance"]}, ensure_ascii=False))
