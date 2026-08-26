"""Thin user-facing orchestration for the frozen Runtime V1 chain."""

from __future__ import annotations

import copy
import uuid
from typing import Any

from src.answer_generation_v1 import generate_answer
from src.answer_generation_v1.constrained_decoding_v1 import CONSTRAINT_VERSION, default_constrained_adapter
from src.citation_support_v1 import build_support_package
from src.e2e_orchestrator_v1 import UnifiedE2EOrchestratorV1
from src.evidence_sufficiency_v1 import evaluate_evidence

from .answer_prompt_freeze_v1_1 import AnswerPromptFreezeVerificationError, verify_answer_prompt_freeze_v1_1
from .freeze_loader_v1_1 import FreezeVerificationError, build_dense_retriever_v1, verify_active_freeze_reference


RUNTIME_VERSION = "RUNTIME_V1"


class RuntimeV1Error(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def _failure(query: Any, request_id: str | None, code: str, message: str) -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "query": query,
        "request_id": request_id,
        "answer": "",
        "status": "RUNTIME_ERROR",
        "retrieval": None,
        "evidence": None,
        "citation": None,
        "refusal": {"refused": True, "reason_codes": [code], "message": message},
        "diagnostics": {"error": {"code": code, "message": message}},
    }


class RuntimeV1:
    """Reusable user-facing façade over the already-frozen V1 runtimes."""

    def __init__(self, model_adapter: Any | None = None) -> None:
        try:
            self.freeze = verify_active_freeze_reference()
            self.retriever = build_dense_retriever_v1()
            self.answer_prompt_freeze = verify_answer_prompt_freeze_v1_1()
        except (FreezeVerificationError, AnswerPromptFreezeVerificationError) as exc:
            raise RuntimeV1Error(exc.code, exc.message) from exc
        self.model_adapter = model_adapter if model_adapter is not None else default_constrained_adapter()
        self.answer_generation_constraint = CONSTRAINT_VERSION if model_adapter is None else None

    def answer_query(self, query: str, request_id: str | None = None) -> dict[str, Any]:
        case_id = request_id or f"runtime-v1-{uuid.uuid4()}"
        if not isinstance(query, str) or not query.strip():
            return _failure(query, case_id, "INPUT_SCHEMA_INVALID", "query must be a non-empty string")

        captured: dict[str, Any] = {"retrieval": None, "evidence": None, "citation": None, "answer": None}

        def retrieve(value: str, identifier: str) -> dict[str, Any]:
            result = self.retriever.retrieve(value, identifier)
            captured["retrieval"] = copy.deepcopy(result)
            return result

        class _CapturedRetriever:
            def retrieve(self, value: str, identifier: str) -> dict[str, Any]:
                return retrieve(value, identifier)

        def evidence(value: str, identifier: str, retrieval_result: dict[str, Any]) -> dict[str, Any]:
            result = evaluate_evidence(value, identifier, retrieval_result)
            captured["evidence"] = copy.deepcopy(result)
            return result

        def citation(value: str, identifier: str, retrieval_result: dict[str, Any], evidence_result: dict[str, Any]) -> dict[str, Any]:
            result = build_support_package(value, identifier, retrieval_result, evidence_result)
            captured["citation"] = copy.deepcopy(result)
            return result

        def answer(value: str, identifier: str, support_package: dict[str, Any], adapter: Any | None) -> dict[str, Any]:
            result = generate_answer(
                value, identifier, support_package, adapter,
                prompt_verifier=verify_answer_prompt_freeze_v1_1,
                decoding_constraint=self.answer_generation_constraint,
            )
            captured["answer"] = copy.deepcopy(result)
            return result

        orchestrator = UnifiedE2EOrchestratorV1(
            retriever=_CapturedRetriever(), evidence_runtime=evidence, citation_runtime=citation,
            answer_runtime=answer, model_adapter=self.model_adapter,
        )
        result = orchestrator.run_e2e(query, case_id)
        answer_result = captured["answer"]
        refusal_codes = [] if not isinstance(answer_result, dict) else [
            code for code in answer_result.get("reason_codes", [])
            if code in {"SUPPORT_BLOCKED", "PROMPT_INJECTION_GUARD", "MODEL_NOT_CALLED", "UPSTREAM_BLOCKED"}
        ]
        return {
            "runtime_version": RUNTIME_VERSION,
            "query": query,
            "request_id": case_id,
            "answer": result["final_answer"],
            "status": result["orchestrator_status"],
            "retrieval": captured["retrieval"],
            "evidence": captured["evidence"],
            "citation": captured["citation"],
            "refusal": {
                "refused": result["answer_status"] in {"REFUSAL", "ERROR"},
                "reason_codes": refusal_codes,
                "message": result.get("error"),
            },
            "diagnostics": {
                "freeze": self.freeze,
                "answer_prompt_freeze": self.answer_prompt_freeze,
                "orchestrator": result,
                "answer_runtime": answer_result,
            },
        }


def answer_query(query: str, request_id: str | None = None, model_adapter: Any | None = None) -> dict[str, Any]:
    """One-shot public Runtime V1 API; callers need not know about run_e2e."""
    try:
        return RuntimeV1(model_adapter=model_adapter).answer_query(query, request_id=request_id)
    except RuntimeV1Error as exc:
        return _failure(query, request_id, exc.code, exc.message)
