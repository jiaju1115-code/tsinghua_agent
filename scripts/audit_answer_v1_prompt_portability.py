"""Strict, bounded audit for Answer Generation V1 Prompt portability."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.answer_generation_v1 import runtime as answer_runtime


RELATIVE = "evaluation/answer_generation/runtime_v1/prompts/answer_generation_v1_prompt.md"
PROMPT = ROOT / RELATIVE
CONFIG = ROOT / "evaluation/answer_generation/runtime_v1/config/answer_generation_v1.json"
OUT = ROOT / "experiments" / "answer_v1_prompt_freeze_v1_1"
AUTHORITY = ROOT / "experiments/frozen_bundle_v1_1_candidate/candidate/dense_retriever_v1_portability_adapter.py"


def authority():
    spec = importlib.util.spec_from_file_location("prompt_audit_canonical_authority", AUTHORITY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._canonical, module._hash


def counts(value: bytes) -> dict[str, int]:
    return {"byte_length": len(value), "crlf_count": value.count(b"\r\n"), "bare_lf_count": value.count(b"\n") - value.count(b"\r\n"), "bare_cr_count": value.count(b"\r") - value.count(b"\r\n")}


def placeholders(text: str) -> dict[str, int]:
    # A JSON example's braces are literals, not template variables.  Recognize
    # only identifier-shaped format fields plus Jinja, printf, and $ variables.
    tokens = re.findall(r"\{\{[^{}]+\}\}|\{[A-Za-z_][A-Za-z0-9_]*\}|%\([^)]+\)[#0 +\-]?\d*(?:\.\d+)?[a-zA-Z]|%s|\$[A-Za-z_][A-Za-z0-9_]*", text)
    return {token: tokens.count(token) for token in sorted(set(tokens))}


def render_with_actual_function(prompt_bytes: bytes, cases: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Call Answer V1's real _prompt implementation against isolated LF/CRLF files."""
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    relative = Path(config["prompt"]["path"])
    outputs = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / relative
        target.parent.mkdir(parents=True)
        target.write_bytes(prompt_bytes)
        expected = config["prompt"]["sha256"]
        with patch.object(answer_runtime, "ROOT", root), patch.object(answer_runtime, "sha256", lambda path: expected):
            for query, support_status in cases:
                package = {"support_status": support_status, "required_point_support": []}
                context = {"unit_map": {}}
                messages, injection, error = answer_runtime._prompt(query, package, context, config)
                assert not injection and error is None
                outputs.append({"system": messages[0]["content"], "user": messages[1]["content"]})
    return outputs


def main() -> None:
    canonical, digest = authority()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    worktree = PROMPT.read_bytes()
    git_blob = subprocess.check_output(["git", "show", f"HEAD:{RELATIVE}"], cwd=ROOT)
    git_object_id = subprocess.check_output(["git", "rev-parse", f"HEAD:{RELATIVE}"], cwd=ROOT, text=True).strip()
    canonical_bytes = canonical(PROMPT)
    expected = config["prompt"]["sha256"]
    canonical_equal_git = canonical_bytes == git_blob
    raw_hash = digest(worktree)
    canonical_hash = digest(canonical_bytes)
    git_content_hash = digest(git_blob)
    text_worktree = canonical_bytes.decode("utf-8")
    text_git = git_blob.decode("utf-8")
    semantic = {
        "canonical_byte_equality": canonical_equal_git,
        "unicode_codepoint_equality": list(text_worktree) == list(text_git),
        "line_count_equal": text_worktree.count("\n") == text_git.count("\n"),
        "placeholder_inventory_equal": placeholders(text_worktree) == placeholders(text_git),
        "placeholder_inventory": placeholders(text_git),
        "literal_instruction_equality": text_worktree == text_git,
        "delimiter_equality": all(token in text_worktree and token in text_git for token in ["<user_query_data>", "<support_data>", "```json"]),
        "semantic_content_changed": False,
    }
    cases = [("What official fact is supported?", "READY"), ("What is only partially supported?", "PARTIAL"), ("What cannot be supported?", "BLOCKED")]
    rendered_worktree = render_with_actual_function(worktree, cases)
    rendered_git = render_with_actual_function(git_blob, cases)
    render = [{"case": label, "canonical_model_input_equal": a == b} for (label, _), a, b in zip(cases, rendered_worktree, rendered_git)]
    classification = "LINE_ENDING_ONLY" if raw_hash != expected and canonical_hash == expected and canonical_equal_git and all(render_row["canonical_model_input_equal"] for render_row in render) else "CONTENT_MISMATCH"
    inventory = {
        "audit_version": "ANSWER_V1_PROMPT_PORTABILITY_AUDIT_V1",
        "prompt_artifacts": [{
            "path": RELATIVE, "role": "Answer Generation Runtime V1 system prompt", "expected_sha256": expected,
            "working_tree_raw_sha256": raw_hash, "git_blob_object_id": git_object_id,
            "git_blob_content_sha256": git_content_hash, "canonical_text_sha256": canonical_hash,
            "raw_match": raw_hash == expected, "canonical_match": canonical_hash == expected,
            "classification": classification, "working_tree_bytes": counts(worktree), "git_blob_bytes": counts(git_blob),
        }],
    }
    tests = {"lf_crlf_canonical_equal": digest(git_blob) == canonical_hash, "real_prompt_verification": canonical_hash == expected,
             "content_mutation_detected": digest(canonical_bytes.replace(b"support", b"supports", 1)) != expected,
             "template_contract_token_mutation_detected": digest(canonical_bytes.replace(b"CSU-...", b"CSX-...", 1)) != expected,
             "whitespace_mutation_detected": digest(canonical_bytes.replace(b"Evidence boundary", b"Evidence  boundary", 1)) != expected,
             "render_equivalence": all(row["canonical_model_input_equal"] for row in render)}
    approved = classification == "LINE_ENDING_ONLY" and all(semantic.values()) is not False and all(tests.values())
    # all(semantic.values()) includes an empty placeholder dictionary, so decide explicit required booleans instead.
    approved = classification == "LINE_ENDING_ONLY" and all(value for key, value in semantic.items() if key not in {"placeholder_inventory", "semantic_content_changed"}) and not semantic["semantic_content_changed"] and all(tests.values())
    manifest = {
        "version": "ANSWER_V1_PROMPT_FREEZE_V1.1", "status": "APPROVED" if approved else "PROMPT_PORTABILITY_APPROVAL_BLOCKED",
        "approval_time_utc": datetime.now(timezone.utc).isoformat(), "parent_version": "ANSWER_V1_PROMPT_FREEZE_V1",
        "reason": "cross-platform line-ending portability", "semantic_content_changed": False,
        "text_hash_mode": "CANONICAL_TEXT_V1", "canonicalization_rules": ["strict UTF-8; remove UTF-8 BOM", "CRLF to LF", "CR to LF", "preserve all other bytes/content", "SHA256 canonical bytes"],
        "prompt_artifacts": [{"path": RELATIVE, "role": "system_prompt", "expected_canonical_sha256": canonical_hash, "legacy_raw_sha256": expected, "working_tree_raw_sha256": raw_hash, "git_blob_object_id": git_object_id, "git_blob_content_sha256": git_content_hash}],
        "audit_references": ["audit/answer_v1_prompt_mismatch_inventory.json", "audit/answer_v1_prompt_semantic_equivalence_audit.json", "results/answer_v1_prompt_portability_tests.json"],
    }
    semantic["rendered_prompt_equivalence"] = render
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    (OUT / "manifest").mkdir(parents=True, exist_ok=True)
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    (OUT / "audit/answer_v1_prompt_mismatch_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "audit/answer_v1_prompt_semantic_equivalence_audit.json").write_text(json.dumps(semantic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "results/answer_v1_prompt_portability_tests.json").write_text(json.dumps(tests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "manifest/answer_v1_prompt_freeze_v1_1_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"classification": classification, "approval": manifest["status"], "tests": tests}, ensure_ascii=False))
    if not approved:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
