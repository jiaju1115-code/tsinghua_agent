from __future__ import annotations

from src.runtime_v1.demo_cli import format_demo_result


def _result(answer: str = "示例回答", status: str = "PARTIAL_ANSWER") -> dict:
    return {
        "query": "示例问题",
        "answer": answer,
        "status": "COMPLETED",
        "retrieval": {"ordered_top5_chunks": [{"source_id": "S1", "title": "来源标题", "url": "https://example.test", "category": "测试"}], "source_ids": ["S1"]},
        "citation": {"usable_source_ids": ["S1"]},
        "refusal": {"refused": status == "REFUSAL"},
        "diagnostics": {"orchestrator": {"total_latency_ms": 12.5}, "answer_runtime": {"answer_status": status}},
    }


def test_demo_formatter_preserves_answer_and_shows_source() -> None:
    rendered = format_demo_result(_result("原始 Runtime 回答"))
    assert "原始 Runtime 回答" in rendered
    assert "来源标题" in rendered
    assert "https://example.test" in rendered
    assert "Traceback" not in rendered


def test_demo_formatter_refusal_is_human_readable() -> None:
    rendered = format_demo_result(_result("", "REFUSAL"))
    assert "当前资料不足" in rendered
    # The fixture carries a usable source; refusal presentation must retain it.
    assert "https://example.test" in rendered


def test_demo_formatter_hides_runtime_error_details() -> None:
    result = _result("", "REFUSAL")
    result["status"] = "RUNTIME_ERROR"
    result["diagnostics"]["answer_runtime"]["error"] = "internal stack details"
    rendered = format_demo_result(result)
    assert "internal stack details" not in rendered
    assert "系统暂时无法完成请求" in rendered
