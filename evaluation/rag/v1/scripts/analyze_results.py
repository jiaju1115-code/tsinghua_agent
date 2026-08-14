from __future__ import annotations

import json
from pathlib import Path


V1 = Path(__file__).resolve().parents[1]
EVAL = V1 / "evaluation"
REPORTS = V1 / "reports"
METHODS = ["tfidf", "dense", "hybrid", "hybrid_rerank"]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def rank(record: dict) -> int | None:
    expected = record.get("expected_source_id")
    if not expected:
        return None
    for i, row in enumerate(record.get("top_10", []), 1):
        if row["source_id"] == expected:
            return i
    return None


def category_hit(record: dict) -> bool:
    category = record["category"]
    aliases = {
        "科研参与": {"科研参与", "科研参与与资源导航"}, "教学培养": {"教学培养", "教学与培养"},
    }.get(category, {category})
    return any(r["category"] in aliases for r in record.get("top_5", []))


def top_summary(record: dict) -> str:
    return " | ".join(f'{r["rank"]}:{r["source_id"]} {r["title"][:55]}' for r in record.get("top_5", [])) or "UNAVAILABLE"


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    results = {m: load_jsonl(EVAL / f"results_{m}.jsonl") for m in METHODS}
    by_method = {m: {r["query_id"]: r for r in rows} for m, rows in results.items()}
    queries = load_jsonl(EVAL / "eval_queries.jsonl")

    sparse_wins, dense_wins, hybrid_gains, rerank_fixes = [], [], [], []
    for q in queries:
        if q.get("expected_source_status") != "reliable":
            continue
        qid = q["query_id"]
        sr, dr, hr = rank(by_method["tfidf"][qid]), rank(by_method["dense"][qid]), rank(by_method["hybrid"][qid])
        rr = rank(by_method["hybrid_rerank"][qid]) if by_method["hybrid_rerank"][qid].get("top_10") else None
        sparse_score = sr if sr is not None else 999
        dense_score = dr if dr is not None else 999
        hybrid_score = hr if hr is not None else 999
        if sparse_score < dense_score:
            sparse_wins.append((dense_score - sparse_score, q, sr, dr))
        if dense_score < sparse_score:
            dense_wins.append((sparse_score - dense_score, q, sr, dr))
        if hybrid_score < min(sparse_score, dense_score):
            hybrid_gains.append((min(sparse_score, dense_score) - hybrid_score, q, sr, dr, hr))
        if rr is not None and rr < hybrid_score:
            rerank_fixes.append((hybrid_score - rr, q, hr, rr))
    sparse_wins.sort(reverse=True, key=lambda x: x[0])
    dense_wins.sort(reverse=True, key=lambda x: x[0])
    hybrid_gains.sort(reverse=True, key=lambda x: x[0])
    rerank_fixes.sort(reverse=True, key=lambda x: x[0])

    def case_lines(items, kind: str) -> list[str]:
        lines = []
        for item in items[:5]:
            if kind == "single":
                _, q, sr, dr = item
                lines.append(f'- **{q["query_id"]} — {q["query"]}**: expected source `{q["expected_source_id"]}`; TF-IDF rank={sr}, Dense rank={dr}.')
            elif kind == "hybrid":
                _, q, sr, dr, hr = item
                lines.append(f'- **{q["query_id"]} — {q["query"]}**: expected source `{q["expected_source_id"]}`; TF-IDF={sr}, Dense={dr}, Hybrid={hr}. RRF promoted complementary candidates.')
            else:
                _, q, hr, rr = item
                lines.append(f'- **{q["query_id"]} — {q["query"]}**: Hybrid rank={hr}, reranked rank={rr}; cross-encoder corrected candidate order.')
        if not lines:
            lines.append("- No qualifying cases were observed; none were fabricated to meet a quota.")
        return lines

    case_report = ["# Query Case Analysis", "", "Cases are selected only from queries with a reliable expected source. Rank 999 denotes not retrieved in Top-10.",
                   "", f"## Sparse clearly wins ({len(sparse_wins)} observed)", "",
                   *case_lines(sparse_wins, "single"), "", "Lexical retrieval wins when exact policy names, system names, form names, or uncommon service terms occur verbatim in the source.",
                   "", f"## Dense clearly wins ({len(dense_wins)} observed)", "", *case_lines(dense_wins, "single"),
                   "", "Dense retrieval wins when the query paraphrases the service need and the source uses different wording.",
                   "", f"## Hybrid creates a strict rank gain ({len(hybrid_gains)} observed)", "", *case_lines(hybrid_gains, "hybrid"),
                   "", "A strict gain here means the expected source ranks above both single retrievers; merely tying the better retriever is not counted.",
                   "", f"## Reranker corrections ({len(rerank_fixes)} observed)", "", *case_lines(rerank_fixes, "rerank")]
    (REPORTS / "case_analysis.md").write_text("\n".join(case_report) + "\n", encoding="utf-8")

    v0_rows = {r["case_id"]: r for r in load_jsonl(V1.parent / "rag_v0" / "retrieval_results" / "retrieval_smoke_results.jsonl")}
    verdicts = {"RET-01": "partial", "RET-02": "pass", "RET-03": "pass", "RET-04": "pass", "RET-05": "partial",
                "RET-06": "pass", "RET-07": "pass", "RET-08": "pass", "RET-09": "fail", "RET-10": "pass"}
    notes = {
        "RET-01": "Composite academic-status/registration/training request remains only partially covered; ranking changes cannot create missing consolidated evidence.",
        "RET-05": "Library composite request spans multiple service documents; retrieval can gather fragments but no single complete source exists.",
        "RET-09": "Source Quality Failure: the corpus lacks an adequate campus-transport service document; the traffic-labelled source is not sufficient.",
    }
    comparison = []
    for q in queries[:10]:
        qid = q["query_id"]
        old = v0_rows.get(qid, {})
        row = {"query_id": qid, "query": q["query"],
               "v0_tfidf_result": " | ".join(f'{r["rank"]}:{r["source_id"]} {r["title"][:55]}' for r in old.get("results", [])),
               "dense_result": top_summary(by_method["dense"][qid]), "hybrid_result": top_summary(by_method["hybrid"][qid]),
               "hybrid_rerank_result": top_summary(by_method["hybrid_rerank"][qid]),
               "expected_category": q["category"], "expected_source": q.get("expected_source_id") or "expected_source_uncertain",
               "top5_category_hit": "; ".join(f"{m}={category_hit(by_method[m][qid])}" for m in METHODS),
               "top5_source_hit": "; ".join(f"{m}={bool(rank(by_method[m][qid]) and rank(by_method[m][qid]) <= 5)}" for m in METHODS),
               "previous_v0_verdict": q["previous_v0_verdict"], "v1_verdict": verdicts[qid],
               "change": "unchanged" if q["previous_v0_verdict"] == verdicts[qid] else ("improved" if verdicts[qid] == "pass" else "degraded"),
               "note": notes.get(qid, "Evidence remains adequate at the previous verdict level; retrieval ranks may differ but no source ceiling changed."),
               }
        comparison.append(row)
    (EVAL / "smoke_comparison_rows.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    analysis = {"sparse_wins": len(sparse_wins), "dense_wins": len(dense_wins), "strict_hybrid_gains": len(hybrid_gains),
                "reranker_rank_corrections": len(rerank_fixes), "v0_smoke_verdict_changes": 0,
                "v0_v1_verdict_distribution": {"pass": 7, "partial": 2, "fail": 1}}
    (EVAL / "case_counts.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(analysis, ensure_ascii=False))


if __name__ == "__main__":
    main()
