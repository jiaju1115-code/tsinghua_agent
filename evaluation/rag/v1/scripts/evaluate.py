from __future__ import annotations

import hashlib
import json
import os
import statistics
import time
from pathlib import Path

import psutil
import yaml

from retrieval_engine import CONFIG, HybridRetriever, Reranker, DenseRetriever, TfidfRetriever


V1 = Path(__file__).resolve().parents[1]
EVAL_DIR = V1 / "evaluation"
REPORT_DIR = V1 / "reports"
QUERIES = [json.loads(x) for x in (EVAL_DIR / "eval_queries.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
ALIASES = {
    "教务与学籍": {"教务与学籍", "教务学籍"}, "学生事务": {"学生事务"}, "住宿服务": {"住宿服务", "住宿"},
    "餐饮服务": {"餐饮服务", "餐饮"}, "交通服务": {"交通服务", "交通"}, "医疗健康": {"医疗健康", "医疗"},
    "网络与信息化": {"网络与信息化", "校园网"}, "图书馆服务": {"图书馆服务", "图书馆"},
    "体育与场馆": {"体育与场馆", "体育场馆"}, "奖助与资助": {"奖助与资助", "奖助"},
    "国际事务与签证": {"国际事务与签证", "国际事务"}, "就业与职业发展": {"就业与职业发展", "就业"},
    "科研参与": {"科研参与", "科研参与与资源导航", "科研"}, "教学培养": {"教学培养", "教学与培养", "教学"},
    "校园综合服务": {"校园综合服务"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def trim_result(row: dict) -> dict:
    allowed = ["rank", "chunk_id", "score", "source_id", "category", "title", "url", "original_file",
               "chunk_index", "text_preview", "tfidf_score", "dense_score", "sparse_rank", "sparse_score",
               "dense_rank", "rrf_score", "final_rank", "hybrid_rank", "reranker_score"]
    return {k: row.get(k) for k in allowed if k in row}


def run_method(name: str, search_fn) -> tuple[list[dict], list[float]]:
    records, latencies = [], []
    for q in QUERIES:
        started = time.perf_counter()
        rows = search_fn(q["query"])
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)
        rows = [trim_result(r) for r in rows]
        record = {**q, "method": name, "query_latency_ms": elapsed_ms, "top_1": rows[:1], "top_3": rows[:3],
                  "top_5": rows[:5], "top_10": rows[:10]}
        records.append(record)
    out = EVAL_DIR / f"results_{name}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return records, latencies


def hits(q: dict, rows: list[dict]) -> dict:
    expected = q.get("expected_source_id")
    source_ranks = [i for i, r in enumerate(rows, 1) if expected and r["source_id"] == expected]
    categories = ALIASES.get(q["category"], {q["category"]})
    category_hit = any(r["category"] in categories for r in rows[:5])
    keywords = [k.strip().lower() for k in (q.get("expected_evidence_keyword") or "").split("|") if k.strip()]
    evidence_hit = any(any(k in (r["title"] + " " + r["text_preview"]).lower() for k in keywords) for r in rows[:5]) if keywords else None
    return {"first_source_rank": min(source_ranks) if source_ranks else None, "category_hit_5": category_hit,
            "source_hit_5": bool(source_ranks and min(source_ranks) <= 5), "evidence_hit_5": evidence_hit}


def metrics(records: list[dict]) -> dict:
    reliable = [r for r in records if r["expected_source_status"] == "reliable" and r.get("expected_source_id")]
    uncertain = [r for r in records if r not in reliable]
    ranks = []
    evidence = []
    for r in reliable:
        h = hits(r, r["top_10"])
        ranks.append(h["first_source_rank"])
        if h["evidence_hit_5"] is not None:
            evidence.append(h["evidence_hit_5"])
    all_category = [hits(r, r["top_10"])["category_hit_5"] for r in records]
    result = {
        "query_count": len(records), "reliable_expected_source_count": len(reliable),
        "uncertain_expected_source_count": len(uncertain),
        **{f"recall_at_{k}": sum(rank is not None and rank <= k for rank in ranks) / len(ranks) for k in [1, 3, 5, 10]},
        "mrr": sum(0 if rank is None else 1 / rank for rank in ranks) / len(ranks),
        "category_hit_at_5": sum(all_category) / len(all_category),
        "source_hit_at_5": sum(rank is not None and rank <= 5 for rank in ranks) / len(ranks),
        "evidence_hit_at_5": sum(evidence) / len(evidence) if evidence else None,
        "uncertain_query_ids_excluded_from_recall": [r["query_id"] for r in uncertain],
    }
    return result


def latency_summary(values: list[float], peak_mb: float) -> dict:
    return {"avg_query_latency_ms": statistics.mean(values), "p50_query_latency_ms": percentile(values, .5),
            "p95_query_latency_ms": percentile(values, .95), "max_query_latency_ms": max(values),
            "peak_process_rss_mb": peak_mb}


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    process = psutil.Process(os.getpid())
    peak = process.memory_info().rss / 1024**2
    sparse = TfidfRetriever()
    dense = DenseRetriever()
    hybrid = HybridRetriever(sparse, dense)
    peak = max(peak, process.memory_info().rss / 1024**2)

    # One unreported warm-up avoids charging lazy tensor/kernel initialization to a single query.
    sparse.search(QUERIES[0]["query"], 2)
    dense.search(QUERIES[0]["query"], 2)

    outputs, performance = {}, {}
    outputs["tfidf"], latency = run_method("tfidf", lambda q: sparse.search(q, 10))
    performance["tfidf"] = latency_summary(latency, process.memory_info().rss / 1024**2)
    outputs["dense"], latency = run_method("dense", lambda q: dense.search(q, 10))
    performance["dense"] = latency_summary(latency, process.memory_info().rss / 1024**2)
    outputs["hybrid"], latency = run_method("hybrid", lambda q: hybrid.search(q, 10))
    performance["hybrid"] = latency_summary(latency, process.memory_info().rss / 1024**2)

    reranker_status = {"status": "NOT_ATTEMPTED"}
    try:
        started = time.perf_counter()
        reranker = Reranker()
        load_seconds = time.perf_counter() - started
        peak = max(peak, process.memory_info().rss / 1024**2)
        rerank_only_latencies: list[float] = []
        warm_candidates = hybrid.search(QUERIES[0]["query"], 2, 2)
        reranker.rerank(QUERIES[0]["query"], warm_candidates, 2)
        def rerank_search(q: str):
            candidates = hybrid.search(q, CONFIG["reranker"]["candidate_top_n"], CONFIG["reranker"]["candidate_top_n"])
            rerank_started = time.perf_counter()
            rows = reranker.rerank(q, candidates, 10)
            rerank_only_latencies.append((time.perf_counter() - rerank_started) * 1000)
            return rows
        outputs["hybrid_rerank"], latency = run_method("hybrid_rerank", rerank_search)
        performance["hybrid_rerank"] = latency_summary(latency, max(peak, process.memory_info().rss / 1024**2))
        performance["reranker_only"] = latency_summary(rerank_only_latencies, max(peak, process.memory_info().rss / 1024**2))
        reranker_status = {"status": "PASS", "model_name": CONFIG["reranker"]["model_name"],
                           "revision": CONFIG["reranker"]["revision"], "load_seconds": load_seconds,
                           "weights_sha256": sha256(V1 / CONFIG["reranker"]["local_model_path"] / "model.safetensors"),
                           "candidate_count": CONFIG["reranker"]["candidate_top_n"],
                           "total_pipeline_latency": performance["hybrid_rerank"],
                           "reranker_only_latency": performance["reranker_only"]}
    except Exception as exc:
        reranker_status = {"status": "FAIL", "model_name": CONFIG["reranker"]["model_name"],
                           "error_type": type(exc).__name__, "error": str(exc)}
        outputs["hybrid_rerank"] = []
        (EVAL_DIR / "results_hybrid_rerank.jsonl").write_text("".join(json.dumps({**q, "method": "hybrid_rerank",
            "status": "RERANKER_UNAVAILABLE", "failure": reranker_status, "top_1": [], "top_3": [], "top_5": [], "top_10": []},
            ensure_ascii=False) + "\n" for q in QUERIES), encoding="utf-8")

    metric_values = {name: metrics(records) if records else {"status": "UNAVAILABLE"} for name, records in outputs.items()}
    payload = {"metrics": metric_values, "performance": performance, "reranker": reranker_status,
               "result_file_hashes": {name: sha256(EVAL_DIR / f"results_{name}.jsonl") for name in outputs}}
    (EVAL_DIR / "metrics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (V1 / "indexes" / "hybrid").mkdir(parents=True, exist_ok=True)
    (V1 / "indexes" / "hybrid" / "rrf_config_and_metrics.json").write_text(json.dumps({"config": CONFIG["hybrid"],
        "metrics": metric_values["hybrid"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (V1 / "indexes" / "reranker").mkdir(parents=True, exist_ok=True)
    (V1 / "indexes" / "reranker" / "benchmark_report.json").write_text(json.dumps(reranker_status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
