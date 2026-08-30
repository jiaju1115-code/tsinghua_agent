from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


def redact(text: str) -> str:
    text = re.sub(r"(?<!\d)\d{10,14}(?!\d)", "[ID_REDACTED]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL_REDACTED]", text)
    text = re.sub(r"1[3-9]\d{9}", "[PHONE_REDACTED]", text)
    return text


class TraceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def append(self, result: dict[str, Any], *, session_id: str) -> None:
        response = result.get("response", {})
        row = {
            "at": datetime.now().astimezone().isoformat(), "case_id": result.get("case_id"),
            "session_id": session_id, "query": redact(str(result.get("query", ""))),
            "path": result.get("path"), "evidence_status": result.get("evidence_status"),
            "stage_latency_ms": result.get("stage_latency_ms"), "total_latency_ms": result.get("total_latency_ms"),
            "source_ids": [item.get("source_id") for item in response.get("citations", [])],
            "clarification_count": len(response.get("clarification_questions") or []),
            "tool_route": result.get("tool_route"), "artifact": bool(result.get("artifact")),
        }
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def get(self, case_id: str) -> dict[str, Any] | None:
        if not self.path.is_file():
            return None
        for line in reversed(self.path.read_text(encoding="utf-8").splitlines()):
            row = json.loads(line)
            if row.get("case_id") == case_id:
                return row
        return None

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 200)):]
        return [json.loads(line) for line in reversed(lines)]
