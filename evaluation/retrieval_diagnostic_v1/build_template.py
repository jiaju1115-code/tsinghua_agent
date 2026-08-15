"""Build a human-label-ready retrieval diagnostic dataset from a frozen replay.

This is deliberately post-hoc only: it never invokes a retriever, edits the
held-out evaluation, or infers any gold / failure labels.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPLAY = ROOT / "evaluation" / "e2e_heldout" / "v1" / "diagnostic" / "retrieval_replay.jsonl"
DEFAULT_CASES = ROOT / "evaluation" / "e2e_heldout" / "v1" / "cases" / "e2e_50_cases.jsonl"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "retrieval_gold_template.jsonl"
DEFAULT_STATS = Path(__file__).resolve().parent / "retrieval_diagnostic_stats.json"
FAILURE_TYPES = [
    "kb_missing", "retrieval_miss", "ranking_miss", "entity_mismatch",
    "evidence_over_refusal", "other",
]


def tokens(text: str) -> set[str]:
    """Low-cost, language-agnostic lexical features (words plus CJK chars)."""
    return set(re.findall(r"[\u3400-\u9fff]|[A-Za-z0-9_]+", text.lower()))


def lexical_features(query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    query_terms = tokens(query)
    per_chunk = []
    for row in chunks:
        candidate_terms = tokens(f"{row.get('title', '')}\n{row.get('text', '')}")
        shared = query_terms & candidate_terms
        union = query_terms | candidate_terms
        per_chunk.append({
            "rank": row.get("rank"),
            "query_token_overlap_count": len(shared),
            "query_token_overlap_ratio": round(len(shared) / len(query_terms), 6) if query_terms else 0.0,
            "query_candidate_jaccard": round(len(shared) / len(union), 6) if union else 0.0,
        })
    return {
        "query_token_count": len(query_terms),
        "top5_max_query_token_overlap_ratio": max((x["query_token_overlap_ratio"] for x in per_chunk), default=0.0),
        "top5_mean_query_token_overlap_ratio": round(sum(x["query_token_overlap_ratio"] for x in per_chunk) / len(per_chunk), 6) if per_chunk else 0.0,
        "per_chunk": per_chunk,
    }


def build_row(replay: dict[str, Any], case_categories: dict[str, str]) -> dict[str, Any]:
    chunks = replay.get("ordered_top5_chunks", [])
    return {
        "case_id": replay["case_id"],
        "query": replay["query"],
        "category": case_categories.get(replay["case_id"]),
        "top5": [{
            "rank": x.get("rank"), "chunk_id": x.get("chunk_id"),
            "source_id": x.get("source_id"), "score": x.get("score"),
        } for x in chunks],
        "top5_unique_source_count": len({x.get("source_id") for x in chunks if x.get("source_id")}),
        "lexical_features": lexical_features(replay["query"], chunks),
        "gold_exists_in_kb": None,
        "gold_chunk_id": None,
        "gold_source_id": None,
        "gold_rank": None,
        "failure_type": None,
        "hard_negative_chunk_id": None,
        "note": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    args = parser.parse_args()
    if not args.replay.is_file() or not args.cases.is_file():
        raise SystemExit("replay input or case metadata input not found")
    if args.output.exists() or args.stats.exists():
        raise SystemExit("refusing to overwrite diagnostic outputs")
    case_categories = {row["case_id"]: row["category"] for row in (json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip())}
    rows = [build_row(json.loads(line), case_categories) for line in args.replay.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(row["category"] is None for row in rows):
        raise RuntimeError("every replay case must resolve to its held-out case category")
    if any(row["failure_type"] is not None or row["gold_chunk_id"] is not None for row in rows):
        raise RuntimeError("template construction must not populate human labels")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    stats = {
        "status": "TEMPLATE_READY_NO_HUMAN_GOLD_LABELS",
        "input_replay": str(args.replay.relative_to(ROOT)),
        "case_count": len(rows),
        "top5_unique_source_count_distribution": dict(sorted(Counter(x["top5_unique_source_count"] for x in rows).items())),
        "category_distribution": dict(sorted(Counter(x["category"] for x in rows).items(), key=lambda x: str(x[0]))),
        "allowed_failure_types": FAILURE_TYPES,
        "human_fields_all_null": all(
            all(row[field] is None for field in ("gold_exists_in_kb", "gold_chunk_id", "gold_source_id", "gold_rank", "failure_type", "hard_negative_chunk_id", "note"))
            for row in rows
        ),
    }
    args.stats.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": stats["status"], "case_count": len(rows), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
