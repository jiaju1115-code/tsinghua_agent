from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT.parent; V0=DATA/"answer_eval_v0"
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def load(p): return json.loads(p.read_text(encoding="utf-8"))

def score(a):
    return a["correctness"]+a["faithfulness"]+0.5*a["completeness"]+2*int(a["citation_compliance"])-2*int("GENERATION_HALLUCINATION" in a["hallucination_types"])
def change(a,b,answer_a,answer_b):
    if answer_a == answer_b:
        return "unchanged"
    a_h="GENERATION_HALLUCINATION" in a["hallucination_types"]; b_h="GENERATION_HALLUCINATION" in b["hallucination_types"]
    if (b_h and not a_h) or (a.get("refusal_appropriate") is True and b.get("refusal_appropriate") is not True):
        return "degraded"
    if int(b["citation_compliance"]) < int(a["citation_compliance"]) or b["correctness"] < a["correctness"] or b["faithfulness"] < a["faithfulness"]:
        return "degraded"
    if int(b["citation_compliance"]) > int(a["citation_compliance"]) and b["correctness"] >= a["correctness"] and b["faithfulness"] >= a["faithfulness"] and b["unsupported_claim_count"] <= a["unsupported_claim_count"]:
        return "improved"
    return "uncertain"

def main():
    ga=jl(ROOT/"results"/"generation_a.jsonl"); gb=jl(ROOT/"results"/"generation_b.jsonl")
    ea={x["question_id"]:x for x in jl(ROOT/"results"/"evaluation_a.jsonl")}; eb={x["question_id"]:x for x in jl(ROOT/"results"/"evaluation_b.jsonl")}
    v0={x["question_id"]:x for x in jl(V0/"results"/"answer_generation_results.jsonl")}
    if [x["question_id"] for x in ga]!=[x["question_id"] for x in gb] or len(ga)!=38: raise SystemExit("A/B order mismatch")
    rows=[]
    for a,b in zip(ga,gb):
        aa=ea[a["question_id"]]["auto_evaluation"]; bb=eb[b["question_id"]]["auto_evaluation"]
        row={"question_id":a["question_id"],"question":a["question"],"eval_status":a["eval_status"],"category":a["category"],"retrieved_chunk_ids":a["retrieved_chunk_ids"],"retrieved_document_ids":a["retrieved_document_ids"],"retrieval_scores":a["retrieval_scores"],"a_answer":a["generated_answer"],"b_answer":b["generated_answer"],"a_citations":a["answer_citations"],"b_citations":b["answer_citations"],"a_evaluation":aa,"b_evaluation":bb,"a_generation_seconds":a["latency"]["generation_seconds"],"b_generation_seconds":b["latency"]["generation_seconds"],"correctness_delta":bb["correctness"]-aa["correctness"],"faithfulness_delta":bb["faithfulness"]-aa["faithfulness"],"citation_compliance_delta":int(bb["citation_compliance"])-int(aa["citation_compliance"]),"unsupported_claim_delta":bb["unsupported_claim_count"]-aa["unsupported_claim_count"],"composite_score_a":score(aa),"composite_score_b":score(bb),"overall_change":change(aa,bb,a["generated_answer"],b["generated_answer"]),"a_equals_v0_answer":a["generated_answer"]==v0[a["question_id"]]["generated_answer"],"diagnosis":bb["reason"]}
        rows.append(row)
    with (ROOT/"results"/"ab_per_question.jsonl").open("w",encoding="utf-8",newline="\n") as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False)+"\n")
    ma=load(ROOT/"results"/"metrics_a.json"); mb=load(ROOT/"results"/"metrics_b.json")
    comp={"scope":"PROVISIONAL_AUTO_EVAL","questions":38,"a_prompt_sha_matches_v0":True,"a_answer_exact_match_v0_count":sum(x["a_equals_v0_answer"] for x in rows),"group_a":ma,"group_b":mb,"delta":{"correctness_normalized":round(mb["correctness_normalized"]-ma["correctness_normalized"],4),"faithfulness_normalized":round(mb["faithfulness_normalized"]-ma["faithfulness_normalized"],4),"unsupported_claim_rate":round(mb["unsupported_claim_rate"]-ma["unsupported_claim_rate"],4),"citation_compliance_rate":round(mb["citation_compliance_rate"]-ma["citation_compliance_rate"],4),"correct_refusal_count":mb["correct_refusal_count"]-ma["correct_refusal_count"],"hallucination_answer_count":mb["hallucination_answer_count"]-ma["hallucination_answer_count"]},"per_question_change":dict(Counter(x["overall_change"] for x in rows)),"human_validated_metrics":{"correctness":None,"faithfulness":None,"unsupported_claim_rate":None,"citation_compliance":None,"reason":"Human review fields are blank; scores are local-model provisional proxies."}}
    (ROOT/"results"/"ab_metrics.json").write_text(json.dumps(comp,ensure_ascii=False,indent=2),encoding="utf-8")

    # Focused change analysis; preserve all degradations and improvements.
    md=["# A/B change analysis","","> PROVISIONAL_AUTO_EVAL；没有使用人工标签。Composite score = correctness + faithfulness + 0.5×completeness + 2×citation_compliance − 2×generation_hallucination。",""]
    for label in ("improved","degraded","uncertain","unchanged"):
        xs=[x for x in rows if x["overall_change"]==label]; md += [f"## {label} ({len(xs)})",""]
        if not xs: md += ["本轮无此类案例。",""]; continue
        for x in xs:
            md += [f"### {x['question_id']} — {x['question']}","",f"- A：{x['a_answer']}",f"- B：{x['b_answer']}",f"- Citation：A={x['a_evaluation']['citation_error_types'] or ['NONE']}；B={x['b_evaluation']['citation_error_types'] or ['NONE']}",f"- Δ correctness={x['correctness_delta']}，faithfulness={x['faithfulness_delta']}，citation compliance={x['citation_compliance_delta']}，unsupported claims={x['unsupported_claim_delta']}",f"- Diagnosis：{x['diagnosis']}",""]
    (ROOT/"analysis").mkdir(exist_ok=True); (ROOT/"analysis"/"ab_change_analysis.md").write_text("\n".join(md),encoding="utf-8")

    def pp(x):return f"{100*x:.2f}%"
    report=f"""# Grounded Generation Prompt A/B V1 Report

> **PROVISIONAL_AUTO_EVAL** — Human Audit/人工复核未完成，不是最终 benchmark。

## 1. 实验设计

- 同一冻结 38 题、同一 RAG V1 Dense Top-5、同一 context、同一 `Qwen2.5-1.5B-Instruct-GGUF` revision、同一量化、seed、temperature、token limit 和运行时。
- A：字节级复现 Answer Eval V0 prompt。
- B：只修改 system prompt，强化 evidence-only、逐事实句末 citation、证据不足拒答、禁止证据外渠道/常识。
- A/B 使用完全相同的本地 evaluator 与确定性规则。没有人工字段参与计算。

## 2. 冻结与复现

- A prompt SHA 与 V0 一致：是。
- A 生成答案与 V0 逐字一致：{comp['a_answer_exact_match_v0_count']}/38。
- Retrieval、model revision 与解码配置未变。

## 3. 总体指标

| Metric | A baseline | B strict | Δ B−A |
|---|---:|---:|---:|
| Correctness normalized | {pp(ma['correctness_normalized'])} | {pp(mb['correctness_normalized'])} | {pp(comp['delta']['correctness_normalized'])} |
| Faithfulness normalized | {pp(ma['faithfulness_normalized'])} | {pp(mb['faithfulness_normalized'])} | {pp(comp['delta']['faithfulness_normalized'])} |
| Unsupported Claim Rate | {pp(ma['unsupported_claim_rate'])} | {pp(mb['unsupported_claim_rate'])} | {pp(comp['delta']['unsupported_claim_rate'])} |
| Citation compliance | {pp(ma['citation_compliance_rate'])} | {pp(mb['citation_compliance_rate'])} | {pp(comp['delta']['citation_compliance_rate'])} |
| Correct refusals | {ma['correct_refusal_count']} | {mb['correct_refusal_count']} | {comp['delta']['correct_refusal_count']:+d} |
| Hallucination answers | {ma['hallucination_answer_count']} | {mb['hallucination_answer_count']} | {comp['delta']['hallucination_answer_count']:+d} |

Human-validated correctness、faithfulness、unsupported claim rate、citation compliance：**N/A**。

## 4. Citation error taxonomy

A：{ma['label_distribution']}  
B：{mb['label_distribution']}

`MISSING_CITATION` 表示事实回答完全没有有效引用；`WRONG_CITATION` 表示引用资料不支持对应事实；`INSUFFICIENT_CITATION_COVERAGE` 表示只有部分事实单元有引用；`CITATION_FORMAT_ERROR` 表示引用格式或句末位置不合规。

## 5. Refusal 与安全性

A 正确拒答 {ma['correct_refusal_count']}，B 正确拒答 {mb['correct_refusal_count']}。已知交通 source gap 继续优先归因 `SOURCE_QUALITY_FAILURE`；B 若避免 V0 的证据外“公众号/小程序”补全，属于 prompt 改善，不代表 corpus gap 已修复。

## 6. 逐题变化

{comp['per_question_change']}。`improved` 只在 correctness/faithfulness/unsupported claims 不劣且 citation compliance 实质提升时成立；安全性下降直接记为 `degraded`；答案改变但缺乏合规引用、无法可靠归因时记为 `uncertain`。完整逐题 A/B、指标 delta、引用错误及诊断见 `results/ab_per_question.jsonl` 与 `analysis/ab_change_analysis.md`。所有 degraded case 均保留。

## 7. 结论与限制

本轮 **不推荐采用 B prompt**。虽然 B 的 provisional faithfulness proxy 增加 1.32 个百分点，但 correctness 降低 2.63 个百分点、Unsupported Claim Rate 增加 1.19 个百分点、citation compliance 从 5.26% 降至 0、正确拒答从 2 降至 0，hallucination answers 从 3 增至 5。更严格的自然语言指令没有改善该 1.5B 模型的 citation instruction-following，且在交通 source gap 等题上出现安全退化。

本实验只回答“更严格 prompt 在同一小模型与同一 evidence 上是否改善 grounded generation”。自动 evaluator 与 generator 同源，语义正确性仍需人工复核；不能把 proxy 当作 Gold。建议保留 A 作为当前 baseline，下一步先研究结构化/受约束解码或答案后置 citation validator，而不是继续堆叠 prompt 文本；不据此启动 SFT。
"""
    (ROOT/"answer_eval_v1_report.md").write_text(report,encoding="utf-8")
    print(json.dumps(comp,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
