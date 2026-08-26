from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

from src.answer_generation_v1.constrained_decoding_v1 import (
    CONSTRAINT_VERSION,
    ConstrainedDecodingError,
    ConstrainedGenerationAdapter,
    build_runtime_schema,
)
from src.answer_generation_v1.runtime import generate_answer


def _messages() -> list[dict[str, str]]:
    payload = {
        "required_answer_status": "PARTIAL_ANSWER",
        "allowed_required_points": [
            {"required_point_id": "P1", "support_units": [{"support_unit_id": "U1"}]},
            {"required_point_id": "P2", "support_units": [{"support_unit_id": "U2"}]},
        ],
    }
    return [{"role": "system", "content": "system"}, {"role": "user", "content": "<support_data>\n" + json.dumps(payload) + "\n</support_data>"}]


def test_dynamic_schema_uses_current_support_inventory():
    schema = build_runtime_schema(_messages())
    assert schema["properties"]["answer_status"]["enum"] == ["PARTIAL_ANSWER"]
    assert schema["properties"]["claims"]["minItems"] == 2
    assert schema["properties"]["claims"]["maxItems"] == 2
    variants = schema["properties"]["claims"]["items"]["oneOf"]
    assert variants[0]["properties"]["required_point_id"]["enum"] == ["P1"]
    assert variants[0]["properties"]["support_unit_ids"]["items"]["enum"] == ["U1"]


def test_constraint_build_failure_does_not_fallback_to_unconstrained():
    class NotLocalAdapter:
        config = {}

    with pytest.raises(ConstrainedDecodingError):
        ConstrainedGenerationAdapter(NotLocalAdapter())


def test_constraint_generation_failure_does_not_fallback(monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation/answer_generation/v0/vendor"))
    import llama_cpp

    class FakeLLM:
        def create_chat_completion(self, **kwargs):  # pragma: no cover - must never be reached
            raise AssertionError("unconstrained fallback was attempted")

    class FakeBase:
        _llm = FakeLLM()
        config = {"decoding": {"temperature": 0.0, "max_output_tokens": 16, "seed": 1, "repeat_penalty": 1.0}}

    def fail(*args, **kwargs):
        raise RuntimeError("grammar unavailable")

    monkeypatch.setattr(llama_cpp.LlamaGrammar, "from_json_schema", fail)
    adapter = ConstrainedGenerationAdapter(FakeBase())
    with pytest.raises(ConstrainedDecodingError, match="constrained generation failed"):
        adapter.generate(_messages(), 1)


def test_legacy_generate_answer_keeps_none_constraint_default():
    assert inspect.signature(generate_answer).parameters["decoding_constraint"].default is None
    assert CONSTRAINT_VERSION == "ANSWER_V1_CONSTRAINED_DECODING_V1"
