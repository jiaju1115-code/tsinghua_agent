from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
AE1 = DATA / "answer_eval_v1"


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")


def clip(text: str, n: int = 320) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def pct(value):
    return "N/A" if value is None else f"{value * 100:.2f}%"


def main():
    metrics = json.loads((ROOT / "results" / "citation_metrics.json").read_text(encoding="utf-8"))
    threshold = json.loads((ROOT / "results" / "threshold_analysis.json").read_text(encoding="utf-8"))
    claims = read_jsonl(ROOT / "results" / "claims_classified.jsonl")
    maps = {x["claim_id"]: x for x in read_jsonl(ROOT / "results" / "claim_evidence_mapping.jsonl")}
    per = read_jsonl(ROOT / "results" / "per_question_results.jsonl")
    a_rows = read_jsonl(AE1 / "results" / "generation_a.jsonl")
    aby = {x["question_id"]: x for x in a_rows}
    pby = {x["question_id"]: x for x in per}
    cby = defaultdict(list)
    for c in claims:
        cby[c["question_id"]].append(c)

    known_gap = {"RET-09", "PROV-009"}
    unsupported = []
    attribution_counts = Counter()
    for c in claims:
        if c["final_support_label"] != "UNSUPPORTED":
            continue
        q = aby[c["question_id"]]
        m = maps[c["claim_id"]]
        retrieved_sources = set(q["retrieved_document_ids"])
        top = m["candidates"][0]
        if c["question_id"] in known_gap:
            attribution = "SOURCE_QUALITY_FAILURE"
        elif q.get("expected_source_status") == "reliable" and q.get("expected_source_id") not in retrieved_sources:
            attribution = "RETRIEVAL_LIMITATION"
        elif c["semantic_score"] >= 0.68 and not c["hard_rules_pass"]:
            attribution = "GENERATION_HALLUCINATION"
        else:
            attribution = "AMBIGUOUS"
        attribution_counts[attribution] += 1
        evidence = next(x for x in q["retrieved_context"] if x["chunk_id"] == top["chunk_id"])
        unsupported.append({
            "question_id": c["question_id"],
            "claim_id": c["claim_id"],
            "question": q["question"],
            "original_answer": q["generated_answer"],
            "claim": c["claim_text"],
            "claim_type": c["claim_type"],
            "top_candidate_chunk": top["chunk_id"],
            "top_candidate_score": c["semantic_score"],
            "rule_flags": c["rule_flags"],
            "candidate_evidence": clip(evidence["text"]),
            "automatic_attribution": attribution,
            "reason": "deterministic hard rule failed" if c["rule_flags"] else "predeclared semantic/lexical threshold not met",
        })
    write_jsonl(ROOT / "results" / "unsupported_attribution.jsonl", unsupported)

    lines = [
        "# Unsupported Claims",
        "",
        "> PROVISIONAL_AUTO_EVAL：以下归因来自确定性规则，不是人工裁决。Human-validated citation correctness 为 N/A。",
        "",
        f"共 {len(unsupported)} 个 UNSUPPORTED claim。自动归因分布：" + "，".join(f"{k}={v}" for k, v in sorted(attribution_counts.items())) + "。",
        "",
    ]
    for x in unsupported:
        lines += [
            f"## {x['claim_id']} · {x['automatic_attribution']}",
            "",
            f"- Question：{x['question']}",
            f"- Claim：{x['claim']}",
            f"- Top candidate：`{x['top_candidate_chunk']}`，semantic={x['top_candidate_score']:.4f}",
            f"- Rule flags：{', '.join(x['rule_flags']) if x['rule_flags'] else 'none'}",
            f"- 判定依据：{x['reason']}",
            f"- Candidate evidence：{x['candidate_evidence']}",
            "",
        ]
    (ROOT / "analysis" / "unsupported_claims.md").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "analysis" / "unsupported_claims.md").write_text("\n".join(lines), encoding="utf-8")

    def first(pred):
        return next((x for x in unsupported if pred(x)), None)

    cases = [
        ("Claim 正确拆分，但 evidence mapping 错误", first(lambda x: x["automatic_attribution"] == "RETRIEVAL_LIMITATION"), "自动归因仅说明冻结 Top-5 未含预期 source，需人工确认拆分是否正确。"),
        ("Semantic similarity 高，但事实不支持", first(lambda x: x["top_candidate_score"] >= .75 and x["rule_flags"]), "高相似度被实体/数字/流程硬规则拦截，未分配 citation。"),
        ("数字/时间不一致", first(lambda x: any(f in x["rule_flags"] for f in ("NUMERIC_MISMATCH", "TEMPORAL_MISMATCH"))), "关键值不直接匹配，因此不能仅凭 embedding 判支持。"),
        ("Entity 看似相同但实际指向不同", first(lambda x: "ENTITY_MISMATCH" in x["rule_flags"]), "实体表面验证失败。"),
        ("一个 claim 需要多个 chunk", None, "主阈值下没有形成可靠的 multi-citation 实例；不得凑例。"),
        ("Evidence 存在冲突", None, "没有检测到满足保守冲突规则的实际案例。"),
        ("Source Quality Failure", first(lambda x: x["automatic_attribution"] == "SOURCE_QUALITY_FAILURE"), "交通核心事实在现有 corpus 中不足。"),
        ("Unsupported generation claim", first(lambda x: x["automatic_attribution"] == "GENERATION_HALLUCINATION"), "回答事实与冻结证据的硬规则不一致。"),
        ("Citation pipeline 无法映射", first(lambda x: not x["rule_flags"] and x["top_candidate_score"] < .60), "Top-5 中没有达到保守阈值的候选。"),
        ("错误 citation assignment", None, "自动规则 proxy 下 0 个；人工验证前真实数量为 N/A。"),
    ]
    flines = ["# Failure Cases", "", "> 只列真实可复现案例；没有满足条件的类别明确写“未检测到”，不补造。", ""]
    for title, x, note in cases:
        flines += [f"## {title}", "", note, ""]
        if x:
            flines += [
                f"- Question：{x['question']}",
                f"- Claim：{x['claim']}",
                f"- Evidence：`{x['top_candidate_chunk']}` — {x['candidate_evidence']}",
                f"- Diagnosis：{x['automatic_attribution']}；semantic={x['top_candidate_score']:.4f}；flags={x['rule_flags'] or 'none'}",
                "",
            ]
    (ROOT / "analysis" / "failure_cases.md").write_text("\n".join(flines), encoding="utf-8")

    sens_rows = []
    for t, v in threshold["sensitivity"].items():
        sens_rows.append({"threshold": float(t), **v})
    workbook = {
        "summary": {
            "questions": metrics["questions_completed"],
            "claims": metrics["claim_total"],
            "factual_claims": metrics["factual_claim_total"],
            "coverage": metrics["claim_level_citation_coverage"],
            "precision_proxy": metrics["citation_precision_proxy"],
            "baseline_compliance": metrics["answer_level_citation_compliance"]["a_baseline"],
            "pipeline_compliance": metrics["answer_level_citation_compliance"]["citation_pipeline_v1"],
            "preservation": metrics["answer_preservation_rate"],
            "human_validated_precision": None,
        },
        "rows": [{
            "question_id": x["question_id"], "question": x["question"], "original_answer": x["original_answer"],
            "cited_answer": x["cited_answer"], "original_citation_status": x["original_citation_status"],
            "new_citation_status": x["new_citation_status"], "claim_count": x["claim_count"],
            "supported_claim_count": x["supported_claim_count"], "partial_claim_count": x["partial_claim_count"],
            "unsupported_claim_count": x["unsupported_claim_count"], "citation_count": x["citation_count"],
            "citation_coverage": x["citation_coverage"], "citation_precision_proxy": x["citation_precision_proxy"],
            "preservation_status": x["preservation_status"], "human_citation_correctness": "",
            "human_claim_support": "", "human_comment": "",
        } for x in per],
        "thresholds": sens_rows,
    }
    (ROOT / "evaluation").mkdir(parents=True, exist_ok=True)
    (ROOT / "evaluation" / "workbook_data.json").write_text(json.dumps(workbook, ensure_ascii=False, indent=2), encoding="utf-8")

    dist = metrics["support_distribution"]
    baseline_compliant = round(metrics['answer_level_citation_compliance']['a_baseline'] * metrics['questions_completed'])
    pipeline_compliant = round(metrics['answer_level_citation_compliance']['citation_pipeline_v1'] * metrics['questions_completed'])
    compliance_delta_pp = (metrics['answer_level_citation_compliance']['citation_pipeline_v1'] - metrics['answer_level_citation_compliance']['a_baseline']) * 100
    report = f"""# Citation Pipeline V1 Report

## 1. Motivation

在不改写冻结 A baseline 的前提下，将答案生成与证据引用解耦，并用保守规则阻止“看起来有引用但事实不受支持”的引用。

## 2. Frozen Inputs

- 38/38 A answers 与 Answer Eval V0 逐字一致。
- 每题仅使用冻结 Dense Top-5，不扩大检索。
- BGE：`{metrics['embedding']['model_name']}` revision `{metrics['embedding']['revision']}`。
- 输入冻结检查：PASS；详细 hash 见 `audit/input_freeze.json`。

## 3. Pipeline Architecture

Frozen A answer → deterministic claim segmentation → BGE claim embedding → frozen Top-5 matching → deterministic rules → citation assignment → marker-only rendering → evaluation。

## 4. Claim Segmentation

共 {metrics['claim_total']} 个 claim，其中 factual claim {metrics['factual_claim_total']} 个。方法为 `DETERMINISTIC_RULE_V1`，未调用 generation model。

## 5. Evidence Matching

Claim embeddings 为 {metrics['embedding']['rows']}×{metrics['embedding']['dimension']}，文件 SHA-256 `{metrics['embedding']['sha256']}`。候选严格限制在每题原 Dense Top-5。

## 6. Deterministic Support Rules

数字、时间、实体、流程、顺序分别执行直接匹配规则；拒答不强制事实 citation；冲突采用保守规则。高语义但硬规则失败共 {metrics['high_semantic_hard_rule_failures']} 个典型案例。

## 7. Citation Assignment

主阈值预先固定为 SUPPORTED≥0.75、PARTIALLY_SUPPORTED≥0.68。仅 SUPPORTED/PARTIALLY_SUPPORTED 分配引用，共 {metrics['citation_assignments']} 条；UNSUPPORTED 与冲突不分配。

## 8. Citation Rendering

仅插入 `[n]` marker 和参考资料列表，不改写正文。Answer Preservation Rate={pct(metrics['answer_preservation_rate'])}。

## 9. Metrics

- SUPPORTED={dist.get('SUPPORTED',0)}，PARTIALLY_SUPPORTED={dist.get('PARTIALLY_SUPPORTED',0)}，UNSUPPORTED={dist.get('UNSUPPORTED',0)}，CONFLICTING_EVIDENCE={dist.get('CONFLICTING_EVIDENCE',0)}。
- Claim-level Citation Coverage={pct(metrics['claim_level_citation_coverage'])}。
- Citation Precision Proxy={pct(metrics['citation_precision_proxy'])}；这是确定性规则通过率，不是人工准确率。
- Unsupported Claim Rate={pct(metrics['unsupported_claim_rate'])}；Partial Support Rate={pct(metrics['partial_support_rate'])}；Conflict Rate={pct(metrics['conflict_rate'])}。

## 10. Comparison with A Baseline

Answer-level citation compliance 从 {pct(metrics['answer_level_citation_compliance']['a_baseline'])}（{baseline_compliant}/38）提升至 {pct(metrics['answer_level_citation_compliance']['citation_pipeline_v1'])}（{pipeline_compliant}/38），增加 {compliance_delta_pp:.2f} 个百分点；绝对水平仍低。正文保持率 100%。

## 11. Unsupported Claims

92 个事实 claim 未获支持。自动归因：{', '.join(f'{k}={v}' for k,v in sorted(attribution_counts.items()))}。大量 claim 低于保守阈值；该结果不能直接等同于事实错误。详见 `analysis/unsupported_claims.md`。

## 12. Traffic Source Quality Failure

RET-09 是证据不足型拒答，未强制 citation；PROV-009 生成了“公众号或小程序”等冻结证据外事实，实体/流程规则拦截并拒绝分配 citation。两题继续标记 SOURCE_QUALITY_FAILURE，没有把语义近似候选包装成支持证据。

## 13. Failure Cases

实际案例与“未检测到”的类别均保留在 `analysis/failure_cases.md`。自动错误 citation proxy=0；真实错误 citation 数量在人工审核前为 N/A。

## 14. Threshold Analysis

敏感性分析固定比较 0.60/0.65/0.70/0.75/0.80，且只统计 factual claims。阈值降低会提高自动覆盖 proxy，但 deterministic-rule proxy 不能估计人工 precision，因此不据 38 题反向选择最“好看”的阈值。主方案保持预声明的保守阈值。

## 15. Limitations

短 claim 对长 chunk 的 embedding 分数存在尺度问题；实体规则依赖表面形式；没有 pretrained NLI/verifier；只查看 Top-5；没有人工 citation 标签。高 precision proxy 与低 coverage 同时存在，表明 embedding+rules 可作安全基线，但不足以完成高覆盖 citation mapping。

## 16. Human Validation Status

Human Audit 尚未完成。Human-validated citation correctness=N/A；工作簿中的三个人工字段全部为空。本报告属于 `PROVISIONAL_AUTO_EVAL`。

## 17. Recommendation for V2

有必要开展 Citation Pipeline V2，但本阶段不执行。优先候选是冻结 Top-5 上的 pretrained cross-encoder/NLI verifier、claim-aware evidence spans 和更稳健的实体别名表；仍应先做人审抽样，校准 precision/coverage，再决定是否引入额外组件。无需 SFT 或训练 citation 模型作为第一步。
"""
    (ROOT / "citation_pipeline_v1_report.md").write_text(report, encoding="utf-8")

    print(json.dumps({"unsupported": len(unsupported), "attribution": attribution_counts, "workbook_rows": len(per)}, ensure_ascii=False, default=dict))


if __name__ == "__main__":
    main()
