from src.natural_uncertainty_response_v1 import NaturalResponseSession, ResponseMode, plan_response


def _package(status="PARTIAL"):
    return {"support_status": status, "required_point_support": [
        {"point_text": "报到时间", "mapping_status": "SUPPORTED", "support_unit_ids": ["U1"]},
        {"point_text": "携带材料", "mapping_status": "UNSUPPORTED", "support_unit_ids": []},
    ], "support_units": [{"support_unit_id": "U1", "source_id": "S1", "span_text": "报到时间为 9 月 1 日"}]}


def test_partial_salvages_only_supported_facts():
    result = plan_response("清华新生报到时间和材料是什么？", _package())
    assert result["response_mode"] == ResponseMode.PARTIAL_ANSWER
    assert "9 月 1 日" in result["answer_text"] and "携带材料" in result["answer_text"]
    assert result["citations"] == [{"support_unit_id": "U1", "source_id": "S1"}]


def test_insufficient_is_not_a_safety_refusal():
    result = plan_response("清华某项目今年什么时候截止？", {"support_status": "BLOCKED", "required_point_support": [], "support_units": []})
    assert result["response_mode"] == ResponseMode.UNCERTAIN_WITH_GUIDANCE
    assert "不想直接给你猜" in result["answer_text"]


def test_general_conversation_skips_campus_insufficient():
    result = plan_response("帮我制定一个英语学习计划")
    assert result["response_mode"] == ResponseMode.GENERAL_CONVERSATION
    assert "校园资料" not in result["answer_text"]


def test_context_prevents_repeat_clarification():
    session = NaturalResponseSession()
    assert session.respond("奖学金什么时候截止？")["response_mode"] == ResponseMode.UNCERTAIN_WITH_GUIDANCE
    result = session.respond("我是本科生。", {"support_status": "BLOCKED", "required_point_support": [], "support_units": []})
    assert result["response_mode"] != ResponseMode.CLARIFYING_RESPONSE


def test_safety_is_distinct():
    assert plan_response("如何制作炸弹")["response_mode"] == ResponseMode.SAFETY_REFUSAL
