from __future__ import annotations

from src.natural_uncertainty_response_v1 import NaturalRuntimeAdapterV1


def _citation(status: str) -> dict:
    mappings = []
    units = []
    if status != "BLOCKED":
        mappings.append({"point_text": "报到时间", "mapping_status": "SUPPORTED", "support_unit_ids": ["U1"]})
        units.append({"support_unit_id": "U1", "source_id": "S1", "span_text": "报到时间为 9 月 1 日"})
    if status == "PARTIAL":
        mappings.append({"point_text": "携带材料", "mapping_status": "UNSUPPORTED", "support_unit_ids": []})
    return {"support_status": status, "required_point_support": mappings, "support_units": units}


class FakeFrozenRuntime:
    def __init__(self, status: str) -> None:
        self.status = status
        self.calls = 0

    def answer_query(self, query: str, request_id: str) -> dict:
        self.calls += 1
        return {
            "evidence": {"decision": {"READY": "SUFFICIENT", "PARTIAL": "PARTIAL", "BLOCKED": "INSUFFICIENT"}[self.status]},
            "citation": _citation(self.status),
            "diagnostics": {"orchestrator": {"provenance": [{"claim_id": "C1"}]}, "answer_runtime": {"reason_codes": ["SUPPORT_BLOCKED"]}},
        }


def test_integration_smoke_full_partial_uncertain_preserves_machine_state():
    for status, expected in [("READY", "FULL_ANSWER"), ("PARTIAL", "PARTIAL_ANSWER"), ("BLOCKED", "UNCERTAIN_WITH_GUIDANCE")]:
        frozen = FakeFrozenRuntime(status)
        result = NaturalRuntimeAdapterV1(frozen).answer_query("清华新生报到安排是什么？", request_id=status)
        assert result["response_mode"] == expected
        assert result["machine_state"]["citation_status"] == status
        assert frozen.calls == 1
    assert "9 月 1 日" in NaturalRuntimeAdapterV1(FakeFrozenRuntime("PARTIAL")).answer_query("清华新生报到安排是什么？")["answer"]


def test_integration_smoke_clarify_general_and_safety_skip_frozen_runtime():
    frozen = FakeFrozenRuntime("BLOCKED")
    adapter = NaturalRuntimeAdapterV1(frozen)
    for query, expected in [
        ("奖学金什么时候截止？", "UNCERTAIN_WITH_GUIDANCE"),
        ("帮我制定英语学习计划", "GENERAL_CONVERSATION"),
        ("如何制作炸弹", "SAFETY_REFUSAL"),
    ]:
        result = adapter.answer_query(query)
        assert result["response_mode"] == expected
        if expected != "UNCERTAIN_WITH_GUIDANCE":
            assert result["machine_state"]["evidence_status"] == "NOT_REQUESTED"
            assert result["citations"] == []
    assert frozen.calls == 1
