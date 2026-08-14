from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from src.pipeline import WebSearchPipeline, append_jsonl

ROOT=Path(__file__).resolve().parent
QUESTIONS=json.loads((ROOT/"evaluation"/"frozen_questions.json").read_text(encoding="utf-8"))

def mean(values): return round(sum(values)/len(values),3) if values else "N/A"
def actual_request_count(records):
    """Support the already-persisted first run, whose client counter was cumulative."""
    total=0; previous=None
    for record in records:
        current=record["request_count"]
        total += current if previous is None or current < previous else current-previous
        previous=current
    return total
def failure_type(record):
    if record["errors"]:
        text=" ".join(record["errors"]).upper()
        if "RATE" in text: return "RATE_LIMIT"
        if "TIMEOUT" in text: return "TIMEOUT"
        return "API_ERROR"
    if not record["sources"]: return "SEARCH_NO_RESULT"
    if any(s.get("extraction_status")=="REJECT" for s in record["sources"]): return "EXTRACTION_FAILURE"
    return "IRRELEVANT_RESULT"

def main():
    pipeline=WebSearchPipeline(ROOT); records=[]
    results_dir=ROOT/"results"; results_dir.mkdir(exist_ok=True)
    output_path=results_dir/"formal_per_question_results.jsonl"
    if output_path.exists():
        # A time-limited host may interrupt a long live run. Reuse the already
        # persisted immutable per-question records and only retrieve missing IDs.
        records=[json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    completed={record["evaluation_id"] for record in records}
    for item in QUESTIONS:
        if item["id"] in completed:
            continue
        result=pipeline.retrieve(item["query"])
        result["evaluation_id"]=item["id"]; result["expected_mode"]=item["expected_mode"]
        if result["mode"]=="ACADEMIC_RETRIEVAL":
            result["original_problem"]=item["query"]
            result["knowledge_queries"]=result.get("academic_rewrite",{}).get("knowledge_queries",[])
            result["retrieved_sources"]=result["sources"]
            result["knowledge_evidence"]=result["evidence_spans"]
            result["possible_direct_answer_flag"]=any(bool(s.get("possible_direct_answer_flag")) for s in result["sources"])
        append_jsonl(output_path,result)
        for source in result["sources"]:
            append_jsonl(results_dir/"search_results.jsonl",source)
            if "extraction_status" in source: append_jsonl(results_dir/"extracted_pages.jsonl",source)
        for span in result["evidence_spans"]: append_jsonl(results_dir/"web_evidence_spans.jsonl",span)
        records.append(result)
        print(f'{item["id"]}: {result["status"]} ({result["request_count"]} API requests)')
    successes=[r for r in records if r["status"]=="SUCCESS"]
    extracted=[s for r in records for s in r["sources"] if "extraction_status" in s]
    evidence=[s for r in records for s in r["sources"] if s.get("extraction_status")!="REJECT" and "extraction_status" in s]
    academic=[r for r in records if r["expected_mode"]=="ACADEMIC_RETRIEVAL"]
    campus=[s for r in records if r["expected_mode"]=="CAMPUS_PUBLIC" for s in r["sources"] if s.get("extraction_status")!="REJECT"]
    failures=Counter(failure_type(r) for r in records if r["status"]!="SUCCESS")
    metrics={
      "evaluation_questions":len(records), "completed_questions":len(records),
      "router_accuracy_proxy":round(sum(r["mode"]==r["expected_mode"] for r in records)/len(records),4),
      "search_success_rate":round(sum(bool(r["sources"]) for r in records)/len(records),4),
      "extraction_success_rate":round(sum(s.get("extraction_status") in {"PASS","PARTIAL"} for s in extracted)/len(extracted),4) if extracted else "N/A",
      "campus_official_source_rate":round(sum(s.get("source_authority_level")=="OFFICIAL_THSINGHUA" for s in campus)/len(campus),4) if campus else "N/A",
      "high_authority_source_rate":round(sum(s.get("source_authority_level") in {"OFFICIAL_THSINGHUA","OFFICIAL_GOV","ACADEMIC","OFFICIAL_COMPANY","REPUTABLE_MEDIA"} for s in evidence)/len(evidence),4) if evidence else "N/A",
      "academic_knowledge_sufficiency_proxy":round(sum(bool(r.get("knowledge_evidence")) and r["status"]=="SUCCESS" for r in academic)/len(academic),4),
      "direct_answer_leakage_rate":round(sum(bool(r.get("possible_direct_answer_flag")) for r in academic)/len(academic),4),
      "average_search_latency_seconds":mean([r["search_latency_seconds"] for r in records if r["search_latency_seconds"]>0]),
      "average_extract_latency_seconds":mean([r["extract_latency_seconds"] for r in records if r["extract_latency_seconds"]>0]),
      "average_total_web_retrieval_latency_seconds":mean([r["total_latency_seconds"] for r in records]),
      "api_request_count":actual_request_count(records), "failure_taxonomy":dict(failures)
    }
    (results_dir/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    (results_dir/"failure_taxonomy.json").write_text(json.dumps(dict(failures),ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__": main()
