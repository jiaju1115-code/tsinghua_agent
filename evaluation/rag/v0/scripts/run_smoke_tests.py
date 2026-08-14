from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from retrieve import DEFAULT_CONFIG, RAG_DIR, Retriever, assemble_evidence


DEFAULT_CASES = RAG_DIR / "retrieval_test_cases" / "retrieval_test_cases.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(config_path: Path, cases_path: Path) -> dict[str, Any]:
    cases = load_jsonl(cases_path)
    retriever = Retriever(config_path)
    output: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        hits = retriever.search(case["query"], case.get("top_k"))
        searchable = " ".join(f"{x['title']} {x['category']} {x['text']}" for x in hits).lower()
        keyword_hits = [keyword for keyword in case["expected_keywords"] if keyword.lower() in searchable]
        category_hit = any(x["category"] in case["expected_categories"] for x in hits)
        output.append(
            {
                **case,
                "latency_seconds": round(time.perf_counter() - started, 3),
                "keyword_hit_count": len(keyword_hits),
                "matched_keywords": keyword_hits,
                "keyword_hit_at_k": bool(keyword_hits),
                "category_hit_at_k": category_hit,
                "results": hits,
                "evidence_assembly": assemble_evidence(case["query"], hits),
            }
        )
    out_path = RAG_DIR / "retrieval_results" / "retrieval_smoke_results.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in output:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "test_count": len(output),
        "top_k": output[0]["top_k"] if output else None,
        "keyword_hit_at_k_count": sum(row["keyword_hit_at_k"] for row in output),
        "category_hit_at_k_count": sum(row["category_hit_at_k"] for row in output),
        "mean_latency_seconds": round(sum(row["latency_seconds"] for row in output) / len(output), 3) if output else None,
        "note": "These are deterministic heuristic smoke indicators, not human relevance judgments.",
    }
    (RAG_DIR / "retrieval_results" / "retrieval_smoke_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args()
    print(json.dumps(run(args.config.resolve(), args.cases.resolve()), ensure_ascii=False, indent=2))
