"""Run a provisional, evidence-only local evaluator over frozen generation results.

The evaluator is deliberately local and uses the same cached Qwen model as the
generator.  Its judgements are therefore PROVISIONAL_AUTO_EVAL, never human gold.
Deterministic citation/source checks are applied after the model judgement.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\python_projects\tsinghua_ai\data_second\answer_eval_v0")
VENDOR = ROOT / "vendor"
sys.path.insert(0, str(VENDOR))

from llama_cpp import Llama  # noqa: E402


MODEL = Path(
    r"C:\Users\林宇轩\.cache\huggingface\hub\models--Qwen--Qwen2.5-1.5B-Instruct-GGUF"
    r"\snapshots\91cad51170dc346986eccefdc2dd33a9da36ead9\qwen2.5-1.5b-instruct-q4_k_m.gguf"
)
INFILE = ROOT / "results" / "answer_generation_results.jsonl"
OUTFILE = ROOT / "results" / "answer_evaluation_results.jsonl"
SUMMARY = ROOT / "results" / "answer_evaluation_summary.json"

ALLOWED_TYPES = {
    "NONE",
    "RETRIEVAL_FAILURE",
    "SOURCE_QUALITY_FAILURE",
    "GENERATION_HALLUCINATION",
    "UNSUPPORTED_INFERENCE",
    "CITATION_MISMATCH",
    "OVERCONFIDENT_ANSWER",
    "INCOMPLETE_ANSWER",
    "CONFLICT_NOT_DISCLOSED",
}
REFUSAL_RE = re.compile(r"(根据当前资料无法确认|当前资料无法确认|资料不足|无法从.{0,8}资料|证据不足)")
CITATION_RE = re.compile(r"\[C([1-5])\]")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compact_evidence(row: dict, limit_each: int = 400) -> str:
    parts = []
    for c in row["retrieved_context"]:
        text = re.sub(r"\s+", " ", c["text"]).strip()
        parts.append(
            f"[{c['context_id']}] source={c['source_id']} title={c['title'][:100]}\n{text[:limit_each]}"
        )
    return "\n\n".join(parts)


def build_prompt(row: dict) -> str:
    return f"""你是证据约束型评估器。只能比较问题、回答和证据，不得使用外部知识。

评分：correctness/faithfulness/completeness/citation_correctness 均为 0、1、2：0=失败，1=部分，2=充分。
claim_count 为回答中可核验事实句数量；unsupported_claim_count 为证据无法支持的事实句数量。
evidence_sufficiency 只能是 sufficient / insufficient / conflicting。
consistency 只能是：
retrieval_correct_answer_correct / retrieval_correct_answer_wrong /
retrieval_wrong_answer_wrong / retrieval_insufficient_correct_refusal /
retrieval_insufficient_hallucination。
hallucination_types 只能从 NONE, RETRIEVAL_FAILURE, SOURCE_QUALITY_FAILURE,
GENERATION_HALLUCINATION, UNSUPPORTED_INFERENCE, CITATION_MISMATCH,
OVERCONFIDENT_ANSWER, INCOMPLETE_ANSWER, CONFLICT_NOT_DISCLOSED 中选择。
若回答有事实却无 [C#]，citation_correctness=0 且含 CITATION_MISMATCH。
如果证据不足而回答“根据当前资料无法确认”，这是正确拒答，不是答案错误。
只输出单个 JSON 对象，reason 不超过80字，不要 markdown。

问题：{row['question']}
期望证据关键词（仅作线索）：{row.get('expected_evidence_keyword') or 'N/A'}
回答：{row['generated_answer']}

证据：
{compact_evidence(row)}

JSON字段：correctness, faithfulness, completeness, citation_correctness,
claim_count, unsupported_claim_count, refusal_appropriate(true/false/null),
evidence_sufficiency, consistency, hallucination_types(数组), reason"""


def safe_int(value, default=0, lo=0, hi=20):
    try:
        return min(hi, max(lo, int(value)))
    except (TypeError, ValueError):
        return default


def normalize_judgement(row: dict, raw: dict) -> dict:
    out = {
        "correctness": safe_int(raw.get("correctness"), 0, 0, 2),
        "faithfulness": safe_int(raw.get("faithfulness"), 0, 0, 2),
        "completeness": safe_int(raw.get("completeness"), 0, 0, 2),
        "citation_correctness": safe_int(raw.get("citation_correctness"), 0, 0, 2),
        "claim_count": safe_int(raw.get("claim_count"), 0),
        "unsupported_claim_count": safe_int(raw.get("unsupported_claim_count"), 0),
        "refusal_appropriate": raw.get("refusal_appropriate")
        if raw.get("refusal_appropriate") in (True, False, None)
        else None,
        "evidence_sufficiency": raw.get("evidence_sufficiency")
        if raw.get("evidence_sufficiency") in {"sufficient", "insufficient", "conflicting"}
        else "insufficient",
        "consistency": raw.get("consistency")
        if raw.get("consistency")
        in {
            "retrieval_correct_answer_correct",
            "retrieval_correct_answer_wrong",
            "retrieval_wrong_answer_wrong",
            "retrieval_insufficient_correct_refusal",
            "retrieval_insufficient_hallucination",
        }
        else "retrieval_wrong_answer_wrong",
        "hallucination_types": [],
        "reason": str(raw.get("reason") or "")[:160],
    }
    types = raw.get("hallucination_types") or []
    if isinstance(types, str):
        types = [types]
    out["hallucination_types"] = [t for t in types if t in ALLOWED_TYPES and t != "NONE"]

    answer = row["generated_answer"]
    cited = set(row.get("answer_citations") or CITATION_RE.findall(answer))
    valid_context_ids = {c["context_id"] for c in row["retrieved_context"]}
    cited = {f"C{x}" if not str(x).startswith("C") else str(x) for x in cited}
    invalid_citations = sorted(cited - valid_context_ids)
    refused = bool(REFUSAL_RE.search(answer))
    expected_reliable = row.get("expected_source_status") == "reliable"
    expected_source = row.get("expected_source_id")
    source_hit = bool(expected_source and expected_source in row["retrieved_document_ids"])
    known_transport_gap = row["question_id"] in {"RET-09", "PROV-009"}

    # Hard, reproducible constraints take precedence over self-judgement.
    if known_transport_gap:
        out["evidence_sufficiency"] = "insufficient"
        if "SOURCE_QUALITY_FAILURE" not in out["hallucination_types"]:
            out["hallucination_types"].append("SOURCE_QUALITY_FAILURE")
        out["hallucination_types"] = [t for t in out["hallucination_types"] if t != "RETRIEVAL_FAILURE"]
    elif expected_reliable and not source_hit:
        if "RETRIEVAL_FAILURE" not in out["hallucination_types"]:
            out["hallucination_types"].append("RETRIEVAL_FAILURE")

    if out["claim_count"] > 0 and (not cited or invalid_citations):
        out["citation_correctness"] = 0
        if "CITATION_MISMATCH" not in out["hallucination_types"]:
            out["hallucination_types"].append("CITATION_MISMATCH")

    if refused and out["evidence_sufficiency"] == "insufficient":
        out["refusal_appropriate"] = True
        out["consistency"] = "retrieval_insufficient_correct_refusal"
    elif not refused and out["evidence_sufficiency"] == "insufficient":
        out["refusal_appropriate"] = False
        out["consistency"] = "retrieval_insufficient_hallucination"
        for t in ("OVERCONFIDENT_ANSWER", "GENERATION_HALLUCINATION"):
            if t not in out["hallucination_types"]:
                out["hallucination_types"].append(t)

    if out["unsupported_claim_count"] > out["claim_count"]:
        out["unsupported_claim_count"] = out["claim_count"]
    if out["unsupported_claim_count"] > 0 and "UNSUPPORTED_INFERENCE" not in out["hallucination_types"]:
        out["hallucination_types"].append("UNSUPPORTED_INFERENCE")
    if out["completeness"] < 2 and out["evidence_sufficiency"] == "sufficient" and not refused:
        if "INCOMPLETE_ANSWER" not in out["hallucination_types"]:
            out["hallucination_types"].append("INCOMPLETE_ANSWER")
    if not out["hallucination_types"]:
        out["hallucination_types"] = ["NONE"]

    out.update(
        {
            "refused": refused,
            "expected_source_reliable": expected_reliable,
            "expected_source_hit_top5": source_hit if expected_reliable else None,
            "valid_citations": sorted(cited & valid_context_ids),
            "invalid_citations": invalid_citations,
        }
    )
    return out


def summarize(rows: list[dict]) -> dict:
    judged = [r for r in rows if r["evaluation_status"] == "COMPLETED"]
    total_claims = sum(r["auto_evaluation"]["claim_count"] for r in judged)
    unsupported = sum(r["auto_evaluation"]["unsupported_claim_count"] for r in judged)
    type_counts = Counter(
        t for r in judged for t in r["auto_evaluation"]["hallucination_types"] if t != "NONE"
    )
    hallucination_rows = sum(
        any(t in {"GENERATION_HALLUCINATION", "UNSUPPORTED_INFERENCE", "OVERCONFIDENT_ANSWER"}
            for t in r["auto_evaluation"]["hallucination_types"])
        for r in judged
    )
    return {
        "evaluation_scope": "PROVISIONAL_AUTO_EVAL",
        "completed": len(judged),
        "answer_correctness_mean_0_to_2": round(sum(r["auto_evaluation"]["correctness"] for r in judged) / len(judged), 4) if judged else None,
        "answer_correctness_normalized": round(sum(r["auto_evaluation"]["correctness"] for r in judged) / (2 * len(judged)), 4) if judged else None,
        "fully_correct_count": sum(r["auto_evaluation"]["correctness"] == 2 for r in judged),
        "faithfulness_mean_0_to_2": round(sum(r["auto_evaluation"]["faithfulness"] for r in judged) / len(judged), 4) if judged else None,
        "faithfulness_normalized": round(sum(r["auto_evaluation"]["faithfulness"] for r in judged) / (2 * len(judged)), 4) if judged else None,
        "unsupported_claim_rate": round(unsupported / total_claims, 4) if total_claims else 0.0,
        "unsupported_claims": unsupported,
        "total_claims": total_claims,
        "correct_refusal_count": sum(r["auto_evaluation"]["refusal_appropriate"] is True for r in judged),
        "hallucination_answer_count": hallucination_rows,
        "hallucination_type_distribution": dict(type_counts),
        "retrieval_failure_count": type_counts.get("RETRIEVAL_FAILURE", 0),
        "source_quality_failure_count": type_counts.get("SOURCE_QUALITY_FAILURE", 0),
        "citation_mismatch_count": type_counts.get("CITATION_MISMATCH", 0),
        "retrieval_correct_answer_wrong_count": sum(r["auto_evaluation"]["consistency"] == "retrieval_correct_answer_wrong" for r in judged),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    rows = read_jsonl(INFILE)
    if len(rows) != 38:
        raise SystemExit(f"Expected 38 generation rows, found {len(rows)}")
    completed_ids = set()
    if OUTFILE.exists():
        completed_ids = {r["question_id"] for r in read_jsonl(OUTFILE)}

    llm = Llama(
        model_path=str(MODEL), n_ctx=4096, n_threads=12, n_threads_batch=16,
        n_batch=2048, n_ubatch=512, n_gpu_layers=0, verbose=False, seed=20260813,
    )
    for idx, row in enumerate(rows, 1):
        if row["question_id"] in completed_ids:
            continue
        started = time.perf_counter()
        status = "COMPLETED"
        raw_text = ""
        error = None
        try:
            response = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "只依据给定证据评估回答，严格输出JSON。"},
                    {"role": "user", "content": build_prompt(row)},
                ],
                temperature=0.0,
                max_tokens=220,
                response_format={"type": "json_object"},
                seed=20260813,
            )
            raw_text = response["choices"][0]["message"]["content"]
            raw = json.loads(raw_text)
            judgement = normalize_judgement(row, raw)
            usage = response.get("usage", {})
        except Exception as exc:  # Preserve failures; never fabricate a score.
            status = "BLOCKED"
            error = f"{type(exc).__name__}: {exc}"
            judgement = None
            usage = {}
        out = {
            "question_id": row["question_id"],
            "evaluation_scope": "PROVISIONAL_AUTO_EVAL",
            "evaluator_model": "Qwen/Qwen2.5-1.5B-Instruct-GGUF Q4_K_M local CPU",
            "evaluation_status": status,
            "auto_evaluation": judgement,
            "evaluator_raw_output": raw_text,
            "evaluator_error": error,
            "evaluator_latency_seconds": round(time.perf_counter() - started, 6),
            "evaluator_usage": usage,
        }
        with OUTFILE.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
        print(f"[{idx:02d}/38] {row['question_id']} {status} {out['evaluator_latency_seconds']:.2f}s", flush=True)

    merged = {r["question_id"]: r for r in read_jsonl(OUTFILE)}
    ordered = [merged[r["question_id"]] for r in rows]
    SUMMARY.write_text(json.dumps(summarize(ordered), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summarize(ordered), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
