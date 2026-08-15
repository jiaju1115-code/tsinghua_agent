from __future__ import annotations

from typing import Final


VERSION: Final = "ANSWER_GENERATION_V1"
EXPECTED_CITATION_SUPPORT: Final = "CITATION_SUPPORT_V1"
EXPECTED_EVIDENCE: Final = "EVIDENCE_SUFFICIENCY_V1"
EXPECTED_RETRIEVER: Final = "RAG_RETRIEVAL_V1"
EXPECTED_CORPUS: Final = "KNOWLEDGE_BASE_V1"

SUPPORT_STATUSES: Final = ("READY", "PARTIAL", "BLOCKED")
ANSWER_STATUSES: Final = ("FULL_ANSWER", "PARTIAL_ANSWER", "REFUSAL")
CLAIM_TYPES: Final = ("FACTUAL", "LIMITATION", "REFUSAL", "OTHER")

OUTPUT_FIELDS: Final = {
    "query", "case_id", "answer_generation_version", "citation_support_version",
    "evidence_sufficiency_version", "retriever_version", "corpus_version",
    "support_status", "answer_status", "answer_text", "answered_required_point_ids",
    "unanswered_required_point_ids", "used_support_unit_ids", "used_source_ids",
    "claim_records", "reason_codes", "diagnostics", "latency_ms", "error",
}
CLAIM_RECORD_FIELDS: Final = {
    "claim_id", "claim_text", "claim_type", "required_point_ids",
    "support_unit_ids", "source_ids",
}
MODEL_OUTPUT_FIELDS: Final = {"answer_status", "claims"}
MODEL_CLAIM_FIELDS: Final = {"required_point_id", "claim_text", "support_unit_ids"}

REASON_CODES: Final = {
    "ANSWER_SCHEMA_INVALID", "ANSWER_STATUS_MISMATCH", "EMPTY_GENERATION", "FULL_ANSWER_GENERATED",
    "GENERATION_ERROR", "GENERATION_TIMEOUT", "INPUT_SCHEMA_INVALID", "INVALID_SOURCE_REFERENCE",
    "INVALID_SUPPORT_REFERENCE", "LEXICAL_TRACE_FAILED", "LEXICAL_TRACE_REPAIRED", "MODEL_CALLED", "MODEL_LOAD_ERROR",
    "MODEL_NOT_CALLED", "MODEL_OUTPUT_INVALID", "NON_SEMANTIC_SUPPORT_VALIDATION",
    "NO_SUPPORTED_CONTENT", "OUTPUT_TOO_LONG", "PARTIAL_ANSWER_GENERATED", "PARTIAL_SCOPE_VIOLATION",
    "PROMPT_INJECTION_GUARD", "READY_SCOPE_INCOMPLETE", "RESTRICTED_METADATA_SANITIZED",
    "SAFE_REFUSAL", "SUPPORT_BLOCKED", "SUPPORT_PARTIAL", "SUPPORT_READY",
    "UNATTRIBUTED_FACTUAL_CLAIM", "UPSTREAM_BLOCKED", "VERSION_MISMATCH",
}

MODEL_RESPONSE_JSON_SCHEMA: Final = {
    "type": "object",
    "properties": {
        "answer_status": {"type": "string", "enum": ["FULL_ANSWER", "PARTIAL_ANSWER"]},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "required_point_id": {"type": "string"},
                    "claim_text": {"type": "string"},
                    "support_unit_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["required_point_id", "claim_text", "support_unit_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answer_status", "claims"],
    "additionalProperties": False,
}
