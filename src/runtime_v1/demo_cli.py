"""Minimal presentation-only CLI for Runtime V1 demonstrations."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .runtime import answer_query


STATUS_LABELS = {
    "FULL_ANSWER": "已找到充分支持的信息",
    "PARTIAL_ANSWER": "部分信息得到支持",
    "REFUSAL": "当前资料不足，暂不可靠回答",
    "RUNTIME_ERROR": "系统暂时无法完成请求",
}


def _sources(result: dict[str, Any]) -> list[dict[str, Any]]:
    retrieval = result.get("retrieval") or {}
    citation = result.get("citation") or {}
    chunks = {row.get("source_id"): row for row in retrieval.get("ordered_top5_chunks", [])}
    source_ids = citation.get("usable_source_ids", []) or []
    output = []
    for source_id in source_ids:
        chunk = chunks.get(source_id, {})
        output.append({
            "source_id": source_id,
            "title": chunk.get("title"),
            "url": chunk.get("url"),
            "category": chunk.get("category"),
        })
    return output


def format_demo_result(result: dict[str, Any]) -> str:
    """Render only presentation fields; never rewrite the Runtime answer."""
    answer_runtime = result.get("diagnostics", {}).get("answer_runtime") or {}
    answer_status = answer_runtime.get("answer_status") or result.get("status", "RUNTIME_ERROR")
    diagnostics = result.get("diagnostics", {}).get("orchestrator", {}) or {}
    sources = _sources(result)
    lines = [
        "=" * 56,
        "清华校园智能问答 Demo",
        "=" * 56,
        f"问题：{result.get('query', '')}",
        "",
        "回答：",
        result.get("answer") or STATUS_LABELS.get(answer_status, "系统暂时无法完成请求"),
        "",
        f"状态：{STATUS_LABELS.get(answer_status, answer_status)}",
    ]
    if sources:
        lines.extend(["", "参考来源："])
        for index, source in enumerate(sources, 1):
            title = source.get("title") or source["source_id"]
            url = f" — {source['url']}" if source.get("url") else ""
            lines.append(f"[{index}] {title}{url}")
    else:
        lines.extend(["", "参考来源：当前没有可展示的支持来源"])
    latency = diagnostics.get("total_latency_ms")
    if isinstance(latency, (int, float)):
        lines.extend(["", f"耗时：{latency:.0f} ms"])
    if result.get("status") == "RUNTIME_ERROR":
        lines.extend(["", "提示：系统暂时无法完成请求，请稍后重试。"])
    lines.append("=" * 56)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runtime V1 minimal demo CLI")
    parser.add_argument("--query", help="one query; omit for interactive mode")
    parser.add_argument("--json", action="store_true", help="print the structured Runtime result")
    args = parser.parse_args(argv)
    if args.query is not None:
        queries = [args.query]
    else:
        print("清华校园智能问答 Demo（输入空行退出）")
        queries = []
        while True:
            query = input("问题：").strip()
            if not query:
                break
            queries.append(query)
    for query in queries:
        result = answer_query(query)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_demo_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
