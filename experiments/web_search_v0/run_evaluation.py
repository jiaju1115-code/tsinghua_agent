from __future__ import annotations
import argparse, json
from pathlib import Path
from src.pipeline import WebSearchPipeline, append_jsonl

ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser(); p.add_argument("--query"); args=p.parse_args(); query=args.query or "清华大学 本科生 奖助学金 最新通知"
    result=WebSearchPipeline(ROOT).retrieve(query)
    append_jsonl(ROOT/"results"/"per_question_results.jsonl",result)
    for source in result.get("sources",[]):
        append_jsonl(ROOT/"results"/"search_results.jsonl",source)
        if "extraction_status" in source:
            append_jsonl(ROOT/"results"/"extracted_pages.jsonl",source)
    for span in result.get("evidence_spans",[]): append_jsonl(ROOT/"results"/"web_evidence_spans.jsonl",span)
    print(json.dumps({k:result[k] for k in ("query","mode","status","router_reason","errors","request_count","total_latency_seconds") if k in result},ensure_ascii=False))
if __name__=="__main__": main()
