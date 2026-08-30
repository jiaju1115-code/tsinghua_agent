from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class SessionStore:
    """Small local conversation state store; no uploaded content is persisted here."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, session_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", session_id):
            raise ValueError("invalid session id")
        return self.root / f"{session_id}.json"

    def create(self) -> dict[str, Any]:
        session_id = uuid.uuid4().hex
        value = {"session_id": session_id, "profile": {}, "active_intent": "", "pending_questions": [], "events": [], "updated_at": datetime.now().astimezone().isoformat()}
        self.save(value)
        return value

    def load(self, session_id: str | None) -> dict[str, Any]:
        if not session_id:
            return self.create()
        path = self._path(session_id)
        if not path.is_file():
            return self.create()
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, value: dict[str, Any]) -> None:
        value["updated_at"] = datetime.now().astimezone().isoformat()
        path = self._path(value["session_id"])
        temp = path.with_suffix(".tmp")
        with self._lock:
            temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(path)

    @staticmethod
    def extract_profile(query: str) -> dict[str, str]:
        profile: dict[str, str] = {}
        for marker, value in (("本科生", "本科生"), ("本科", "本科生"), ("硕士", "研究生"), ("博士", "博士生"), ("研究生", "研究生"), ("国际学生", "国际学生"), ("毕业生", "毕业生"), ("新生", "新生")):
            if marker in query:
                profile["audience"] = value
                break
        term = re.search(r"(20\d{2}(?:[-—]20\d{2})?学年(?:春季|秋季)?学期?|20\d{2}年(?:春季|秋季)学期|(?:本|下|上)学期|春季学期|秋季学期)", query)
        if term:
            profile["term"] = term.group(1)
        target = re.search(r"(?:转入|目标(?:院系|专业)?(?:是|为|：)?)([\u4e00-\u9fffA-Za-z0-9·]{2,20}(?:学院|系|专业))", query)
        if target:
            profile["target_department"] = target.group(1)
        current = re.search(r"(?:来自|现在在|当前(?:院系)?(?:是|为|：)?)([\u4e00-\u9fffA-Za-z0-9·]{2,20}(?:学院|系|专业))", query)
        if current:
            profile["department"] = current.group(1)
        program = re.search(r"((?:校级|院系级|院级)[\u4e00-\u9fffA-Za-z0-9·]{0,20}(?:交换)?项目)", query)
        if program:
            profile["program"] = program.group(1)
        return profile

    def prepare_query(self, state: dict[str, Any], message: str) -> tuple[str, dict[str, Any]]:
        pending = state.get("pending_questions") or []
        extracted = self.extract_profile(message)
        pending_text = " ".join(pending)
        compact = message.strip().rstrip("。；;，,")
        if "当前院系和目标院系" in pending_text:
            pair = re.search(r"([\u4e00-\u9fffA-Za-z0-9·]{2,20}(?:学院|系|专业))\s*(?:转|到|->|→)\s*([\u4e00-\u9fffA-Za-z0-9·]{2,20}(?:学院|系|专业))", compact)
            if pair:
                extracted.setdefault("department", pair.group(1))
                extracted.setdefault("target_department", pair.group(2))
            elif re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9·]{2,20}(?:学院|系|专业)", compact):
                extracted.setdefault("target_department", compact)
        if "哪个学年" in pending_text and "term" not in extracted and len(compact) <= 30:
            extracted["term"] = compact
        if "交换项目" in pending_text and "program" not in extracted and len(compact) <= 40:
            extracted["program"] = compact
        state["profile"].update(extracted)
        active = state.get("active_intent", "")
        is_short_answer = bool(pending and active and len(message) <= 80 and not any(mark in message for mark in "？?"))
        effective = f"{active}。补充信息：{message}" if is_short_answer else message
        return effective, dict(state["profile"])

    def record(self, state: dict[str, Any], *, user_message: str, effective_query: str, result: dict[str, Any]) -> None:
        response = result.get("response", {})
        questions = response.get("clarification_questions") or []
        state["pending_questions"] = questions
        base_intent = effective_query.split("。补充信息：", 1)[0]
        state["active_intent"] = base_intent if questions else ""
        state["events"] = (state.get("events") or [])[-18:] + [{
            "at": datetime.now().astimezone().isoformat(), "user": user_message[:1000],
            "case_id": result.get("case_id"), "evidence_status": result.get("evidence_status"),
        }]
        self.save(state)
