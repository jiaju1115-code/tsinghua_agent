from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "evaluation" / "answer_generation" / "runtime_v1" / "config" / "answer_generation_v1.json"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_answer_status(support_status: str, config: dict[str, Any]) -> str:
    return config["answer_status_policy"].get(support_status, "REFUSAL")


def contains_injection(text: str, config: dict[str, Any]) -> bool:
    value = text or ""
    return any(re.search(re.escape(pattern), value, flags=re.IGNORECASE) for pattern in config["injection_patterns"])


def redact_injection(text: str, config: dict[str, Any]) -> tuple[str, bool]:
    value = text or ""
    changed = False
    for pattern in config["injection_patterns"]:
        updated, count = re.subn(re.escape(pattern), "[UNTRUSTED_INSTRUCTION_REDACTED]", value, flags=re.IGNORECASE)
        value = updated
        changed = changed or count > 0
    return value, changed


def stable_id(prefix: str, payload: str) -> str:
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16].upper()}"
