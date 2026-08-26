"""User-facing Runtime V1 entrypoint for the frozen Dense V1 chain."""

from .runtime import RuntimeV1, RuntimeV1Error, answer_query

__all__ = ["RuntimeV1", "RuntimeV1Error", "answer_query"]
