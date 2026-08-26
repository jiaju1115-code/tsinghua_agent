from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "chat_submission_candidate_v1.py"
SPEC = importlib.util.spec_from_file_location("chat_submission_candidate_v1", SCRIPT)
assert SPEC and SPEC.loader
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class Session:
    def __init__(self) -> None:
        self.turns = ["earlier"]


class FakeRuntime:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.session = Session()
        self.result = result or {"answer": "正常回答", "response_mode": "GENERAL_CONVERSATION", "machine_state": {"evidence_status": "NOT_REQUESTED", "citation_status": "NOT_REQUESTED"}, "citations": [], "frozen_runtime": None}
        self.error = error
        self.calls = 0

    def answer_query(self, query: str):
        self.calls += 1
        if self.error:
            raise self.error
        self.session.turns.append(query)
        return self.result


def test_module_commands_and_clear_context():
    runtime = FakeRuntime()
    assert "/debug on" in cli.handle_command("/help", runtime, False)["message"]
    assert cli.handle_command("/debug on", runtime, False)["debug"] is True
    assert cli.handle_command("/debug off", runtime, True)["debug"] is False
    assert cli.handle_command("/wat", runtime, False)["handled"] is True
    assert cli.handle_command("/exit", runtime, False)["exit"] is True
    assert cli.handle_command("/quit", runtime, False)["exit"] is True
    assert cli.handle_command("/clear", runtime, False)["handled"] is True
    assert runtime.session.turns == []


def test_rendering_uses_only_real_retrieved_citations_and_debug_does_not_change_answer():
    result = {
        "answer": "有支持的回答。",
        "response_mode": "PARTIAL_ANSWER",
        "machine_state": {"evidence_status": "PARTIAL", "citation_status": "PARTIAL", "unsupported_points": [{"point": "材料"}]},
        "citations": [{"source_id": "S1", "support_unit_id": "U1"}],
        "frozen_runtime": {"retrieval": {"ordered_top5_chunks": [{"chunk_id": "C1", "source_id": "S1", "title": "真实来源", "url": "https://example.test"}, {"chunk_id": "C2", "source_id": "S2", "title": "不得显示", "url": "https://bad.test"}]}, "citation": {"required_point_support": [{"point_text": "时间", "mapping_status": "SUPPORTED"}]}, "diagnostics": {"orchestrator": {"total_latency_ms": 12}}},
    }
    rendered = cli.render_response(result)
    assert "真实来源" in rendered and "https://example.test" in rendered
    assert "不得显示" not in rendered and "bad.test" not in rendered
    assert result["answer"] in rendered
    debug = cli.render_debug_info(result)
    assert "PARTIAL_ANSWER" in debug and "材料" in debug


def test_runtime_failure_has_no_fallback():
    runtime = FakeRuntime(error=RuntimeError("failure"))
    with pytest.raises(RuntimeError):
        cli.process_query(runtime, "清华本科生奖学金什么时候申请？")
    assert runtime.calls == 1


def test_process_query_reuses_the_same_session_runtime_across_turns():
    runtime = FakeRuntime()
    first = cli.process_query(runtime, "奖学金怎么申请？")
    second = cli.process_query(runtime, "本科生的。")
    assert first["answer"] == second["answer"]
    assert runtime.calls == 2
    assert runtime.session.turns[-2:] == ["奖学金怎么申请？", "本科生的。"]


def test_build_runtime_requires_integrity_before_factory():
    with pytest.raises(cli.StartupIntegrityError):
        cli.build_runtime(runtime_factory=FakeRuntime, integrity_verifier=lambda: (_ for _ in ()).throw(RuntimeError("bad freeze")))
    runtime = cli.build_runtime(runtime_factory=FakeRuntime, integrity_verifier=lambda: {"freeze_version": "FROZEN_BUNDLE_V1.1"})
    assert isinstance(runtime, FakeRuntime)
