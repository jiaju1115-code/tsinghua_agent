from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from src.runtime_v1.freeze_loader_v1_1 import verify_active_freeze_reference


ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "experiments" / "frozen_bundle_v1_1_candidate" / "candidate" / "dense_retriever_v1_portability_adapter.py"


def _approved_adapter_module():
    spec = importlib.util.spec_from_file_location("test_approved_portability_adapter", ADAPTER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_active_reference_has_required_v1_1_hash_modes() -> None:
    assert verify_active_freeze_reference() == {
        "freeze_version": "FROZEN_BUNDLE_V1.1",
        "text_hash_mode": "CANONICAL_TEXT_V1",
        "binary_hash_mode": "RAW_BINARY",
    }


def test_approved_canonical_text_hash_is_line_ending_portable(tmp_path: Path) -> None:
    adapter = _approved_adapter_module()
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b'{"line":"one"}\n{"line":"two"}\n')
    crlf.write_bytes(b'{"line":"one"}\r\n{"line":"two"}\r\n')
    assert adapter._hash(adapter._canonical(lf)) == adapter._hash(adapter._canonical(crlf))


def test_approved_hashing_detects_text_and_binary_mutation(tmp_path: Path) -> None:
    adapter = _approved_adapter_module()
    text = tmp_path / "artifact.jsonl"
    binary = tmp_path / "embeddings.bin"
    text.write_bytes(b'{"value":"original"}\n')
    binary.write_bytes(b"\x00\x01\x02")
    expected_text = adapter._hash(adapter._canonical(text))
    expected_binary = adapter._hash(binary.read_bytes())
    text.write_bytes(b'{"value":"changed"}\n')
    binary.write_bytes(b"\x00\x01\x03")
    assert adapter._hash(adapter._canonical(text)) != expected_text
    assert adapter._hash(binary.read_bytes()) != expected_binary
