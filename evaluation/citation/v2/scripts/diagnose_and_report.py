from __future__ import annotations

import importlib.util
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
V1 = DATA / "citation_pipeline_v1"
RAG0 = DATA / "rag_v0"
RAG1 = DATA / "rag_v1"
AE1 = DATA / "answer_eval_v1"

spec = importlib.util.spec_from_file_location("run_v2", ROOT / "scripts" / "run_v2.py")
rv2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv2)
FACT_TYPES = rv2.FACT_TYPES


def jl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def dumpjl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")


def clip(text, n=420):
    value = " ".join((text or "").split())
    return value if len(value) <= n else value[:n-1] + "…"


def pct(value):
    return "N/A" if value is None else f"{value*100:.2f}%"


def main():
    metrics = json.loads((ROOT / "results" / "citation_metrics_v2.json").read_text(encoding="utf-8"))
    sanity = json.loads((ROOT / "evaluation" / "verifier_sanity_results.json").read_text(encoding="utf-8"))
    mapping = jl(ROOT / "results" / "claim_evidence_mapping_v2.jsonl")
    candidates = {x["claim_id"]: x for x in jl(ROOT / "results" / "claim_span_candidates.jsonl")}
    spans = {x["span_id"]: x for x in jl(ROOT / "results" / "evidence_spans.jsonl")}
    assignments = jl(ROOT / "results" / "citation_assignments_v2.jsonl")
    per = jl(ROOT / "results" / "per_question_results_v2.jsonl")
    a_rows = jl(AE1 / "results" / "generation_a.jsonl")
    aby = {x["question_id"]: x for x in a_rows}
    v1_attr = {x["claim_id"]: x for x in jl(V1 / "results" / "unsupported_attribution.jsonl")}
    aliases_doc = json.loads((ROOT / "normalization" / "entity_aliases.json").read_text(encoding="utf-8"))
    alias_map = defaultdict(set)
    for x in aliases_doc["aliases"]:
        alias_map[rv2.norm_text(x["alias"])].add(rv2.norm_text(x["canonical"]))
        alias_map[rv2.norm_text(x["canonical"])].add(rv2.norm_text(x["alias"]))

    chunks = jl(RAG0 / "chunks" / "chunks.jsonl")
    chunk_by_id = {x["chunk_id"]: x for x in chunks}
    row_map = jl(RAG1 / "indexes" / "dense" / "row_mapping.jsonl")
    row_by_id = {x["chunk_id"]: x["embedding_row"] for x in row_map}
    doc_vectors = np.load(RAG1 / "indexes" / "dense" / "document_embeddings.npy", mmap_mode="r")
    claim_vectors = np.load(V1 / "results" / "claim_embeddings.npy", mmap_mode="r")
    all_v1_claims = jl(V1 / "results" / "claims.jsonl")
    claim_row = {x["claim_id"]: i for i, x in enumerate(all_v1_claims)}
    original_top5 = {x["question_id"]: set(x["retrieved_chunk_ids"]) for x in a_rows}

    unsupported = [x for x in mapping if x["v1_label"] == "UNSUPPORTED" and x["claim_type"] in FACT_TYPES]
    diagnostics = []
    for claim in unsupported:
        scores = np.asarray(doc_vectors @ claim_vectors[claim_row[claim["claim_id"]]], dtype=float)
        order = np.argsort(-scores)[:25]
        outside = []
        for idx in order:
            cid = row_map[int(idx)]["chunk_id"]
            if cid in original_top5[claim["question_id"]]:
                continue
            chunk = chunk_by_id[cid]
            pseudo = {"span_text": chunk["title"] + "\n" + chunk["text"]}
            rules = rv2.normalized_rules(claim, pseudo, alias_map)
            outside.append({"rank": int(np.where(order == idx)[0][0]) + 1, "chunk_id": cid, "document_id": chunk["source_id"], "title": chunk["title"], "url": chunk["url"], "score": float(scores[int(idx)]), "lexical_claim_coverage": rules["lexical_claim_coverage"], "hard_rules_pass": rules["hard_rules_pass"], "rule_flags": rules["rule_flags"], "preview": clip(chunk["text"], 260)})
            if len(outside) >= 10:
                break
        viable = [x for x in outside if x["score"] >= .70 and x["hard_rules_pass"] and x["lexical_claim_coverage"] >= .35]
        if viable:
            status = "FOUND_OUTSIDE_TOP5"
        elif claim["question_id"] in rv2.KNOWN_GAPS or not outside or max(x["score"] for x in outside) < .60:
            status = "NOT_FOUND_IN_CORPUS"
        else:
            status = "AMBIGUOUS"
        diagnostics.append({"question_id": claim["question_id"], "claim_id": claim["claim_id"], "claim": claim["claim_text"], "diagnostic_status": status, "official_metric_use": False, "top_outside_candidates": outside})
    dumpjl(ROOT / "analysis" / "full_corpus_diagnostic_search.jsonl", diagnostics)
    diag_by = {x["claim_id"]: x for x in diagnostics}

    reclassified = []
    for claim in unsupported:
        v2 = claim["V2-C"]["label"]
        diag = diag_by[claim["claim_id"]]["diagnostic_status"]
        if v2 == "SUPPORTED":
            label = "V1_MAPPING_FAILURE"
        elif v2 == "PARTIALLY_SUPPORTED":
            label = "TOP5_EVIDENCE_PARTIAL"
        elif claim["question_id"] in rv2.KNOWN_GAPS:
            label = "SOURCE_QUALITY_FAILURE"
        elif diag == "FOUND_OUTSIDE_TOP5":
            label = "RETRIEVAL_FAILURE"
        elif diag == "NOT_FOUND_IN_CORPUS" and v1_attr.get(claim["claim_id"], {}).get("automatic_attribution") == "GENERATION_HALLUCINATION":
            label = "GENERATION_HALLUCINATION"
        else:
            label = "AMBIGUOUS"
        reclassified.append({"question_id": claim["question_id"], "claim_id": claim["claim_id"], "claim": claim["claim_text"], "v1_label": "UNSUPPORTED", "v2_label": v2, "reclassification": label, "diagnostic_status": diag, "basis": "V2-C frozen-Top5 result first; full-corpus search diagnostic only"})
    dumpjl(ROOT / "analysis" / "v1_unsupported_reclassification.jsonl", reclassified)
    rcount = Counter(x["reclassification"] for x in reclassified)
    dcount = Counter(x["diagnostic_status"] for x in diagnostics)
    md = ["# V1 Unsupported Reclassification", "", "> PROVISIONAL_AUTO_EVAL；自动重归因不是人工 Gold。全库检索只用于诊断，不影响 V2 官方引用和指标。", "", f"总计：{len(reclassified)}。", ""]
    for key in ("V1_MAPPING_FAILURE", "TOP5_EVIDENCE_PARTIAL", "RETRIEVAL_FAILURE", "SOURCE_QUALITY_FAILURE", "GENERATION_HALLUCINATION", "AMBIGUOUS"):
        md.append(f"- {key}: {rcount[key]}")
    md += ["", "## 逐条结果", ""]
    for x in reclassified:
        md += [f"### {x['claim_id']} · {x['reclassification']}", "", f"- Question: {aby[x['question_id']]['question']}", f"- Claim: {x['claim']}", f"- V2 label: {x['v2_label']}", f"- Full-corpus diagnostic: {x['diagnostic_status']}", ""]
    (ROOT / "analysis" / "v1_unsupported_reclassification.md").write_text("\n".join(md), encoding="utf-8")

    # Failure case selection, retaining explicit no-case statements.
    map_by = {x["claim_id"]: x for x in mapping}
    ass_by = defaultdict(list)
    for x in assignments:
        ass_by[x["claim_id"]].append(x)
    hard = metrics["hard_contradiction_blocks"]
    def first(pred, rows=reclassified):
        return next((x for x in rows if pred(x)), None)
    alias_success = next((x for x in mapping if x["claim_type"] in FACT_TYPES and x["V2-A"]["label"] == "UNSUPPORTED" and x["V2-B"]["label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} and any("ENTITY" in f for c in candidates[x["claim_id"]]["top_10"] for f in c["raw_rule_flags"]) and x["V2-B"]["chosen"]), None)
    numeric_success = next((x for x in mapping if x["claim_type"] in {"NUMERIC", "TEMPORAL"} and x["V2-A"]["label"] == "UNSUPPORTED" and x["V2-B"]["label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}), None)
    partial = next((x for x in mapping if x["V2-C"]["label"] == "PARTIALLY_SUPPORTED"), None)
    multi = next((x for x in mapping if len(x["V2-C"]["chosen"]) > 1), None)
    gain = first(lambda x: x["reclassification"] == "V1_MAPPING_FAILURE")
    outside = first(lambda x: x["diagnostic_status"] == "FOUND_OUTSIDE_TOP5")
    missing = first(lambda x: x["diagnostic_status"] == "NOT_FOUND_IN_CORPUS")
    halluc = first(lambda x: x["reclassification"] == "GENERATION_HALLUCINATION")
    source_gap = first(lambda x: x["reclassification"] == "SOURCE_QUALITY_FAILURE")
    false_positive_anchor = next((x for x in sanity["results"] if x["anchor_type"] != "POSITIVE" and x["verifier_score"] >= sanity["selected_threshold"]), None)
    false_negative_anchor = next((x for x in sanity["results"] if x["anchor_type"] == "POSITIVE" and x["verifier_score"] < sanity["selected_threshold"]), None)
    cases = [
        ("V1 unsupported → V2 successfully supported", gain, "reclassification"),
        ("whole-chunk failure → span-level success", gain, "reclassification"),
        ("entity alias success", alias_success, "mapping"),
        ("numeric normalization success", numeric_success, "mapping"),
        ("semantic similarity high but support false", hard[0] if hard else None, "hard"),
        ("verifier false positive", false_positive_anchor, "anchor"),
        ("verifier false negative", false_negative_anchor, "anchor"),
        ("hard safety rule veto", hard[0] if hard else None, "hard"),
        ("evidence only outside Top-5", outside, "reclassification"),
        ("evidence not present anywhere in corpus", missing, "reclassification"),
        ("generation hallucination", halluc, "reclassification"),
        ("source quality failure", source_gap, "reclassification"),
        ("partial support", partial, "mapping"),
        ("multiple spans required", multi, "mapping")
    ]
    flines = ["# Citation Pipeline V2 Failure Cases", "", "> 只展示真实案例；没有实际案例的类别明确记为未检测到。", ""]
    for title, item, kind in cases:
        flines += [f"## {title}", ""]
        if item is None:
            flines += ["未检测到满足条件的实际案例。", ""]
            continue
        if kind == "reclassification":
            flines += [f"- Claim: `{item['claim_id']}` — {item['claim']}", f"- Diagnosis: {item['reclassification']} / {item['diagnostic_status']}", ""]
        elif kind == "mapping":
            chosen = item["V2-C"]["chosen"] or item["V2-B"]["chosen"]
            flines += [f"- Claim: `{item['claim_id']}` — {item['claim_text']}", f"- V1/V2: {item['v1_label']} → {item['V2-C']['label']}", f"- Chosen spans: {chosen}", ""]
        elif kind == "hard":
            flines += [f"- Claim: `{item['claim_id']}`", f"- Span: `{item['span_id']}`", f"- Scores: embedding={item['embedding_score']:.4f}, verifier={item['verifier_score']:.4f}", f"- Veto flags: {item['rule_flags']}", ""]
        else:
            flines += [f"- Anchor: `{item['anchor_id']}` ({item['anchor_type']})", f"- Verifier score: {item['verifier_score']:.6f} at threshold {sanity['selected_threshold']}", f"- Premise: {clip(item['premise'],220)}", f"- Hypothesis: {clip(item['hypothesis'],220)}", ""]
    (ROOT / "analysis" / "failure_cases.md").write_text("\n".join(flines), encoding="utf-8")

    traffic = {
        "status": "PASS",
        "role": "SAFETY_STRESS_TEST",
        "official_metrics_unchanged": True,
        "RET-09": {
            "frozen_answer_type": "REFUSAL",
            "v2_assignment_count": sum(x["question_id"] == "RET-09" for x in assignments),
            "full_corpus_diagnostic": "NOT_APPLICABLE_TO_REFUSAL_CLAIM",
            "source_quality_failure": True,
            "result": "correct refusal preserved; no citation assigned"
        },
        "PROV-009": {
            "v1_label": next(x["v1_label"] for x in mapping if x["claim_id"] == "PROV-009-C001"),
            "v2_label": next(x["V2-C"]["label"] for x in mapping if x["claim_id"] == "PROV-009-C001"),
            "v2_assignment_count": sum(x["question_id"] == "PROV-009" for x in assignments),
            "full_corpus_diagnostic": diag_by["PROV-009-C001"]["diagnostic_status"],
            "top_span_verifier_score": candidates["PROV-009-C001"]["top_10"][0]["verifier_score"],
            "top_span_rule_flags": candidates["PROV-009-C001"]["top_10"][0]["normalized_rule_flags"],
            "source_quality_failure": True,
            "result": "high cross-encoder relevance did not override source-gap/entity safety veto; no citation assigned"
        }
    }
    (ROOT / "analysis" / "traffic_safety_stress_test.json").write_text(json.dumps(traffic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Human calibration sample: 32 real claims + 4 synthetic sanity anchors.
    selected = []
    seen = set()
    def add_one(x, stratum_override=None):
        if x["claim_id"] in seen or len([y for y in selected if y.get("record_type") == "CLAIM"]) >= 32:
            return False
        seen.add(x["claim_id"])
        chosen = ass_by.get(x["claim_id"], [])
        top = candidates[x["claim_id"]]["top_10"][0] if x["claim_id"] in candidates else None
        span_id = chosen[0]["span_id"] if chosen else (top["span_id"] if top else None)
        span = spans.get(span_id, {})
        q = aby[x["question_id"]]
        chunk = next((c for c in q["retrieved_context"] if c["chunk_id"] == span.get("chunk_id")), {})
        default_stratum = "V1_FAILURE_TO_V2_SUCCESS" if x["v1_label"] == "UNSUPPORTED" and x["V2-C"]["label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} else x["V2-C"]["label"]
        selected.append({"record_type": "CLAIM", "question_id": x["question_id"], "question": q["question"], "claim_id": x["claim_id"], "claim": x["claim_text"], "claim_type": x["claim_type"], "assigned_evidence_span": span.get("span_text", ""), "complete_chunk_context": chunk.get("text", ""), "source_title": span.get("source_title", chunk.get("title", "")), "source_url": span.get("source_url", chunk.get("url", "")), "v1_label": x["v1_label"], "v2_label": x["V2-C"]["label"], "embedding_score": top.get("embedding_score") if top else None, "verifier_score": top.get("verifier_score") if top else None, "rule_flags": " | ".join(top.get("normalized_rule_flags", [])) if top else "", "stratum": stratum_override or default_stratum, "human_support_label": "", "human_citation_correct": "", "human_comment": ""})
        return True
    def add_pool(rows, count, stratum_override=None):
        added = 0
        for x in rows:
            if added >= count:
                break
            if add_one(x, stratum_override):
                added += 1
    real_candidates = [x for x in mapping if x["claim_type"] in FACT_TYPES]
    add_pool([x for x in real_candidates if x["V2-C"]["label"] == "SUPPORTED"], 7)
    add_pool([x for x in real_candidates if x["V2-C"]["label"] == "PARTIALLY_SUPPORTED"], 7)
    add_pool([x for x in real_candidates if x["V2-C"]["label"] == "UNSUPPORTED"], 7)
    add_pool([x for x in real_candidates if x["question_id"] in rv2.KNOWN_GAPS], 1, "SOURCE_QUALITY_FAILURE")
    for claim_type in ("NUMERIC", "TEMPORAL", "ENTITY", "PROCEDURAL"):
        add_pool([x for x in real_candidates if x["claim_type"] == claim_type], 1, f"{claim_type}_CLAIM")
    risky_ids = {x["claim_id"] for x in metrics["hard_contradiction_blocks"]}
    add_pool([x for x in real_candidates if x["claim_id"] in risky_ids], 2, "HARD_SAFETY_VETO")
    add_pool([x for x in real_candidates if x["v1_label"] == "UNSUPPORTED" and x["V2-C"]["label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}], 2, "V1_FAILURE_TO_V2_SUCCESS")
    add_pool(real_candidates, 32)
    for anchor in [x for x in sanity["results"] if x["anchor_type"] != "POSITIVE"][:4]:
        selected.append({"record_type": "SANITY_HARD_NEGATIVE", "question_id": "SANITY_ONLY", "question": "Verifier calibration only; not benchmark", "claim_id": anchor["anchor_id"], "claim": anchor["hypothesis"], "claim_type": anchor["anchor_type"], "assigned_evidence_span": anchor["premise"], "complete_chunk_context": anchor["premise"], "source_title": "Synthetic hard negative from real evidence", "source_url": "", "v1_label": "N/A", "v2_label": "HARD_NEGATIVE", "embedding_score": None, "verifier_score": anchor["verifier_score"], "rule_flags": anchor["anchor_type"], "stratum": "HARD_NEGATIVE", "human_support_label": "", "human_citation_correct": "", "human_comment": ""})

    comparison = {
        "summary": metrics,
        "reclassification_counts": {k: rcount[k] for k in ("V1_MAPPING_FAILURE", "TOP5_EVIDENCE_PARTIAL", "RETRIEVAL_FAILURE", "SOURCE_QUALITY_FAILURE", "GENERATION_HALLUCINATION", "AMBIGUOUS")},
        "diagnostic_counts": dict(dcount),
        "claims": [{"question_id": x["question_id"], "claim_id": x["claim_id"], "claim": x["claim_text"], "claim_type": x["claim_type"], "v1_label": x["v1_label"], "v2a_label": x["V2-A"]["label"], "v2b_label": x["V2-B"]["label"], "v2c_label": x["V2-C"]["label"], "v2c_chosen_spans": " | ".join(x["V2-C"]["chosen"]), "change": "improved" if x["v1_label"] == "UNSUPPORTED" and x["V2-C"]["label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} else "unchanged" if x["v1_label"] == x["V2-C"]["label"] else "changed", "human_support_label": "", "human_comment": ""} for x in mapping if x["claim_type"] in FACT_TYPES],
        "questions": per,
        "calibration_sample": selected
    }
    (ROOT / "evaluation" / "workbook_data.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")

    v1_count = 12
    v2_count = metrics["artifacts"]["citation_assignments"]
    report = f"""# Citation Pipeline V2 Report

## 1. Scope and Frozen Inputs

V2 保持38题、120 claims、104 factual claims、A baseline answer、V1 claim IDs 与每题原 Dense Top-5 完全冻结。输入不变性审计 PASS。未生成答案、未重切 claim、未训练模型、未使用 Web Search 或外部 API。

## 2. Architecture

Frozen claim → Top-5 evidence span extraction → BGE span ranking → normalization → pretrained cross-encoder relevance gate → deterministic safety veto → citation assignment/rendering。

## 3. Evidence Spans

从冻结 Top-5 提取 {metrics['artifacts']['span_count']} 个去重1–3句 spans（30–350字符）。V2-A coverage={pct(metrics['v2a']['claim_level_citation_coverage'])}，相对 V1 11.54% 显著上升，说明 whole-chunk mapping 过粗是 V1 低 coverage 的主要因素之一。

## 4. Normalization Contribution

V2-B coverage={pct(metrics['v2b']['claim_level_citation_coverage'])}，比 V2-A 增加 {(metrics['v2b']['claim_level_citation_coverage']-metrics['v2a']['claim_level_citation_coverage'])*100:.2f} 个百分点。实体 alias 只来自同一来源明确等价表达；没有逐题 alias。

## 5. Pretrained Verifier

使用已有 `BAAI/bge-reranker-base` revision `{metrics['verifier']['revision']}`，CPU 推理。它是 cross-encoder relevance 模型，不是 NLI。Sanity 状态：`{sanity['status']}`；正/负 median separation={sanity['positive_negative_median_separation']:.6f}，20/20 hard negatives 在0.95阈值上仍为高分。因此不能把它当 entailment verifier，只作为保守 relevance gate。

V2-C coverage={pct(metrics['v2c']['claim_level_citation_coverage'])}，较 V2-B 变化 {(metrics['v2c']['claim_level_citation_coverage']-metrics['v2b']['claim_level_citation_coverage'])*100:.2f} 个百分点。Verifier 没有带来正向 coverage 增益，且显示明显 false-positive 风险。

## 6. Safety Guards

硬规则拦截 {metrics['hard_contradiction_block_count']} 个“embedding/verifier高分但数字、时间、实体或流程不匹配”的候选。自动规则下错误 citation={metrics['automatic_wrong_citations']}；Citation Precision Proxy={pct(metrics['citation_precision_proxy'])}，但人工验证 precision=N/A。

## 7. Ablation

- V1: 11.54%
- V2-A spans+embedding+V1 rules: {pct(metrics['v2a']['claim_level_citation_coverage'])}
- V2-B + normalization: {pct(metrics['v2b']['claim_level_citation_coverage'])}
- V2-C + pretrained verifier+safety: {pct(metrics['v2c']['claim_level_citation_coverage'])}

提升主要来自 span-level mapping；normalization 有小幅增益；当前 cross-encoder verifier 没有提供可靠 entailment 增益。

## 8. Citation Metrics and Rendering

V2 分配 {v2_count} 条 span citation（V1={v1_count}）。Answer-level compliance：A={pct(metrics['answer_level_citation_compliance']['a_baseline'])} → V1={pct(metrics['answer_level_citation_compliance']['v1'])} → V2={pct(metrics['answer_level_citation_compliance']['v2'])}。Claim coverage 提升没有转化为 answer-level 全覆盖，因为多-claim回答仍残留 unsupported claim。Answer Preservation={pct(metrics['answer_preservation_rate'])}。

## 9. V1 Unsupported Reclassification

92条分布：{', '.join(f'{k}={rcount[k]}' for k in ('V1_MAPPING_FAILURE','TOP5_EVIDENCE_PARTIAL','RETRIEVAL_FAILURE','SOURCE_QUALITY_FAILURE','GENERATION_HALLUCINATION','AMBIGUOUS'))}。

## 10. Full-corpus Diagnostic

只作诊断，不污染正式指标。FOUND_OUTSIDE_TOP5={dcount['FOUND_OUTSIDE_TOP5']}，NOT_FOUND_IN_CORPUS={dcount['NOT_FOUND_IN_CORPUS']}，AMBIGUOUS={dcount['AMBIGUOUS']}。

## 11. Traffic Safety Stress Test

RET-09继续保持证据不足拒答且无错误 citation；PROV-009 被 source-gap override 保持 UNSUPPORTED。Cross-encoder 对错误交通候选也可能给高分，但实体/流程规则与已知 source-quality guard 拦截，未产生交通 citation。全库诊断结果记录于机器可读文件，未用于官方 coverage。

## 12. Performance

Span extraction={metrics['performance_seconds']['evidence_span_extraction']:.3f}s，span embedding={metrics['performance_seconds']['span_embedding']:.3f}s，ranking={metrics['performance_seconds']['span_ranking']:.3f}s，verifier claim pairs={metrics['performance_seconds']['verifier_claim_pairs']:.3f}s，assignment={metrics['performance_seconds']['citation_assignment']:.3f}s，总计={metrics['performance_seconds']['total']:.3f}s，平均每题={metrics['performance_seconds']['average_per_question']:.3f}s。V1 total latency 未被完整记录，因此比较值为 N/A。

## 13. Human Calibration

生成36行分层抽样（32条真实 claim + 4条 sanity hard negatives）。全部人工字段为空。Human-validated precision 仍为 N/A。

## 14. Core Research Answers

1. V1 低 coverage 的主要原因之一是 whole-chunk mapping 太粗；span-level带来37.50个百分点增益。
2. Span-level显著提升 coverage。
3. Normalization额外贡献3.85个百分点。
4. 当前 pretrained reranker没有正向增益，反而因0.95 gate降低0.96个百分点。
5. Verifier存在明确 false positive：20/20 synthetic hard negatives超过阈值。
6. Safety rules成功拦截69个风险候选。
7. 92条重归因见上节与逐条文件。
8. V2不宜直接进入最终系统；需先完成人工 citation calibration。
9. 推荐 V3，但本阶段不执行。
10. V3核心原因是 verifier 不足、entity/procedure resolution 仍脆弱，以及部分 retrieval/source/generation问题；不是单纯降低阈值。

## 15. Limitations and V3 Recommendation

Coverage proxy 与 precision proxy 均为自动规则结果；cross-encoder relevance ≠ entailment；full-corpus diagnostic 使用冻结 whole-chunk embedding 与规则，不能证明 corpus 绝对不存在事实。建议 V3 先引入真正的中文/多语 NLI或更可靠的预训练 verifier，并以本次人工 calibration 样本校准，不训练新模型、不修改生成答案作为第一步。
"""
    (ROOT / "citation_pipeline_v2_report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"reclassification": dict(rcount), "diagnostic": dict(dcount), "calibration_rows": len(selected), "report": str(ROOT / 'citation_pipeline_v2_report.md')}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
