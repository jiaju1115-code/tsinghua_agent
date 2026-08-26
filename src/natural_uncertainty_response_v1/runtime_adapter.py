"""Compatibility adapter from frozen Runtime V1 results to natural response modes."""

from __future__ import annotations

import copy
import uuid
from typing import Any

from src.runtime_v1 import RuntimeV1

from .policy import NaturalResponseSession, ResponseMode


ADAPTER_VERSION = "NATURAL_UNCERTAINTY_RUNTIME_ADAPTER_V1"


class NaturalRuntimeAdapterV1:
    """Routes non-campus turns locally and decorates, never alters, frozen output."""

    def __init__(self, runtime: Any | None = None) -> None:
        self.runtime = runtime if runtime is not None else RuntimeV1()
        self.session = NaturalResponseSession()

    def answer_query(self, query: str, request_id: str | None = None) -> dict[str, Any]:
        request_id = request_id or f"natural-v1-{uuid.uuid4()}"
        preliminary = self.session.preview(query)
        if preliminary["response_mode"] != ResponseMode.UNCERTAIN_WITH_GUIDANCE:
            self.session.turns.append(query)
            return self._local_result(query, request_id, preliminary)

        frozen = self.runtime.answer_query(query, request_id=request_id)
        citation = frozen.get("citation") or {}
        planned = self.session.respond(query, citation)
        orchestrator = frozen.get("diagnostics", {}).get("orchestrator", {}) or {}
        return {
            "runtime_version": ADAPTER_VERSION,
            "query": query,
            "request_id": request_id,
            "answer": planned["answer_text"],
            "response_mode": str(planned["response_mode"]),
            "machine_state": {
                "evidence_status": (frozen.get("evidence") or {}).get("decision"),
                "citation_status": citation.get("support_status"),
                "unsupported_points": copy.deepcopy(planned["unsupported_points"]),
                "support_provenance": copy.deepcopy(orchestrator.get("provenance", [])),
                "reason_codes": copy.deepcopy((frozen.get("diagnostics", {}).get("answer_runtime") or {}).get("reason_codes", [])),
            },
            "citations": planned["citations"],
            "frozen_runtime": frozen,
        }

    @staticmethod
    def _local_result(query: str, request_id: str, planned: dict[str, Any]) -> dict[str, Any]:
        return {
            "runtime_version": ADAPTER_VERSION,
            "query": query,
            "request_id": request_id,
            "answer": planned["answer_text"],
            "response_mode": str(planned["response_mode"]),
            "machine_state": {
                "evidence_status": "NOT_REQUESTED",
                "citation_status": "NOT_REQUESTED",
                "unsupported_points": copy.deepcopy(planned["unsupported_points"]),
                "support_provenance": [],
                "reason_codes": ["LOCAL_RESPONSE_ROUTE"],
            },
            "citations": planned["citations"],
            "frozen_runtime": None,
        }
