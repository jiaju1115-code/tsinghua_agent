from __future__ import annotations

import json
import sys
from pathlib import Path
import argparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2 import OpenAICompatibleFileToolPlanner, TrustedCampusAgentV2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow", action="store_true", help="use the opt-in unpublished V2 expansion bundle")
    parser.add_argument("--no-warmup", action="store_true", help="skip one-time dense model warmup")
    parser.add_argument("--file-llm", action="store_true", help="enable LLM Tool Calling for file requests")
    parser.add_argument("--llm-env-prefix", default="MOMO", help="LLM environment prefix (default: MOMO)")
    args = parser.parse_args()
    print(f"清问·可信校园事务智能体 V2（本地候选版；{'shadow 扩展' if args.shadow else '冻结 V1'}；输入 /exit 退出）")
    file_planner = OpenAICompatibleFileToolPlanner.from_env(args.llm_env_prefix) if args.file_llm else None
    agent = TrustedCampusAgentV2(use_shadow=args.shadow, file_planner=file_planner)
    if not args.no_warmup:
        print("正在预热 Full Path dense 检索……")
        ready = agent.warmup_full_path()
        print(f"检索已就绪（{ready['latency_ms']:.0f} ms）")
    while True:
        try:
            query = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if query == "/exit":
            return
        if not query:
            continue
        result = agent.handle(query)
        if "artifact" in result:
            print(json.dumps({
                "tool_route": result["route"], "artifact": result["artifact"],
                "latency_ms": result["latency_ms"],
            }, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({
                "path": result["path"], "evidence_status": result["evidence_status"],
                **result["response"], "latency_ms": result["total_latency_ms"],
            }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
