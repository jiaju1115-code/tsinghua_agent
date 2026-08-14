"""Merge generation/evaluation traces and build provisional reports."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


DATA = Path(r"D:\python_projects\tsinghua_ai\data_second")
ROOT = DATA / "answer_eval_v0"
RAG1 = DATA / "rag_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def pct(x):
    return "N/A" if x is None else f"{100*x:.2f}%"


def verdict(auto: dict) -> str:
    if auto.get("refusal_appropriate") is True:
        return "pass"
    return {2: "pass", 1: "partial", 0: "fail"}.get(auto.get("correctness"), "N/A")


def change(previous: str | None, current: str) -> str:
    scale = {"fail": 0, "partial": 1, "pass": 2}
    if previous not in scale or current not in scale:
        return "uncertain"
    return "improved" if scale[current] > scale[previous] else "degraded" if scale[current] < scale[previous] else "unchanged"


def evidence_preview(contexts: list[dict], max_chars=900) -> str:
    out = []
    remaining = max_chars
    for c in contexts[:3]:
        text = " ".join(c["text"].split())
        piece = f"[{c['context_id']}] {c['source_id']} {c['title']}: {text}"
        piece = piece[: max(0, remaining)]
        if piece:
            out.append(piece)
            remaining -= len(piece)
        if remaining <= 0:
            break
    return "\n".join(out)


def derived_consistency(a: dict) -> str:
    """Deterministic consistency layer so rubric fields cannot contradict the label."""
    if a["evidence_sufficiency"] == "insufficient":
        return "retrieval_insufficient_correct_refusal" if a["refusal_appropriate"] is True else "retrieval_insufficient_hallucination"
    if "RETRIEVAL_FAILURE" in a["hallucination_types"]:
        return "retrieval_wrong_answer_wrong"
    return (
        "retrieval_correct_answer_correct"
        if a["correctness"] == 2 and a["faithfulness"] == 2 and a["citation_correctness"] == 2
        else "retrieval_correct_answer_wrong"
    )


def normalize_for_reporting(raw: dict) -> dict:
    """Resolve model-rubric contradictions using observable answer/retrieval state."""
    a = dict(raw)
    types = [t for t in a.get("hallucination_types", []) if t != "NONE"]
    if "RETRIEVAL_FAILURE" in types:
        a["evidence_sufficiency"] = "insufficient"
    refused = bool(a.get("refused"))
    if a.get("evidence_sufficiency") == "insufficient":
        a["refusal_appropriate"] = refused
        if refused:
            # A bare conservative refusal contains no factual claim and needs no citation.
            a["claim_count"] = 0
            a["unsupported_claim_count"] = 0
            a["citation_correctness"] = 2
            types = [t for t in types if t not in {
                "UNSUPPORTED_INFERENCE", "GENERATION_HALLUCINATION",
                "OVERCONFIDENT_ANSWER", "CITATION_MISMATCH",
            }]
        elif any(t in types for t in {"SOURCE_QUALITY_FAILURE", "GENERATION_HALLUCINATION", "OVERCONFIDENT_ANSWER"}):
            # An asserted answer over a known evidence gap contributes at least one
            # unsupported factual claim even if the small judge miscounted claims.
            a["claim_count"] = max(1, int(a.get("claim_count") or 0))
            a["unsupported_claim_count"] = max(1, int(a.get("unsupported_claim_count") or 0))
    else:
        a["refusal_appropriate"] = None
    a["hallucination_types"] = types or ["NONE"]
    return a


def main() -> None:
    gen = read_jsonl(ROOT / "results" / "answer_generation_results.jsonl")
    ev = {r["question_id"]: r for r in read_jsonl(ROOT / "results" / "answer_evaluation_results.jsonl")}
    queries = {r["query_id"]: r for r in read_jsonl(RAG1 / "evaluation" / "eval_queries.jsonl")}
    smoke_old = {
        r["query_id"]: r
        for r in json.loads((RAG1 / "evaluation" / "smoke_comparison_rows.json").read_text(encoding="utf-8"))
    }
    if len(gen) != 38 or len(ev) != 38:
        raise SystemExit(f"Expected 38/38 results, got generation={len(gen)} evaluation={len(ev)}")

    merged = []
    for g in gen:
        e = ev[g["question_id"]]
        q = queries[g["question_id"]]
        auto = normalize_for_reporting(e.get("auto_evaluation") or {})
        auto["model_reported_consistency"] = auto.get("consistency")
        auto["consistency"] = derived_consistency(auto)
        merged.append({**g, "auto_evaluation_record": e, "auto_evaluation": auto})
    with (ROOT / "results" / "answer_eval_merged.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in merged:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    completed = [r for r in merged if r["auto_evaluation_record"]["evaluation_status"] == "COMPLETED"]
    blocked = [r for r in merged if r["auto_evaluation_record"]["evaluation_status"] != "COMPLETED"]
    if blocked:
        raise SystemExit(f"Evaluation incomplete for {[r['question_id'] for r in blocked]}")
    autos = [r["auto_evaluation"] for r in completed]
    total_claims = sum(a["claim_count"] for a in autos)
    unsupported = sum(a["unsupported_claim_count"] for a in autos)
    types = Counter(t for a in autos for t in a["hallucination_types"] if t != "NONE")
    hallucinated_rows = [
        r for r in completed
        if any(t in {"GENERATION_HALLUCINATION", "UNSUPPORTED_INFERENCE", "OVERCONFIDENT_ANSWER"}
               for t in r["auto_evaluation"]["hallucination_types"])
    ]
    metrics = {
        "scope": "PROVISIONAL_AUTO_EVAL",
        "human_validated_metrics": {
            "answer_correctness": None,
            "faithfulness": None,
            "unsupported_claim_rate": None,
            "reason": "Human review is incomplete and the local evaluator is the same small model family as the generator.",
        },
        "questions": 38,
        "generation_completed": len(gen),
        "evaluation_completed": len(completed),
        "answer_correctness_mean_0_to_2": round(sum(a["correctness"] for a in autos) / 38, 4),
        "answer_correctness_normalized": round(sum(a["correctness"] for a in autos) / 76, 4),
        "fully_correct_count": sum(a["correctness"] == 2 for a in autos),
        "faithfulness_mean_0_to_2": round(sum(a["faithfulness"] for a in autos) / 38, 4),
        "faithfulness_normalized": round(sum(a["faithfulness"] for a in autos) / 76, 4),
        "completeness_mean_0_to_2": round(sum(a["completeness"] for a in autos) / 38, 4),
        "citation_correctness_mean_0_to_2": round(sum(a["citation_correctness"] for a in autos) / 38, 4),
        "unsupported_claims": unsupported,
        "total_claims": total_claims,
        "unsupported_claim_rate": round(unsupported / total_claims, 4) if total_claims else 0.0,
        "correct_refusal_count": sum(a["refusal_appropriate"] is True for a in autos),
        "hallucination_answer_count": len(hallucinated_rows),
        "hallucination_type_distribution": dict(types),
        "retrieval_failure_count": types.get("RETRIEVAL_FAILURE", 0),
        "source_quality_failure_count": types.get("SOURCE_QUALITY_FAILURE", 0),
        "retrieval_correct_answer_wrong_count": sum(derived_consistency(a) == "retrieval_correct_answer_wrong" for a in autos),
        "avg_generation_latency_seconds": round(sum(r["latency"]["generation_seconds"] for r in completed) / 38, 4),
        "avg_evaluator_latency_seconds": round(sum(r["auto_evaluation_record"]["evaluator_latency_seconds"] for r in completed) / 38, 4),
        "generation_model": gen[0]["generation_model"],
        "evaluator_model": completed[0]["auto_evaluation_record"]["evaluator_model"],
    }

    smoke_rows = []
    for r in completed[:10]:
        qid = r["question_id"]
        old = smoke_old[qid]
        a = r["auto_evaluation"]
        cur = verdict(a)
        smoke_rows.append(
            {
                "question_id": qid,
                "question": r["question"],
                "rag_v0_result": old["v0_tfidf_result"],
                "rag_v1_dense_result": old["dense_result"],
                "generated_answer": r["generated_answer"],
                "answer_citations": ", ".join(r["answer_citations"]),
                "previous_v0_verdict": old["previous_v0_verdict"],
                "rag_v1_retrieval_verdict": old["v1_verdict"],
                "answer_v0_verdict": cur,
                "change": change(old["previous_v0_verdict"], cur),
                "correctness": a["correctness"],
                "faithfulness": a["faithfulness"],
                "unsupported_claim_rate": round(a["unsupported_claim_count"] / a["claim_count"], 4) if a["claim_count"] else 0.0,
                "citation_correctness": a["citation_correctness"],
                "refusal_appropriate": a["refusal_appropriate"],
                "consistency": derived_consistency(a),
                "hallucination_types": ", ".join(a["hallucination_types"]),
                "error_attribution": (
                    "source" if "SOURCE_QUALITY_FAILURE" in a["hallucination_types"]
                    else "retrieval" if "RETRIEVAL_FAILURE" in a["hallucination_types"]
                    else "generation" if any(t in a["hallucination_types"] for t in ("GENERATION_HALLUCINATION", "UNSUPPORTED_INFERENCE", "CITATION_MISMATCH", "INCOMPLETE_ANSWER"))
                    else "none"
                ),
                "note": a["reason"],
            }
        )
    (ROOT / "results" / "v0_smoke_answer_comparison.json").write_text(
        json.dumps(smoke_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metrics["v0_smoke"] = {
        "previous": dict(Counter(x["previous_v0_verdict"] for x in smoke_rows)),
        "answer_v0": dict(Counter(x["answer_v0_verdict"] for x in smoke_rows)),
        "change": dict(Counter(x["change"] for x in smoke_rows)),
        "retrieval_correct_answer_wrong": sum(x["consistency"] == "retrieval_correct_answer_wrong" for x in smoke_rows),
        "transport_source_gap": next(x for x in smoke_rows if x["question_id"] == "RET-09")["error_attribution"],
    }
    (ROOT / "results" / "final_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    required_sections = {
        "Retrieval 正确但模型仍然答错": lambda a: derived_consistency(a) == "retrieval_correct_answer_wrong",
        "Retrieval 不足但模型正确拒答": lambda a: derived_consistency(a) == "retrieval_insufficient_correct_refusal",
        "Retrieval 不足且模型产生幻觉": lambda a: derived_consistency(a) == "retrieval_insufficient_hallucination",
        "Source Quality Failure": lambda a: "SOURCE_QUALITY_FAILURE" in a["hallucination_types"],
        "Citation Mismatch": lambda a: "CITATION_MISMATCH" in a["hallucination_types"],
        "Unsupported Inference": lambda a: "UNSUPPORTED_INFERENCE" in a["hallucination_types"],
    }
    failure_lines = [
        "# Failure cases", "", "> PROVISIONAL_AUTO_EVAL；案例判读由本地模型与确定性规则生成，待人工复核。", ""
    ]
    for title, pred in required_sections.items():
        matches = [r for r in completed if pred(r["auto_evaluation"])]
        failure_lines += [f"## {title}", ""]
        if not matches:
            failure_lines += ["本轮未观察到可报告案例；未为满足数量而凑例。", ""]
            continue
        for r in matches[:3]:
            a = r["auto_evaluation"]
            failure_lines += [
                f"### {r['question_id']}", "",
                f"- Question：{r['question']}",
                f"- Retrieved evidence：{evidence_preview(r['retrieved_context'])}",
                f"- Answer：{r['generated_answer']}",
                f"- Error diagnosis：{a['reason']}；标签={', '.join(a['hallucination_types'])}", "",
            ]
    (ROOT / "analysis" / "failure_cases.md").write_text("\n".join(failure_lines), encoding="utf-8")

    smoke_counts = metrics["v0_smoke"]
    predominant = "generation constraints" if types.get("CITATION_MISMATCH", 0) + types.get("INCOMPLETE_ANSWER", 0) >= types.get("RETRIEVAL_FAILURE", 0) else "retrieval"
    report = f"""# Answer Generation Evaluation V0 Report

> **PROVISIONAL Answer Generation Evaluation** — Human Audit 尚未完成；本报告不是最终 benchmark。

## 1. 实验目的

在冻结的 RAG V1 Dense Top-5 之上，测量完整 question → retrieval → context → generation → citation → evaluation 链路，区分检索、源数据与生成错误。

## 2. 数据与版本

- Corpus：238 documents / 717 chunks；输入直接复用并校验 RAG V1 冻结文件。
- Evaluation：38 题（10 CONFIRMED Existing Smoke + 28 PROVISIONAL_EVAL）。
- Retriever：`BAAI/bge-small-zh-v1.5`，Dense Top-K=5；未重训 embedding。
- Generator：`Qwen/Qwen2.5-1.5B-Instruct-GGUF`，revision `91cad51170dc346986eccefdc2dd33a9da36ead9`，Q4_K_M，llama.cpp CPU，temperature=0。
- Evaluator：同一模型的本地证据约束判读 + 确定性 citation/source 规则。其分数不是独立 Gold，必须结合人工字段复核。

## 3. Generation pipeline

38 题全部使用冻结 Dense Top-5；每题保存 chunk/document ID、score、完整 context、prompt、answer、citations、token 与时延。回答提示明确禁止外部知识、要求证据不足时拒答、关键事实逐句引用。未调用任何第三方 LLM/API。

## 4. Evaluation methodology

自动指标使用 0/1/2 rubric（正确性、忠实度、完整性、引用正确性）；Unsupported Claim Rate 为自动判定的不支持 claim / 总事实 claim。已知交通题 `RET-09` 与 `PROV-009` 强制优先归因 Source Quality Failure，不因参数调优改写结论。自动判读与生成使用同一小模型，存在自评偏差，因此所有结果标记 `PROVISIONAL_AUTO_EVAL`。

## 5. 总体结果

- Human-validated Answer Correctness / Faithfulness / Unsupported Claim Rate：**N/A**（人工复核未完成）。下列数值仅为同源本地 evaluator 的 provisional proxy。
- 完成：{metrics['generation_completed']}/38 generation，{metrics['evaluation_completed']}/38 auto evaluation。
- Answer Correctness：均值 {metrics['answer_correctness_mean_0_to_2']:.4f}/2（normalized {pct(metrics['answer_correctness_normalized'])}）；fully correct {metrics['fully_correct_count']}/38。
- Faithfulness：均值 {metrics['faithfulness_mean_0_to_2']:.4f}/2（normalized {pct(metrics['faithfulness_normalized'])}）。
- Unsupported Claim Rate：{metrics['unsupported_claims']}/{metrics['total_claims']} = {pct(metrics['unsupported_claim_rate'])}。
- 正确拒答：{metrics['correct_refusal_count']}。
- 含生成型幻觉/不支持推断/过度自信的回答：{metrics['hallucination_answer_count']}。
- Citation Correctness：均值 {metrics['citation_correctness_mean_0_to_2']:.4f}/2；Citation Mismatch {types.get('CITATION_MISMATCH', 0)}。
- 平均生成时延：{metrics['avg_generation_latency_seconds']:.2f}s/query（CPU）。

## 6. V0 smoke 结果

- 原结果：{smoke_counts['previous']}（对应 7 pass / 2 partial / 1 fail）。
- Answer Generation V0：{smoke_counts['answer_v0']}。
- 变化：{smoke_counts['change']}。
- Smoke 中“检索正确但生成错误”：{smoke_counts['retrieval_correct_answer_wrong']}。
- 交通题仍归因：{smoke_counts['transport_source_gap']}；检索排序不能创造 corpus 中不存在的答案。

## 7. 幻觉与 Unsupported Claim

类型分布：{dict(types)}。小模型最突出的问题之一是未稳定遵守逐句 citation 约束；这类输出即使事实可在 context 中找到，也不能视为引用合格。没有为提高数字重跑或挑选输出。

## 8. Retrieval vs Generation 错误归因

- Retrieval Failure：{metrics['retrieval_failure_count']}。
- Source Quality Failure：{metrics['source_quality_failure_count']}。
- Retrieval 正确但 Answer 错误：{metrics['retrieval_correct_answer_wrong_count']}。
- 当前主要风险信号：{predominant}。Dense R@5 不能自动等价为端到端答案正确。

## 9. Source Quality Failure

交通/校车/路线相关题仍缺少充分源资料。生成器必须拒答；任何常识补全都计为过度自信或幻觉。此阶段没有启动新抓取或修改 corpus。

## 10. Failure Cases

逐例见 `analysis/failure_cases.md`，保留 question、evidence、answer 与诊断；缺少的类型明确写“未观察到”，没有凑数。

## 11. 当前局限

1. 28 题为 PROVISIONAL_EVAL；Human Audit 未完成。
2. 自动 evaluator 与 generator 同源且只有 1.5B 参数，可能错判语义支持、完整性与 claim 切分。
3. 只有一套本地生成 baseline；未做模型间比较。
4. 引用格式失败会显著拉低 citation 指标，但不等同于所有事实均错误。

## 12. Human Audit 未完成声明

Human Audit 的五个字段在工作簿中保持空白。本阶段不得作为最终 benchmark，也不得据此修改 production。

## 13. 下一阶段建议（不执行）

优先优化 grounded generation prompt / citation constraint，并在相同 38 题上做一次冻结 A/B；不要先做 SFT。交通类另列 corpus gap，等待 Human Audit 后决定是否补充/清洗。只有在正确 evidence 已到位而生成错误仍稳定复现时，才讨论 SFT 候选实验。
"""
    (ROOT / "answer_eval_v0_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
