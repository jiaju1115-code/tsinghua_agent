"""Development-only retrieval diagnostic; it never reads held-out E2E assets."""
from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2.query_planner import CampusQueryPlanner
from src.trusted_campus_agent_v2.retrieval import TrustedHybridRetrieverV2


BASELINE = ROOT / "experiments" / "retriever_v2" / "dev_benchmark.json"
QUERIES = ROOT / "evaluation" / "rag" / "v1" / "evaluation" / "eval_queries.jsonl"
OUTPUT = Path(__file__).resolve().parent / "dev_retrieval_metrics.json"


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def rank(rows: list[dict], source_id: str) -> int | None:
    return next((row["rank"] for row in rows if row["source_id"] == source_id), None)


def metrics(ranks: list[int | None], cutoff: int) -> dict:
    return {
        "recall": round(sum(value is not None and value <= cutoff for value in ranks) / len(ranks), 6),
        "mrr": round(sum(1 / value for value in ranks if value is not None and value <= cutoff) / len(ranks), 6),
        "cases": len(ranks),
    }


def main() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    query_by_id = {row["query_id"]: row["query"] for row in jsonl(QUERIES)}
    cases = [
        {
            "query_id": row["query_id"], "query": query_by_id[row["query_id"]],
            "gold_source_id": row["gold_source_id"], "baseline_dense_rank": row["dense_rank"],
            "baseline_hybrid_rank": row["hybrid_rank"],
        }
        for row in baseline["case_flags"]
    ]
    planner = CampusQueryPlanner()
    retriever = TrustedHybridRetrieverV2()
    adaptive_ranks, forced_full_ranks, details = [], [], []
    public_adaptive, public_forced, public_dense, public_hybrid = [], [], [], []
    routes = Counter()
    for row in cases:
        adaptive_plan = planner.plan(row["query"])
        routes[adaptive_plan.path] += 1
        adaptive = retriever.retrieve(adaptive_plan, top_k=20, as_of=date(2026, 8, 30))
        forced_plan = replace(adaptive_plan, subqueries=(adaptive_plan.rewritten_query,), path="FULL")
        forced = retriever.retrieve(forced_plan, top_k=20, as_of=date(2026, 8, 30))
        adaptive_rank = rank(adaptive["results"], row["gold_source_id"])
        forced_rank = rank(forced["results"], row["gold_source_id"])
        access_level = retriever.metadata.get(row["gold_source_id"], {}).get("access_level", "public")
        adaptive_ranks.append(adaptive_rank)
        forced_full_ranks.append(forced_rank)
        if access_level == "public":
            public_adaptive.append(adaptive_rank)
            public_forced.append(forced_rank)
            public_dense.append(row["baseline_dense_rank"])
            public_hybrid.append(row["baseline_hybrid_rank"])
        details.append({
            **row, "route": adaptive_plan.path, "adaptive_rank": adaptive_rank,
            "forced_full_rank": forced_rank, "gold_access_level": access_level,
        })
    restricted_count = len(cases) - len(public_adaptive)
    payload = {
        "status": "DEVELOPMENT_ONLY_NOT_HELDOUT",
        "as_of": "2026-08-30",
        "gold_policy": baseline["gold_policy"],
        "case_count": len(cases), "public_case_count": len(public_adaptive),
        "restricted_gold_excluded_from_public_metrics": restricted_count,
        "route_counts": dict(routes),
        "baseline_dense_v1": baseline["dense_v1"],
        "baseline_hybrid_v2": baseline["hybrid_v2"],
        "all_cases_with_public_access_policy": {
            "adaptive": {str(k): metrics(adaptive_ranks, k) for k in (5, 20)},
            "forced_full": {str(k): metrics(forced_full_ranks, k) for k in (5, 20)},
        },
        "public_only_comparison": {
            "baseline_dense_v1": {str(k): metrics(public_dense, k) for k in (5, 20)},
            "baseline_hybrid_v2": {str(k): metrics(public_hybrid, k) for k in (5, 20)},
            "trusted_v2_adaptive": {str(k): metrics(public_adaptive, k) for k in (5, 20)},
            "trusted_v2_forced_full": {str(k): metrics(public_forced, k) for k in (5, 20)},
        },
        "case_details": details,
        "limitations": [
            "existing development gold only; not held-out and not a production claim",
            "only 19 historical URL-resolved cases are eligible",
            "parameters were not tuned on held-out E2E data",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("status", "case_count", "public_case_count", "restricted_gold_excluded_from_public_metrics", "route_counts", "public_only_comparison")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
