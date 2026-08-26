"""Fail-closed verifier for the approved Answer Prompt Freeze V1.1 contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "experiments" / "answer_v1_prompt_freeze_v1_1" / "manifest" / "answer_v1_prompt_freeze_v1_1_manifest.json"


class AnswerPromptFreezeVerificationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _canonical_authority():
    path = ROOT / "experiments" / "frozen_bundle_v1_1_candidate" / "candidate" / "dense_retriever_v1_portability_adapter.py"
    spec = importlib.util.spec_from_file_location("answer_prompt_canonical_text_authority", path)
    if spec is None or spec.loader is None:
        raise AnswerPromptFreezeVerificationError("CANONICAL_IMPLEMENTATION_MISSING", "approved CANONICAL_TEXT_V1 implementation is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._canonical, module._hash


def verify_answer_prompt_freeze_v1_1(
    *,
    project_root: Path = ROOT,
    manifest_path: Path = CONTRACT,
    canonicalizer: Callable[[Path], bytes] | None = None,
    hasher: Callable[[bytes], str] | None = None,
) -> dict[str, str]:
    """Verify V1.1 metadata and the real working-tree prompt without bypassing it."""
    if not manifest_path.is_file():
        raise AnswerPromptFreezeVerificationError("PROMPT_FREEZE_CONTRACT_MISSING", "Prompt Freeze V1.1 manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != "ANSWER_V1_PROMPT_FREEZE_V1.1" or manifest.get("status") != "APPROVED":
        raise AnswerPromptFreezeVerificationError("PROMPT_FREEZE_NOT_APPROVED", "Prompt Freeze V1.1 is not approved")
    if manifest.get("semantic_content_changed") is not False or manifest.get("text_hash_mode") != "CANONICAL_TEXT_V1":
        raise AnswerPromptFreezeVerificationError("PROMPT_FREEZE_CONTRACT_INVALID", "Prompt Freeze V1.1 metadata is incompatible")
    canonical, digest = (canonicalizer, hasher) if canonicalizer and hasher else _canonical_authority()
    artifacts = manifest.get("prompt_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise AnswerPromptFreezeVerificationError("PROMPT_ARTIFACTS_INVALID", "Prompt Freeze V1.1 has no prompt artifacts")
    verified = []
    for artifact in artifacts:
        relative = artifact.get("path")
        expected = artifact.get("expected_canonical_sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise AnswerPromptFreezeVerificationError("PROMPT_ARTIFACTS_INVALID", "Prompt Freeze V1.1 artifact record is incomplete")
        path = project_root / relative
        if not path.is_file():
            raise AnswerPromptFreezeVerificationError("PROMPT_MISSING", f"frozen prompt is missing: {relative}")
        try:
            actual = digest(canonical(path))
        except UnicodeDecodeError as exc:
            raise AnswerPromptFreezeVerificationError("PROMPT_ENCODING_INVALID", f"frozen prompt is not strict UTF-8: {relative}") from exc
        if actual != expected:
            raise AnswerPromptFreezeVerificationError("PROMPT_CANONICAL_HASH_MISMATCH", f"frozen prompt content differs: {relative}")
        verified.append(relative)
    return {"version": manifest["version"], "text_hash_mode": manifest["text_hash_mode"], "verified_artifacts": ",".join(verified)}
