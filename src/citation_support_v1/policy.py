from __future__ import annotations


def support_gate(
    evidence_decision: str,
    mapped_point_count: int,
    required_point_count: int,
    integrity_blocked: bool,
) -> tuple[str, list[str]]:
    """Apply the frozen one-way Evidence-to-Support gate."""
    if evidence_decision == "INSUFFICIENT":
        return "BLOCKED", ["EVIDENCE_DECISION_BLOCKED"]
    if evidence_decision == "PARTIAL" and mapped_point_count == 0:
        return "BLOCKED", ["EMPTY_SUPPORT", "SUPPORT_INTEGRITY_BLOCKED"]
    if evidence_decision == "SUFFICIENT" and (
        required_point_count == 0 or mapped_point_count != required_point_count
    ):
        return "BLOCKED", ["REQUIRED_POINT_UNMAPPED", "SUPPORT_INTEGRITY_BLOCKED"]
    if integrity_blocked:
        return "BLOCKED", ["SUPPORT_INTEGRITY_BLOCKED"]
    if evidence_decision == "SUFFICIENT":
        return "READY", ["READY_FOR_ANSWER"]
    if evidence_decision == "PARTIAL":
        return "PARTIAL", ["PARTIAL_SUPPORT_ONLY"]
    return "BLOCKED", ["INPUT_SCHEMA_INVALID", "SUPPORT_INTEGRITY_BLOCKED"]
