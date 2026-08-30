from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class TaskWorkspaceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.is_file():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, value: dict[str, list[dict[str, Any]]]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def merge_action_plan(self, session_id: str, action_plan: dict[str, list[str]] | None, case_id: str | None) -> list[dict[str, Any]]:
        if not action_plan:
            return self.list(session_id)
        with self._lock:
            data = self._load()
            tasks = data.setdefault(session_id, [])
            existing = {item["text"] for item in tasks}
            for category in ("conditions", "materials", "steps", "deadlines"):
                for text in action_plan.get(category, []):
                    if text in existing:
                        continue
                    deadline = re.search(r"(?:20\d{2}年)?(\d{1,2})月(\d{1,2})日", text)
                    tasks.append({
                        "task_id": uuid.uuid4().hex, "category": category, "text": text,
                        "status": "todo", "deadline": deadline.group(0) if deadline else None,
                        "source_case_id": case_id, "created_at": datetime.now().astimezone().isoformat(),
                    })
                    existing.add(text)
            data[session_id] = tasks[-200:]
            self._save(data)
            return data[session_id]

    def list(self, session_id: str) -> list[dict[str, Any]]:
        return self._load().get(session_id, [])

    def update(self, session_id: str, task_id: str, status: str) -> dict[str, Any]:
        if status not in {"todo", "doing", "done"}:
            raise ValueError("invalid task status")
        with self._lock:
            data = self._load()
            for task in data.get(session_id, []):
                if task["task_id"] == task_id:
                    task["status"] = status
                    task["updated_at"] = datetime.now().astimezone().isoformat()
                    self._save(data)
                    return task
        raise KeyError(task_id)

    def to_ics(self, session_id: str) -> str:
        events = []
        for task in self.list(session_id):
            match = re.search(r"(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日", task.get("deadline") or "")
            if not match:
                continue
            year = int(match.group(1) or datetime.now().year)
            day = f"{year:04d}{int(match.group(2)):02d}{int(match.group(3)):02d}"
            events.extend(["BEGIN:VEVENT", f"UID:{task['task_id']}@tsingask.local", f"DTSTART;VALUE=DATE:{day}", f"SUMMARY:{task['text'][:120]}", "END:VEVENT"])
        return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TsingAsk V2//CN", *events, "END:VCALENDAR", ""])
