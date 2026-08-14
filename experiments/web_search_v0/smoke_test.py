from __future__ import annotations
import json
from pathlib import Path
from src.pipeline import WebSearchPipeline

SMOKES = [
    ("Campus", "清华大学 本科生 奖助学金 最新通知"),
    ("Academic", "泊松分布 期望 方差 二阶矩 公式"),
    ("General", "2026年人工智能领域近期公开进展"),
]
def main():
    pipeline = WebSearchPipeline(Path(__file__).resolve().parent)
    results=[]
    for name, query in SMOKES:
        record=pipeline.retrieve(query); results.append({"name":name,"mode":record["mode"],"status":record["status"],"errors":record["errors"]})
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
