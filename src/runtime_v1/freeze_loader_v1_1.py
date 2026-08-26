"""Approved Frozen Bundle V1.1 loader glue.

The canonical text hashing implementation deliberately remains in the approved
portability adapter.  This module validates the active approval reference and
loads that implementation; it does not create a second normalization policy.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "experiments" / "frozen_bundle_v1_1_candidate" / "candidate"
ACTIVE_REFERENCE = CANDIDATE / "active_freeze_reference.json"
APPROVED_MANIFEST = CANDIDATE / "frozen_bundle_v1_1_approved_manifest.json"
PORTABILITY_ADAPTER = CANDIDATE / "dense_retriever_v1_portability_adapter.py"


class FreezeVerificationError(RuntimeError):
    """Fail-closed, machine-readable Frozen Bundle V1.1 load failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FreezeVerificationError("FREEZE_REFERENCE_MISSING", f"required freeze file is missing: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise FreezeVerificationError("FREEZE_REFERENCE_INVALID", f"invalid freeze JSON: {path.name}") from exc


def verify_active_freeze_reference() -> dict[str, str]:
    active = _json(ACTIVE_REFERENCE)
    approved = _json(APPROVED_MANIFEST)
    if active.get("active_freeze") != "FROZEN_BUNDLE_V1.1":
        raise FreezeVerificationError("ACTIVE_FREEZE_MISMATCH", "Runtime V1 requires FROZEN_BUNDLE_V1.1")
    if approved.get("version") != "FROZEN_BUNDLE_V1.1" or approved.get("status") != "APPROVED" or not approved.get("active_reference"):
        raise FreezeVerificationError("FREEZE_NOT_APPROVED", "Frozen Bundle V1.1 is not an approved active reference")
    modes = approved.get("hash_modes")
    if modes != {"text": "CANONICAL_TEXT_V1", "binary": "RAW_BINARY"}:
        raise FreezeVerificationError("HASH_MODE_MISMATCH", "approved freeze hash modes differ from Runtime V1 contract")
    if approved.get("semantic_content_changed") is not False:
        raise FreezeVerificationError("SEMANTIC_FREEZE_MISMATCH", "Runtime V1 only accepts the non-semantic V1.1 portability evolution")
    if not PORTABILITY_ADAPTER.is_file():
        raise FreezeVerificationError("PORTABILITY_ADAPTER_MISSING", "approved portability adapter is missing")
    return {"freeze_version": "FROZEN_BUNDLE_V1.1", "text_hash_mode": "CANONICAL_TEXT_V1", "binary_hash_mode": "RAW_BINARY"}


def _adapter_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("runtime_v1_approved_portability_adapter", PORTABILITY_ADAPTER)
    if spec is None or spec.loader is None:
        raise FreezeVerificationError("PORTABILITY_ADAPTER_LOAD_FAILED", "could not load approved portability adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_dense_retriever_v1():
    """Verify approval metadata then instantiate the approved fail-closed loader."""
    verify_active_freeze_reference()
    try:
        cls = _adapter_module().DenseRetrieverV1PortabilityAdapter
        return cls()
    except FreezeVerificationError:
        raise
    except Exception as exc:
        raise FreezeVerificationError("RETRIEVER_INITIALIZATION_FAILED", f"approved retriever initialization failed: {type(exc).__name__}: {exc}") from exc
