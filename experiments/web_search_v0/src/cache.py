from __future__ import annotations
import hashlib, json
from pathlib import Path
from datetime import datetime, timezone

class JsonCache:
    def __init__(self, directory: Path): self.directory = directory; directory.mkdir(parents=True, exist_ok=True)
    def _path(self, payload: dict) -> Path:
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return self.directory / f"{digest}.json"
    def get(self, payload: dict):
        path = self._path(payload)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    def put(self, payload: dict, value: dict):
        value = {"retrieved_at": datetime.now(timezone.utc).isoformat(), **value}
        self._path(payload).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        return value
