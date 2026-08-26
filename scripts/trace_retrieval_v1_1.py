"""Print a full retrieval trace for the independent V1.1 candidate."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.semantic_retrieval_v1_1 import CandidateRetrieverV1_1

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("query"); parser.add_argument("--context", action="append", default=[]); args=parser.parse_args()
    print(json.dumps(CandidateRetrieverV1_1().trace(args.query, args.context), ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__": raise SystemExit(main())
