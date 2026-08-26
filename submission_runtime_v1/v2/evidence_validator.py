"""Deterministic, fail-closed validator for Submission Runtime V2."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class EvidenceStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class ValidationResult:
    status: EvidenceStatus
    requested_points: tuple[str, ...]
    supported_points: tuple[str, ...]
    missing_points: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    valid: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "requested_points": list(self.requested_points),
            "supported_points": list(self.supported_points),
            "missing_points": list(self.missing_points),
            "evidence_ids": list(self.evidence_ids),
            "reason_codes": list(self.reason_codes),
            "valid": self.valid,
        }


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a list of strings")
    return tuple(item.strip() for item in value if item.strip())


def _fail(code: str) -> ValidationResult:
    return ValidationResult(
        status=EvidenceStatus.INSUFFICIENT,
        requested_points=(),
        supported_points=(),
        missing_points=(),
        evidence_ids=(),
        reason_codes=(code,),
        valid=False,
    )


def validate_payload(
    payload: str | Mapping[str, Any], available_evidence_ids: Iterable[str]
) -> ValidationResult:
    """Validate a judge payload and fail closed on every malformed condition."""

    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _fail("VALIDATOR_JSON_PARSE_FAILURE")

    try:
        status = EvidenceStatus(data.get("status"))
        requested = _strings(data.get("requested_points"))
        supported = _strings(data.get("supported_points"))
        missing = _strings(data.get("missing_points"))
        evidence_ids = _strings(data.get("evidence_ids"))
        reasons = _strings(data.get("reason_codes", []))
    except (TypeError, ValueError):
        return _fail("VALIDATOR_SCHEMA_FAILURE")

    available = set(available_evidence_ids)
    if not set(evidence_ids).issubset(available):
        return _fail("VALIDATOR_UNKNOWN_EVIDENCE_ID")
    if not requested:
        return _fail("VALIDATOR_REQUESTED_POINTS_EMPTY")
    if status is EvidenceStatus.SUFFICIENT and (not supported or missing):
        return _fail("VALIDATOR_SUFFICIENT_INVARIANT")
    if status is EvidenceStatus.PARTIAL and (not supported or not missing or not evidence_ids):
        return _fail("VALIDATOR_PARTIAL_INVARIANT")
    if status is EvidenceStatus.INSUFFICIENT and (supported or evidence_ids):
        return _fail("VALIDATOR_INSUFFICIENT_FALSE_SUPPORT")

    return ValidationResult(
        status=status,
        requested_points=requested,
        supported_points=supported,
        missing_points=missing,
        evidence_ids=evidence_ids,
        reason_codes=reasons,
        valid=True,
    )


def main() -> int:
    import sys

    raw = sys.stdin.read()
    result = validate_payload(raw, ())
    print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if result.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
