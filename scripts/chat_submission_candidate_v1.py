"""Local interactive CLI for the frozen Submission Candidate V1 runtime."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.natural_uncertainty_response_v1 import NaturalRuntimeAdapterV1
from src.runtime_v1.freeze_loader_v1_1 import verify_active_freeze_reference
from src.semantic_retrieval_v1_1 import CandidateRetrieverV1_1


HELP = """可用命令：
  /help       显示此帮助
  /debug on   显示开发者信息
  /debug off  关闭开发者信息
  /clear      清空当前对话上下文
  /exit       退出
  /quit       退出"""


class StartupIntegrityError(RuntimeError):
    pass


def configure_console_encoding() -> None:
    """Best-effort UTF-8 console compatibility without mutating global files."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def build_runtime(
    runtime_factory: Callable[[], Any] = NaturalRuntimeAdapterV1,
    integrity_verifier: Callable[[], Any] = verify_active_freeze_reference,
) -> Any:
    """Verify approved canonical freeze metadata before creating the runtime."""
    try:
        integrity_verifier()
    except Exception as exc:
        raise StartupIntegrityError("Submission Candidate integrity check failed.") from exc
    return runtime_factory()


def clear_context(runtime: Any) -> bool:
    session = getattr(runtime, "session", None)
    turns = getattr(session, "turns", None)
    if isinstance(turns, list):
        turns.clear()
        return True
    return False


def handle_command(command: str, runtime: Any, debug: bool) -> dict[str, Any]:
    normalized = command.strip().lower()
    if normalized == "/help":
        return {"handled": True, "message": HELP, "debug": debug, "exit": False}
    if normalized == "/debug on":
        return {"handled": True, "message": "开发者信息已开启。", "debug": True, "exit": False}
    if normalized == "/debug off":
        return {"handled": True, "message": "开发者信息已关闭。", "debug": False, "exit": False}
    if normalized == "/clear":
        cleared = clear_context(runtime)
        return {"handled": True, "message": "当前对话上下文已清空。" if cleared else "当前 Runtime 不支持清空上下文。", "debug": debug, "exit": False}
    if normalized in {"/exit", "/quit"}:
        return {"handled": True, "message": "再见。", "debug": debug, "exit": True}
    if normalized.startswith("/"):
        return {"handled": True, "message": "未知命令，输入 /help 查看可用命令。", "debug": debug, "exit": False}
    return {"handled": False, "message": "", "debug": debug, "exit": False}


def process_query(runtime: Any, query: str) -> dict[str, Any]:
    """Call only the submission runtime; exceptions are surfaced to the caller."""
    return runtime.answer_query(query)


def _real_sources(result: dict[str, Any]) -> list[dict[str, str]]:
    frozen = result.get("frozen_runtime") or {}
    retrieval = frozen.get("retrieval") or {}
    permitted = {row.get("source_id") for row in result.get("citations", []) if isinstance(row, dict)}
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for chunk in retrieval.get("ordered_top5_chunks", []) or []:
        source_id = chunk.get("source_id")
        if source_id not in permitted or source_id in seen:
            continue
        seen.add(source_id)
        title = chunk.get("title") or source_id
        row = {"source_id": source_id, "title": title}
        if isinstance(chunk.get("url"), str) and chunk["url"]:
            row["url"] = chunk["url"]
        sources.append(row)
    return sources


def render_response(result: dict[str, Any]) -> str:
    answer = result.get("answer") if isinstance(result.get("answer"), str) else ""
    lines = [f"清小搭：{answer or '本轮运行失败，请检查 Runtime 状态。'}"]
    sources = _real_sources(result)
    if sources:
        lines.append("参考：")
        for index, source in enumerate(sources, 1):
            suffix = f" — {source['url']}" if source.get("url") else ""
            lines.append(f"[{index}] {source['title']}{suffix}")
    return "\n".join(lines)


def _candidate_trace(runtime: Any, query: str) -> dict[str, Any] | None:
    """Diagnostic-only candidate trace; normal answer execution remains frozen V1."""
    frozen_runtime = getattr(runtime, "runtime", None)
    dense = getattr(frozen_runtime, "retriever", None)
    try:
        return CandidateRetrieverV1_1(dense=dense).trace(query, getattr(getattr(runtime, "session", None), "turns", [])[:-1])
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def render_debug_info(result: dict[str, Any], retrieval_trace: dict[str, Any] | None = None) -> str:
    state = result.get("machine_state") or {}
    frozen = result.get("frozen_runtime") or {}
    citation = frozen.get("citation") or {}
    retrieval = frozen.get("retrieval") or {}
    mappings = citation.get("required_point_support") or []
    supported = [row.get("point_text") for row in mappings if row.get("mapping_status") in {"SUPPORTED", "PARTIALLY_SUPPORTED"}]
    unsupported = state.get("unsupported_points") or []
    unsupported_text = [row.get("point") if isinstance(row, dict) else str(row) for row in unsupported]
    chunks = [row.get("chunk_id") for row in retrieval.get("ordered_top5_chunks", []) or []]
    orchestrator = (frozen.get("diagnostics") or {}).get("orchestrator") or {}
    latency = orchestrator.get("total_latency_ms", "N/A")
    value = lambda item: ", ".join(str(x) for x in item if x) if item else "N/A"
    lines = [
        "--- Developer Info ---",
        f"Response Mode: {result.get('response_mode', 'N/A')}",
        "Route: N/A",
        f"Evidence Status: {state.get('evidence_status', 'N/A')}",
        f"Citation Status: {state.get('citation_status', 'N/A')}",
        f"Retrieved Chunks: {value(chunks)}",
        f"Supported Points: {value(supported)}",
        f"Unsupported Points: {value(unsupported_text)}",
        f"Latency: {latency}",
    ]
    if retrieval_trace:
        understanding = retrieval_trace.get("query_understanding", {})
        final_rows = retrieval_trace.get("final_top5", [])
        lines.extend([
            "--- Retrieval Trace V1.1 Candidate ---",
            f"Original Query: {understanding.get('original_query', 'N/A')}",
            f"Normalized Query: {understanding.get('normalized_query', 'N/A')}",
            f"Route: {understanding.get('route', 'N/A')}",
            f"Retrieval Invoked: {retrieval_trace.get('retrieval_invoked', 'N/A')}",
            f"Retriever Version: {retrieval_trace.get('retriever_version', 'N/A')}",
            "Final Top-5: " + value([f"{row.get('chunk_id')}:{row.get('title')}" for row in final_rows]),
        ])
    lines.append("----------------------")
    return "\n".join(lines)


def main() -> int:
    configure_console_encoding()
    try:
        runtime = build_runtime()
    except StartupIntegrityError:
        print("Submission Candidate integrity check failed.")
        return 1
    debug = False
    print("=" * 48)
    print("清小搭 · Submission Candidate V1")
    print("输入 /help 查看命令")
    print("输入 /exit 退出")
    print("=" * 48)
    while True:
        try:
            text = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return 0
        if not text:
            continue
        command = handle_command(text, runtime, debug)
        debug = command["debug"]
        if command["handled"]:
            print(command["message"])
            if command["exit"]:
                return 0
            continue
        try:
            result = process_query(runtime, text)
            print(render_response(result))
            if debug:
                print(render_debug_info(result, _candidate_trace(runtime, text)))
        except Exception as exc:
            print("清小搭：本轮运行失败，请检查 Runtime 状态。")
            if debug:
                print(f"--- Developer Info ---\nException: {type(exc).__name__}\nReason: {getattr(exc, 'code', 'N/A')}\n----------------------")

if __name__ == "__main__":
    raise SystemExit(main())
