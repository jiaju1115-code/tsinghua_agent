"""Versioned, runtime-context-bound constrained decoding for Answer V1.

This adapter constrains only the structured output shape and the support IDs
that are already present in the current Answer input. The original Answer V1
parser/validator remains authoritative after generation.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .model_adapter import GenerationAdapter, default_adapter


CONSTRAINT_VERSION = "ANSWER_V1_CONSTRAINED_DECODING_V1"


def _support_payload(messages: list[dict[str, str]]) -> dict[str, Any]:
    if not messages or not isinstance(messages[-1].get("content"), str):
        raise ValueError("constrained decoding requires the frozen Answer user message")
    content = messages[-1]["content"]
    try:
        body = content.split("<support_data>\n", 1)[1].split("\n</support_data>", 1)[0]
        payload = json.loads(body)
    except (IndexError, json.JSONDecodeError) as exc:
        raise ValueError("constrained decoding could not read the structured support input") from exc
    points = payload.get("allowed_required_points")
    if not isinstance(points, list) or not points:
        raise ValueError("constrained decoding requires at least one allowed required point")
    if not isinstance(payload.get("required_answer_status"), str):
        raise ValueError("constrained decoding requires the expected Answer status")
    return payload


def build_runtime_schema(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Build a shape/support inventory schema from the current Answer input."""
    payload = _support_payload(messages)
    variants: list[dict[str, Any]] = []
    for point in payload["allowed_required_points"]:
        point_id = point.get("required_point_id")
        support_units = point.get("support_units")
        if not isinstance(point_id, str) or not isinstance(support_units, list) or not support_units:
            raise ValueError("constrained decoding received an incomplete required-point support inventory")
        support_ids = [row.get("support_unit_id") for row in support_units]
        if any(not isinstance(value, str) or not value for value in support_ids):
            raise ValueError("constrained decoding received an invalid support ID inventory")
        variants.append({
            "type": "object",
            "properties": {
                "required_point_id": {"type": "string", "enum": [point_id]},
                "claim_text": {"type": "string", "minLength": 1},
                "support_unit_ids": {
                    "type": "array",
                    "items": {"type": "string", "enum": support_ids},
                    "minItems": 1,
                    "maxItems": 1,
                    "uniqueItems": True,
                },
            },
            "required": ["required_point_id", "claim_text", "support_unit_ids"],
            "additionalProperties": False,
        })
    count = len(variants)
    return {
        "type": "object",
        "properties": {
            "answer_status": {"type": "string", "enum": [payload["required_answer_status"]]},
            "claims": {"type": "array", "items": {"oneOf": variants}, "minItems": count, "maxItems": count},
        },
        "required": ["answer_status", "claims"],
        "additionalProperties": False,
    }


class ConstrainedDecodingError(RuntimeError):
    pass


class ConstrainedGenerationAdapter:
    """Use llama.cpp native grammar without changing the legacy adapter."""

    constraint_version = CONSTRAINT_VERSION

    def __init__(self, base_adapter: GenerationAdapter | None = None) -> None:
        self.base_adapter = base_adapter or default_adapter()
        self._llm = getattr(self.base_adapter, "_llm", None)
        self.config = getattr(self.base_adapter, "config", None)
        if self._llm is None or not isinstance(self.config, dict):
            raise ConstrainedDecodingError("constrained adapter requires the verified local llama.cpp adapter")

    def generate(self, messages: list[dict[str, str]], timeout_seconds: int) -> dict[str, Any]:
        del timeout_seconds  # caller owns the deadline, as in the legacy adapter
        try:
            import llama_cpp  # type: ignore

            schema = build_runtime_schema(messages)
            grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(schema, ensure_ascii=False), verbose=False)
            decoding = self.config["decoding"]
            started = time.perf_counter()
            response = self._llm.create_chat_completion(
                messages=messages,
                temperature=decoding["temperature"],
                max_tokens=decoding["max_output_tokens"],
                seed=decoding["seed"],
                repeat_penalty=decoding["repeat_penalty"],
                grammar=grammar,
            )
            content = response["choices"][0]["message"]["content"]
        except Exception as exc:
            raise ConstrainedDecodingError(f"constrained generation failed: {type(exc).__name__}: {exc}") from exc
        return {
            "content": content,
            "finish_reason": response["choices"][0].get("finish_reason"),
            "generation_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "raw_output_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "constraint_version": CONSTRAINT_VERSION,
        }


def default_constrained_adapter() -> ConstrainedGenerationAdapter:
    return ConstrainedGenerationAdapter()
