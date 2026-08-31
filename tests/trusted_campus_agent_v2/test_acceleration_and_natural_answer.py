from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.trusted_campus_agent_v2.local_model import LocalQwenGroundedComposer


FACTS = [
    {"text": "申请人应于9月1日17:00前提交申请表。", "source_id": "S1", "title": "办理办法", "url": "https://x.tsinghua.edu.cn"},
    {"text": "审核通过后可以在系统中查看结果。", "source_id": "S1", "title": "办理办法", "url": "https://x.tsinghua.edu.cn"},
]


def test_natural_answer_validator_accepts_grounded_paragraphs() -> None:
    value = "你需要在9月1日17:00前提交申请表。[F1]\n\n提交后，审核结果可以在系统里查看。[F2]"
    assert LocalQwenGroundedComposer._validate_natural_answer(value, ["F1", "F2"], FACTS, "SUPPORTED") == value


def test_natural_answer_validator_rejects_new_deadline() -> None:
    with pytest.raises(ValueError, match="numeric"):
        LocalQwenGroundedComposer._validate_natural_answer(
            "你需要在9月3日17:00前提交申请表。[F1]", ["F1", "F2"], FACTS, "SUPPORTED"
        )


def test_partial_natural_answer_must_explain_limit() -> None:
    with pytest.raises(ValueError, match="limitation"):
        LocalQwenGroundedComposer._validate_natural_answer(
            "申请人应于9月1日17:00前提交申请表。[F1]", ["F1", "F2"], FACTS, "PARTIAL"
        )


def test_natural_answer_rejects_non_fact_status_tag() -> None:
    with pytest.raises(ValueError, match="fact IDs"):
        LocalQwenGroundedComposer._validate_natural_answer(
            "目前只能确认需要按要求提交申请表。[F1][PARTIAL]", ["F1", "F2"], FACTS, "PARTIAL"
        )


def test_natural_answer_rejects_semantically_unrelated_claim_with_valid_id() -> None:
    with pytest.raises(ValueError, match="sufficiently grounded"):
        LocalQwenGroundedComposer._validate_natural_answer(
            "请登录院系网站查询当年的最新通知和联系人。[F2]", ["F1", "F2"], FACTS, "SUPPORTED"
        )


def test_supported_answer_salvages_only_individually_grounded_claims() -> None:
    answer, dropped = LocalQwenGroundedComposer._salvage_supported_claims(
        "申请人应于9月1日17:00前提交申请表。[F1] 请登录院系网站查询联系人。[F2]",
        ["F1", "F2"], FACTS, "SUPPORTED",
    )
    assert "提交申请表" in answer
    assert "查询联系人" not in answer
    assert dropped == 1


def test_llama_auto_offloads_all_layers_when_backend_supports_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.trusted_campus_agent_v2.hardware import llama_acceleration

    monkeypatch.delenv("TSINGASK_FORCE_CPU", raising=False)
    monkeypatch.setenv("TSINGASK_GPU_LAYERS", "auto")
    info = llama_acceleration(SimpleNamespace(llama_supports_gpu_offload=lambda: True))
    assert info["n_gpu_layers"] == -1
    assert info["mode"] == "gpu"


def test_force_cpu_wins_over_available_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.trusted_campus_agent_v2.hardware import llama_acceleration

    monkeypatch.setenv("TSINGASK_FORCE_CPU", "1")
    info = llama_acceleration(SimpleNamespace(llama_supports_gpu_offload=lambda: True))
    assert info["n_gpu_layers"] == 0
    assert info["mode"] == "cpu"
