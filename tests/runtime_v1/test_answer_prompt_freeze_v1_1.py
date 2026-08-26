from __future__ import annotations

import pytest

from src.runtime_v1.answer_prompt_freeze_v1_1 import verify_answer_prompt_freeze_v1_1


def test_real_windows_prompt_passes_approved_v1_1_verification() -> None:
    result = verify_answer_prompt_freeze_v1_1()
    assert result["version"] == "ANSWER_V1_PROMPT_FREEZE_V1.1"
    assert result["text_hash_mode"] == "CANONICAL_TEXT_V1"
    assert result["verified_artifacts"] == "evaluation/answer_generation/runtime_v1/prompts/answer_generation_v1_prompt.md"
