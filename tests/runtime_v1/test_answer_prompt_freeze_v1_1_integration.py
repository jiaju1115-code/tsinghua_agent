from __future__ import annotations

from src.answer_generation_v1 import runtime as answer_runtime
from src.answer_generation_v1.policy import load_config
import importlib.util
import json
from pathlib import Path

import pytest

from src.runtime_v1.answer_prompt_freeze_v1_1 import AnswerPromptFreezeVerificationError, verify_answer_prompt_freeze_v1_1


def test_legacy_default_raw_verifier_remains_available() -> None:
    messages, injected, error = answer_runtime._prompt(
        "legacy replay", {"support_status": "PARTIAL", "required_point_support": []}, {"unit_map": {}}, load_config()
    )
    assert messages == []
    assert injected is False
    assert error == "frozen prompt file is missing or has a hash mismatch"


def test_runtime_v1_can_explicitly_consume_approved_prompt_verifier() -> None:
    messages, injected, error = answer_runtime._prompt(
        "versioned runtime", {"support_status": "PARTIAL", "required_point_support": []}, {"unit_map": {}}, load_config(),
        prompt_verifier=verify_answer_prompt_freeze_v1_1,
    )
    assert error is None
    assert injected is False
    assert [message["role"] for message in messages] == ["system", "user"]


def test_versioned_verifier_failure_stays_fail_closed() -> None:
    def rejected() -> dict[str, str]:
        raise RuntimeError("simulated prompt mutation")

    messages, injected, error = answer_runtime._prompt(
        "verification failure", {"support_status": "PARTIAL", "required_point_support": []}, {"unit_map": {}}, load_config(),
        prompt_verifier=rejected,
    )
    assert messages == []
    assert injected is False
    assert error and error.startswith("versioned prompt freeze verification failed:")


def _authority():
    root = Path(__file__).resolve().parents[2]
    source = root / "experiments/frozen_bundle_v1_1_candidate/candidate/dense_retriever_v1_portability_adapter.py"
    spec = importlib.util.spec_from_file_location("prompt_verifier_test_authority", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._canonical, module._hash


def _manifest(relative: str, digest: str) -> dict:
    return {"version": "ANSWER_V1_PROMPT_FREEZE_V1.1", "status": "APPROVED", "semantic_content_changed": False,
            "text_hash_mode": "CANONICAL_TEXT_V1", "prompt_artifacts": [{"path": relative, "expected_canonical_sha256": digest}]}


def test_verifier_rejects_mutation_missing_prompt_and_invalid_utf8(tmp_path: Path) -> None:
    canonical, digest = _authority()
    relative = "prompts/prompt.md"
    prompt = tmp_path / relative
    prompt.parent.mkdir()
    prompt.write_bytes(b"line one\r\nline two\r\n")
    expected = digest(canonical(prompt))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest(relative, expected)), encoding="utf-8")
    assert verify_answer_prompt_freeze_v1_1(project_root=tmp_path, manifest_path=manifest, canonicalizer=canonical, hasher=digest)["version"] == "ANSWER_V1_PROMPT_FREEZE_V1.1"
    prompt.write_bytes(b"line changed\r\nline two\r\n")
    with pytest.raises(AnswerPromptFreezeVerificationError) as exc_info:
        verify_answer_prompt_freeze_v1_1(project_root=tmp_path, manifest_path=manifest, canonicalizer=canonical, hasher=digest)
    assert exc_info.value.code == "PROMPT_CANONICAL_HASH_MISMATCH"
    prompt.unlink()
    with pytest.raises(AnswerPromptFreezeVerificationError) as exc_info:
        verify_answer_prompt_freeze_v1_1(project_root=tmp_path, manifest_path=manifest, canonicalizer=canonical, hasher=digest)
    assert exc_info.value.code == "PROMPT_MISSING"
    prompt.write_bytes(b"\xff\xfeinvalid")
    with pytest.raises(AnswerPromptFreezeVerificationError) as exc_info:
        verify_answer_prompt_freeze_v1_1(project_root=tmp_path, manifest_path=manifest, canonicalizer=canonical, hasher=digest)
    assert exc_info.value.code == "PROMPT_ENCODING_INVALID"
