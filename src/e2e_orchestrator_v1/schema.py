from __future__ import annotations

from typing import Final


VERSION: Final = "UNIFIED_E2E_ORCHESTRATOR_V1"
EXPECTED_RETRIEVER: Final = "RAG_RETRIEVAL_V1"
EXPECTED_CORPUS: Final = "KNOWLEDGE_BASE_V1"
EXPECTED_EVIDENCE: Final = "EVIDENCE_SUFFICIENCY_V1"
EXPECTED_CITATION: Final = "CITATION_SUPPORT_V1"
EXPECTED_ANSWER: Final = "ANSWER_GENERATION_V1"

RETRIEVAL_STATUSES: Final = ("SUCCESS", "ERROR", "NOT_RUN")
EVIDENCE_STATUSES: Final = ("SUFFICIENT", "PARTIAL", "INSUFFICIENT", "ERROR", "NOT_RUN")
CITATION_STATUSES: Final = ("READY", "PARTIAL", "BLOCKED", "ERROR", "NOT_RUN")
ANSWER_STATUSES: Final = ("FULL_ANSWER", "PARTIAL_ANSWER", "REFUSAL", "ERROR", "NOT_RUN")
ORCHESTRATOR_STATUSES: Final = ("COMPLETED", "E2E_ERROR")

RETRIEVAL_FIELDS: Final = {
    "query", "case_id", "retriever_version", "corpus_version", "ordered_top5_chunks",
    "source_ids", "chunk_ids", "scores", "latency_ms", "error",
}
RETRIEVAL_CHUNK_FIELDS: Final = {
    "rank", "source_id", "chunk_id", "score", "title", "url", "category", "text",
}

OUTPUT_FIELDS: Final = {
    "query", "case_id", "orchestrator_version", "orchestrator_status",
    "retrieval_status", "evidence_status", "citation_status", "answer_status",
    "final_answer", "answered_required_point_ids", "unanswered_required_point_ids",
    "used_support_unit_ids", "used_source_ids", "claims", "provenance",
    "trace_summary", "layer_latencies_ms", "orchestration_overhead_ms",
    "total_latency_ms", "reason_codes", "error",
}

TRACE_FIELDS: Final = {
    "stage", "status", "version", "reason_codes", "error_code", "latency_ms", "counts",
}

REASON_CODES: Final = {
    "PIPELINE_COMPLETED", "READY_PROPAGATED", "PARTIAL_PROPAGATED", "BLOCKED_PROPAGATED",
    "INPUT_SCHEMA_INVALID", "DUPLICATE_CASE_ID", "RETRIEVAL_ERROR", "EVIDENCE_ERROR",
    "CITATION_ERROR", "ANSWER_ERROR", "VERSION_MISMATCH", "QUERY_CASE_MISMATCH",
    "FROZEN_CONTRACT_CONFLICT", "PROVENANCE_LINK_UNAVAILABLE", "UPSTREAM_FAIL_CLOSED",
    "INJECTION_BOUNDARY_PRESERVED", "RESTRICTED_METADATA_SANITIZED",
}
