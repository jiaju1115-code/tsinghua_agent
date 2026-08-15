from __future__ import annotations

from typing import Final


VERSION: Final = "CITATION_SUPPORT_V1"
EXPECTED_EVIDENCE: Final = "EVIDENCE_SUFFICIENCY_V1"
EXPECTED_RETRIEVER: Final = "RAG_RETRIEVAL_V1"
EXPECTED_CORPUS: Final = "KNOWLEDGE_BASE_V1"

SUPPORT_STATUSES: Final = ("READY", "PARTIAL", "BLOCKED")
MAPPING_STATUSES: Final = ("SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED")
EVIDENCE_DECISIONS: Final = ("SUFFICIENT", "PARTIAL", "INSUFFICIENT")
EVIDENCE_POINT_STATUSES: Final = ("SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_SUPPORTED", "CONFLICT")
EXPECTED_POLICY_SIGNALS: Final = {
    "SUFFICIENT": "ALLOW_FULL_ANSWER",
    "PARTIAL": "ALLOW_PARTIAL_ANSWER",
    "INSUFFICIENT": "REQUIRE_REFUSAL",
}

REQUIRED_RETRIEVAL_FIELDS: Final = {
    "query", "case_id", "retriever_version", "corpus_version", "ordered_top5_chunks", "error"
}
REQUIRED_CHUNK_FIELDS: Final = {
    "rank", "source_id", "chunk_id", "score", "title", "url", "category", "text"
}
REQUIRED_EVIDENCE_FIELDS: Final = {
    "query", "case_id", "evidence_sufficiency_version", "retriever_version", "corpus_version",
    "decision", "policy_signal", "confidence", "required_points", "supported_points",
    "partially_supported_points", "unsupported_points", "requested_attributes",
    "missing_requested_attributes", "optional_information", "supporting_chunk_ids",
    "supporting_source_ids", "reason_codes", "diagnostics", "latency_ms", "error"
}

EXCLUDED_REASON_CODES: Final = {
    "SPAN_INVALID", "SPAN_NOT_FOUND", "SPAN_TOO_WEAK", "DUPLICATE_SUPPORT",
    "SOURCE_DUPLICATE", "CHUNK_NOT_IN_RETRIEVAL", "SOURCE_ID_MISMATCH",
    "REQUIRED_POINT_UNMAPPED", "EVIDENCE_NOT_SUPPORTED", "EVIDENCE_DECISION_BLOCKED",
    "INPUT_SCHEMA_INVALID", "VERSION_MISMATCH",
}

REASON_CODES: Final = EXCLUDED_REASON_CODES | {
    "READY_FOR_ANSWER", "PARTIAL_SUPPORT_ONLY", "EMPTY_SUPPORT", "POLICY_SIGNAL_MISMATCH",
    "QUERY_CASE_MISMATCH", "SUPPORT_INTEGRITY_BLOCKED", "RESTRICTED_METADATA_SANITIZED",
    "ADJACENT_SUPPORT_MERGED", "CANDIDATES_EXCLUDED",
}

OUTPUT_FIELDS: Final = {
    "query", "case_id", "citation_support_version", "evidence_sufficiency_version",
    "retriever_version", "corpus_version", "evidence_decision", "policy_signal",
    "support_status", "required_point_support", "support_units", "citation_candidates",
    "excluded_candidates", "source_groups", "usable_chunk_ids", "usable_source_ids",
    "reason_codes", "diagnostics", "latency_ms", "error",
}
SUPPORT_UNIT_FIELDS: Final = {
    "support_unit_id", "required_point_ids", "source_id", "chunk_id", "source_title",
    "source_url", "source_class", "category", "span_text", "span_start", "span_end",
    "original_span_texts", "normalized_span_text", "normalization_reasons", "support_role",
    "retriever_rank", "evidence_span_ids", "match_occurrence_count",
}
POINT_MAPPING_FIELDS: Final = {
    "point_id", "point_text", "evidence_point_status", "mapping_status",
    "support_unit_ids", "source_ids", "integrity_issue",
}
CITATION_CANDIDATE_FIELDS: Final = {
    "citation_candidate_id", "source_id", "title", "url", "category", "source_class",
    "retriever_rank", "required_point_ids", "support_unit_ids", "chunk_ids",
}
SOURCE_GROUP_FIELDS: Final = {
    "source_group_id", "source_id", "title", "url", "category", "source_class",
    "retriever_rank", "required_point_ids", "support_unit_ids", "chunk_ids",
}
