from __future__ import annotations

from typing import Final


VERSION: Final = "EVIDENCE_SUFFICIENCY_V1"
EXPECTED_RETRIEVER: Final = "RAG_RETRIEVAL_V1"
EXPECTED_CORPUS: Final = "KNOWLEDGE_BASE_V1"
DECISIONS: Final = ("SUFFICIENT", "PARTIAL", "INSUFFICIENT")
POINT_STATUSES: Final = ("SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_SUPPORTED", "CONFLICT")
POLICY_SIGNALS: Final = {
    "SUFFICIENT": "ALLOW_FULL_ANSWER",
    "PARTIAL": "ALLOW_PARTIAL_ANSWER",
    "INSUFFICIENT": "REQUIRE_REFUSAL",
}

OUTPUT_FIELDS: Final = {
    "query",
    "case_id",
    "evidence_sufficiency_version",
    "retriever_version",
    "corpus_version",
    "decision",
    "policy_signal",
    "confidence",
    "required_points",
    "supported_points",
    "partially_supported_points",
    "unsupported_points",
    "requested_attributes",
    "missing_requested_attributes",
    "optional_information",
    "supporting_chunk_ids",
    "supporting_source_ids",
    "reason_codes",
    "diagnostics",
    "latency_ms",
    "error",
}
