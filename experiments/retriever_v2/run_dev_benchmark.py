"""Development-only comparison of frozen Dense V1 and Hybrid Retriever V2.

Gold is accepted only when an existing historical source gold maps to the
frozen KB by the identical historical source URL.  Held-out E2E data is never
read by this runner.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

from hybrid_retriever import CONFIG, HybridRetrieverV2


ROOT = Path(__file__).resolve().parents[2]
QUERIES = ROOT / "evaluation" / "rag" / "v1" / "evaluation" / "eval_queries.jsonl"
LEGACY_SOURCES = ROOT / "evaluation" / "rag" / "v0" / "knowledge_base_manifest" / "knowledge_base_manifest.jsonl"
FROZEN_SOURCES = ROOT / "data" / "03_knowledge_base" / "v1" / "manifests" / "source_manifest.jsonl"
OUT = Path(__file__).resolve().parent / "dev_benchmark.json"
CUTOFFS = (5, 20, 50)


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def first_rank(rows: list[dict], source_id: str) -> int | None:
    return next((row["rank"] for row in rows if row["source_id"] == source_id), None)


def metrics(ranks: list[int | None], cutoff: int) -> dict[str, float | int]:
    return {
        f"recall_at_{cutoff}": round(sum(rank is not None and rank <= cutoff for rank in ranks) / len(ranks), 6),
        f"mrr_at_{cutoff}": round(sum(1 / rank for rank in ranks if rank is not None and rank <= cutoff) / len(ranks), 6),
        "eligible_cases": len(ranks),
    }


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite benchmark: {OUT}")
    queries, legacy, frozen = jsonl(QUERIES), jsonl(LEGACY_SOURCES), jsonl(FROZEN_SOURCES)
    legacy_url = {row["source_id"]: row["url"] for row in legacy}
    frozen_by_url = {row["url"]: row["canonical_source_id"] for row in frozen}
    eligible, excluded = [], Counter()
    for row in queries:
        expected = row.get("expected_source_id")
        frozen_gold = frozen_by_url.get(legacy_url.get(expected)) if expected else None
        if frozen_gold:
            eligible.append({**row, "gold_source_id": frozen_gold, "gold_resolution": "existing_historical_source_id_to_identical_frozen_url"})
        else:
            excluded["no_existing_gold" if not expected else "historical_gold_not_present_in_frozen_kb"] += 1

    retriever = HybridRetrieverV2()
    flags, dense_ranks, hybrid_ranks = [], [], []
    aggregate = {cutoff: Counter() for cutoff in CUTOFFS}
    for row in eligible:
        query_vector = retriever.dense_v1._encode_query(row["query"])
        scores = np.asarray(retriever.dense_v1.embeddings @ query_vector)
        dense_indices = sorted(range(len(retriever.chunks)), key=lambda i: (-float(scores[i]), retriever.chunks[i]["chunk_id"]))[:50]
        dense_rows = [{"rank": rank, "source_id": retriever.chunks[index]["canonical_source_id"]} for rank, index in enumerate(dense_indices, 1)]
        hybrid_rows = retriever._retrieve_from_query_vector(row["query"], row["query_id"], 50, query_vector)["results"]
        bm25_rows = [{"rank": rank, "source_id": retriever.chunks[index]["canonical_source_id"]} for rank, (index, _) in enumerate(retriever.bm25.search(row["query"], 50, retriever.chunks), 1)]
        dense_rank, hybrid_rank, bm25_rank = (first_rank(rows, row["gold_source_id"]) for rows in (dense_rows, hybrid_rows, bm25_rows))
        dense_ranks.append(dense_rank)
        hybrid_ranks.append(hybrid_rank)
        case = {"query_id": row["query_id"], "gold_source_id": row["gold_source_id"], "dense_rank": dense_rank, "bm25_rank": bm25_rank, "hybrid_rank": hybrid_rank}
        for cutoff in CUTOFFS:
            dense_hit = dense_rank is not None and dense_rank <= cutoff
            bm25_hit = bm25_rank is not None and bm25_rank <= cutoff
            hybrid_hit = hybrid_rank is not None and hybrid_rank <= cutoff
            case[f"dense_only_hit_at_{cutoff}"] = dense_hit and not bm25_hit
            case[f"bm25_only_hit_at_{cutoff}"] = bm25_hit and not dense_hit
            case[f"hybrid_rescued_at_{cutoff}"] = hybrid_hit and not dense_hit
            case[f"hybrid_degraded_at_{cutoff}"] = dense_hit and not hybrid_hit
            aggregate[cutoff].update({
                "dense_only_hit": case[f"dense_only_hit_at_{cutoff}"],
                "bm25_only_hit": case[f"bm25_only_hit_at_{cutoff}"],
                "hybrid_rescued": case[f"hybrid_rescued_at_{cutoff}"],
                "hybrid_degraded": case[f"hybrid_degraded_at_{cutoff}"],
            })
        flags.append(case)
    payload = {
        "status": "DEVELOPMENT_ONLY_NOT_HELDOUT", "rrf": CONFIG["rrf"],
        "inputs": {"queries": str(QUERIES.relative_to(ROOT)), "legacy_source_manifest": str(LEGACY_SOURCES.relative_to(ROOT)), "frozen_source_manifest": str(FROZEN_SOURCES.relative_to(ROOT))},
        "gold_policy": "existing historical expected_source_id resolved only by identical URL to frozen KB; no AI/human gold inference",
        "query_count": len(queries), "usable_gold_count": len(eligible), "excluded_without_usable_gold": dict(sorted(excluded.items())),
        "dense_v1": {str(cutoff): metrics(dense_ranks, cutoff) for cutoff in CUTOFFS},
        "hybrid_v2": {str(cutoff): metrics(hybrid_ranks, cutoff) for cutoff in CUTOFFS},
        "comparison_counts": {str(cutoff): dict(aggregate[cutoff]) for cutoff in CUTOFFS},
        "case_flags": flags,
        "performance_conclusion": "NOT_APPLICABLE: development benchmark only; no held-out evaluation or parameter tuning performed.",
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "usable_gold_count": len(eligible), "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
