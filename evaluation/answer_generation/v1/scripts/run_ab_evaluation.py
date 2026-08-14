"""Identical provisional evidence evaluator for both A/B generations."""
from __future__ import annotations

import json, re, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT.parent
sys.path.insert(0,str(DATA/"answer_eval_v0"/"vendor"))
from llama_cpp import Llama  # noqa:E402

MODEL=Path(r"C:\Users\林宇轩\.cache\huggingface\hub\models--Qwen--Qwen2.5-1.5B-Instruct-GGUF\snapshots\91cad51170dc346986eccefdc2dd33a9da36ead9\qwen2.5-1.5b-instruct-q4_k_m.gguf")
VALID_CITE=re.compile(r"\[C([1-5])\]",re.I); REFUSAL=re.compile(r"根据当前资料无法确认|当前资料无法确认|资料不足|无法从.{0,8}资料|证据不足")
CORE_LABELS={"RETRIEVAL_FAILURE","SOURCE_QUALITY_FAILURE","GENERATION_HALLUCINATION","OVERCONFIDENT_ANSWER"}
CITE_LABELS={"MISSING_CITATION","WRONG_CITATION","INSUFFICIENT_CITATION_COVERAGE","CITATION_FORMAT_ERROR"}

def read_jsonl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def compact(row):
    return "\n\n".join(f"[{c['context_id']}] source={c['source_id']} title={c['title'][:100]}\n{re.sub(r'\s+',' ',c['text']).strip()[:260]}" for c in row["retrieved_context"])

def judge_prompt(row):
    return f"""只能比较问题、回答和证据，不得使用外部知识。对回答作证据支持评估。
correctness/faithfulness/completeness 为0、1、2（失败、部分、充分）。
claim_count 是回答中可核验事实数量；unsupported_claim_count 是证据不支持的事实数量。
evidence_sufficiency 只能是 sufficient/insufficient/conflicting。
wrong_citation_context_ids：列出回答中存在但不能支持其对应事实的 C1-C5；没有则空数组。
只输出一个JSON对象，不输出markdown。reason不超过80字。

问题：{row['question']}
回答：{row['generated_answer']}
期望证据关键词（仅线索）：{row.get('expected_evidence_keyword') or 'N/A'}
证据：
{compact(row)}

JSON字段：correctness,faithfulness,completeness,claim_count,unsupported_claim_count,evidence_sufficiency,wrong_citation_context_ids,reason"""

def sint(v,lo=0,hi=30):
    try:return min(hi,max(lo,int(v)))
    except:return lo

def citation_rules(answer, bare_refusal, wrong_ids):
    valid=[f"C{x}" for x in VALID_CITE.findall(answer)]; unique=sorted(set(valid),key=lambda x:int(x[1:]))
    # Units approximate fact sentences/list items; the semantic judge separately counts claims.
    units=[x.strip(" -•\t") for x in re.split(r"(?<=[。！？；])|\n+",answer) if x.strip(" -•\t")]
    factual=[] if bare_refusal else [u for u in units if not REFUSAL.search(u) and len(re.sub(r"\[C[1-5]\]","",u).strip("。！？；：:，,"))>=2]
    cited_units=[u for u in factual if VALID_CITE.search(u)]
    citation_like=re.findall(r"(?:\[\s*C\s*\d+\s*\]|【\s*C\s*\d+\s*】|\(\s*C\s*\d+\s*\)|(?<!\[)\bC\d+\b)",answer,re.I)
    malformed=[x for x in citation_like if not re.fullmatch(r"\[C[1-5]\]",x,re.I)]
    misplaced=[u for u in cited_units if not re.search(r"\[C[1-5]\](?:\s*\[C[1-5]\])*[。！？；]?$",u,re.I)]
    errors=[]
    if not bare_refusal and factual and not unique: errors.append("MISSING_CITATION")
    if unique and factual and len(cited_units)<len(factual): errors.append("INSUFFICIENT_CITATION_COVERAGE")
    if wrong_ids: errors.append("WRONG_CITATION")
    if malformed or misplaced: errors.append("CITATION_FORMAT_ERROR")
    compliant=bare_refusal or (bool(factual) and not errors)
    return {"valid_citations":unique,"claim_units":factual,"cited_claim_units":len(cited_units),"citation_coverage":1.0 if bare_refusal else (len(cited_units)/len(factual) if factual else 0.0),"malformed_citation_tokens":malformed,"misplaced_citation_units":misplaced,"citation_error_types":errors,"citation_compliance":compliant}

def normalize(row,raw):
    answer=row["generated_answer"].strip(); refused=bool(REFUSAL.search(answer)); bare_refusal=answer in {"根据当前资料无法确认。","根据当前资料无法确认","当前资料无法确认。","当前资料无法确认"}; expected_rel=row.get("expected_source_status")=="reliable"; src=row.get("expected_source_id"); src_hit=bool(src and src in row["retrieved_document_ids"])
    suff=raw.get("evidence_sufficiency") if raw.get("evidence_sufficiency") in {"sufficient","insufficient","conflicting"} else "insufficient"
    labels=[]
    if row["question_id"] in {"RET-09","PROV-009"}: suff="insufficient"; labels.append("SOURCE_QUALITY_FAILURE")
    elif expected_rel and not src_hit: suff="insufficient"; labels.append("RETRIEVAL_FAILURE")
    wrong=[x.upper() for x in (raw.get("wrong_citation_context_ids") or []) if str(x).upper() in {"C1","C2","C3","C4","C5"}]
    cr=citation_rules(row["generated_answer"],bare_refusal,wrong)
    claims=sint(raw.get("claim_count")); unsupported=min(claims,sint(raw.get("unsupported_claim_count")))
    correctness=sint(raw.get("correctness"),0,2); faith=sint(raw.get("faithfulness"),0,2); complete=sint(raw.get("completeness"),0,2)
    refusal_appropriate=None
    if suff=="insufficient":
        refusal_appropriate=bare_refusal
        if bare_refusal: claims=unsupported=0; correctness=faith=2
        else:
            labels += ["GENERATION_HALLUCINATION","OVERCONFIDENT_ANSWER"]
            claims=max(1,claims); unsupported=max(1,unsupported)
    elif bare_refusal:
        refusal_appropriate=False; correctness=0; complete=0; cr["citation_compliance"]=False
    if unsupported>0 and "GENERATION_HALLUCINATION" not in labels: labels.append("GENERATION_HALLUCINATION")
    labels += cr["citation_error_types"]
    labels=list(dict.fromkeys(labels)) or ["NONE"]
    consistency=("retrieval_insufficient_correct_refusal" if suff=="insufficient" and refused else "retrieval_insufficient_hallucination" if suff=="insufficient" else "retrieval_correct_answer_correct" if correctness==2 and faith==2 and cr["citation_compliance"] else "retrieval_correct_answer_wrong")
    return {"correctness":correctness,"faithfulness":faith,"completeness":complete,"claim_count":claims,"unsupported_claim_count":unsupported,"evidence_sufficiency":suff,"refused":refused,"bare_refusal":bare_refusal,"refusal_appropriate":refusal_appropriate,"expected_source_reliable":expected_rel,"expected_source_hit_top5":src_hit if expected_rel else None,"wrong_citation_context_ids":wrong,**cr,"hallucination_types":labels,"consistency":consistency,"reason":str(raw.get("reason") or "")[:160]}

def summary(rows):
    good=[r for r in rows if r["evaluation_status"]=="COMPLETED"]; a=[r["auto_evaluation"] for r in good]; claims=sum(x["claim_count"] for x in a); uns=sum(x["unsupported_claim_count"] for x in a); labels=Counter(t for x in a for t in x["hallucination_types"] if t!="NONE")
    return {"scope":"PROVISIONAL_AUTO_EVAL","completed":len(good),"correctness_mean_0_2":round(sum(x["correctness"] for x in a)/len(a),4),"correctness_normalized":round(sum(x["correctness"] for x in a)/(2*len(a)),4),"faithfulness_mean_0_2":round(sum(x["faithfulness"] for x in a)/len(a),4),"faithfulness_normalized":round(sum(x["faithfulness"] for x in a)/(2*len(a)),4),"unsupported_claims":uns,"total_claims":claims,"unsupported_claim_rate":round(uns/claims,4) if claims else 0,"citation_compliant_count":sum(x["citation_compliance"] for x in a),"citation_compliance_rate":round(sum(x["citation_compliance"] for x in a)/len(a),4),"correct_refusal_count":sum(x["refusal_appropriate"] is True for x in a),"inappropriate_refusal_count":sum(x["refusal_appropriate"] is False and x["refused"] for x in a),"hallucination_answer_count":sum("GENERATION_HALLUCINATION" in x["hallucination_types"] for x in a),"label_distribution":dict(labels),"avg_evaluator_latency_seconds":round(sum(r["evaluator_latency_seconds"] for r in good)/len(good),4)}

def main():
    llm=Llama(model_path=str(MODEL),n_ctx=3072,n_threads=12,n_threads_batch=16,n_batch=2048,n_ubatch=512,n_gpu_layers=0,seed=20260813,verbose=False)
    for group in ("A","B"):
        rows=read_jsonl(ROOT/"results"/f"generation_{group.lower()}.jsonl"); out=ROOT/"results"/f"evaluation_{group.lower()}.jsonl"; done={x["question_id"] for x in read_jsonl(out)} if out.exists() else set()
        for idx,row in enumerate(rows,1):
            if row["question_id"] in done: continue
            t=time.perf_counter(); status="COMPLETED"; raw_text=""; err=None
            try:
                resp=llm.create_chat_completion(messages=[{"role":"system","content":"只依据给定证据评估回答，严格输出JSON。"},{"role":"user","content":judge_prompt(row)}],temperature=0,max_tokens=180,response_format={"type":"json_object"},seed=20260813)
                raw_text=resp["choices"][0]["message"]["content"]; auto=normalize(row,json.loads(raw_text)); usage=resp.get("usage",{})
            except Exception as ex: status="BLOCKED"; auto=None; usage={}; err=f"{type(ex).__name__}: {ex}"
            rec={"group":group,"question_id":row["question_id"],"evaluation_scope":"PROVISIONAL_AUTO_EVAL","evaluation_status":status,"auto_evaluation":auto,"evaluator_model":"Qwen/Qwen2.5-1.5B-Instruct-GGUF Q4_K_M local CPU","evaluator_raw_output":raw_text,"evaluator_error":err,"evaluator_latency_seconds":round(time.perf_counter()-t,6),"evaluator_usage":usage,"evaluated_utc":datetime.now(timezone.utc).isoformat()}
            with out.open("a",encoding="utf-8",newline="\n") as fh: fh.write(json.dumps(rec,ensure_ascii=False)+"\n")
            print(f"[{group} {idx:02d}/38] {row['question_id']} {status} {rec['evaluator_latency_seconds']:.2f}s",flush=True)
        res=read_jsonl(out)
        if len(res)!=38 or any(x["evaluation_status"]!="COMPLETED" for x in res): raise SystemExit(f"Group {group} evaluation incomplete")
        (ROOT/"results"/f"metrics_{group.lower()}.json").write_text(json.dumps(summary(res),ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({"group":group,**summary(res)},ensure_ascii=False),flush=True)

if __name__=="__main__": main()
