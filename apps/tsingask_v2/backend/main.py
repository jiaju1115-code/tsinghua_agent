from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import re
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2.file_tools import CampusFileService, CampusToolRouter
from src.trusted_campus_agent_v2.local_model import default_local_runtime
from src.trusted_campus_agent_v2.runtime import TrustedCampusAgentV2
from src.trusted_campus_agent_v2.observability import TraceStore, redact
from src.trusted_campus_agent_v2.session import SessionStore
from src.trusted_campus_agent_v2.workspace import TaskWorkspaceStore


APP_ROOT = ROOT / "apps" / "tsingask_v2"
RUNTIME_ROOT = APP_ROOT / ".artifact_runtime"
UPLOAD_ROOT = RUNTIME_ROOT / "uploads"
OUTPUT_ROOT = RUNTIME_ROOT / "outputs"
REGISTRY_PATH = RUNTIME_ROOT / "files.json"
SESSION_STORE = SessionStore(RUNTIME_ROOT / "sessions")
TRACE_STORE = TraceStore(RUNTIME_ROOT / "traces.jsonl")
TASK_STORE = TaskWorkspaceStore(RUNTIME_ROOT / "tasks.json")
FEEDBACK_PATH = RUNTIME_ROOT / "feedback.jsonl"
KB_ROOT = ROOT / "data" / "05_trusted_campus_kb_v2_public"
MAX_UPLOAD = 25 * 1024 * 1024
SUPPORTED = {".docx", ".xlsx", ".pptx", ".pdf"}

for directory in (UPLOAD_ROOT, OUTPUT_ROOT):
    directory.mkdir(parents=True, exist_ok=True)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    upload_ids: list[str] = Field(default_factory=list, max_length=4)
    output_format: str | None = None
    template_key: str | None = None
    use_rag: bool | None = None
    session_id: str | None = None
    retrieval_mode: str = Field(default="auto", pattern="^(auto|fast|full)$")


class TaskUpdate(BaseModel):
    status: str


class FeedbackRequest(BaseModel):
    case_id: str
    kind: str
    detail: str = Field(default="", max_length=2000)


class ReplayRequest(BaseModel):
    session_id: str | None = None


app = FastAPI(title="清问·TsingAsk V2", version="2.0.0", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Any, call_next: Any) -> Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
    return response

_agent: TrustedCampusAgentV2 | None = None
_agent_manifest_mtime_ns: int | None = None
_agent_lock = threading.RLock()
_jobs: dict[str, dict[str, Any]] = {}


def registry() -> dict[str, dict[str, Any]]:
    if not REGISTRY_PATH.is_file():
        return {}
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_registry(value: dict[str, dict[str, Any]]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REGISTRY_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(REGISTRY_PATH)


def safe_record(file_id: str, *, expected_kind: str | None = None) -> dict[str, Any]:
    record = registry().get(file_id)
    if not record or (expected_kind and record.get("kind") != expected_kind):
        raise HTTPException(404, "文件不存在或已失效")
    expires = record.get("expires_at")
    if expires and datetime.fromisoformat(expires) < datetime.now(timezone.utc):
        raise HTTPException(410, "文件已按隐私策略过期")
    path = Path(record["path"]).resolve()
    allowed = UPLOAD_ROOT.resolve() if record.get("kind") == "upload" else OUTPUT_ROOT.resolve()
    if path.parent != allowed or not path.is_file():
        raise HTTPException(404, "文件不存在或已失效")
    return record


def agent() -> TrustedCampusAgentV2:
    global _agent, _agent_manifest_mtime_ns
    manifest = KB_ROOT / "manifest.json"
    mtime = manifest.stat().st_mtime_ns if manifest.is_file() else None
    if _agent is None or mtime != _agent_manifest_mtime_ns:
        with _agent_lock:
            current_mtime = manifest.stat().st_mtime_ns if manifest.is_file() else None
            if _agent is None or current_mtime != _agent_manifest_mtime_ns:
                _agent = TrustedCampusAgentV2(use_public_v2=True, local_model=True)
                _agent_manifest_mtime_ns = current_mtime
    return _agent


def public_result(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    artifact = result.get("artifact")
    if artifact and artifact.get("path"):
        path = Path(artifact["path"]).resolve()
        if path.parent != OUTPUT_ROOT.resolve():
            raise RuntimeError("file tool wrote outside the independent output directory")
        file_id = uuid.uuid4().hex
        records = registry()
        records[file_id] = {
            "kind": "output", "path": str(path), "filename": artifact["filename"], "media_type": artifact["media_type"],
            "created_at": datetime.now(timezone.utc).isoformat(), "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        save_registry(records)
        clean = {key: item for key, item in artifact.items() if key not in {"path", "download_path"}}
        clean["file_id"] = file_id
        clean["download_url"] = f"/api/files/{file_id}"
        result["artifact"] = clean
    retrieval = result.get("retrieval")
    if retrieval:
        retrieval = dict(retrieval)
        retrieval["results"] = [
            {key: row.get(key) for key in ("rank", "source_id", "title", "url", "score", "temporal_status", "metadata")}
            for row in retrieval.get("results", [])
        ]
        result["retrieval"] = retrieval
    return result


@app.get("/api/health")
def health() -> dict[str, Any]:
    manifest = {}
    if (KB_ROOT / "manifest.json").is_file():
        manifest = json.loads((KB_ROOT / "manifest.json").read_text(encoding="utf-8"))
    try:
        model = default_local_runtime().health(load=False)
    except Exception as exc:
        model = {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}
    from src.trusted_campus_agent_v2.hardware import torch_acceleration
    return {
        "status": "READY" if manifest else "DEGRADED",
        "project": "TsingAsk V2 Independent",
        "online_agent_touched": False,
        "knowledge_base": {key: manifest.get(key) for key in ("bundle_version", "source_count", "chunk_count", "dense_index")},
        "model": model,
        "dense_retrieval_acceleration": torch_acceleration(),
    }


@app.get("/api/coverage")
def coverage() -> dict[str, Any]:
    path = KB_ROOT / "coverage_matrix.json"
    if not path.is_file():
        raise HTTPException(503, "新版知识库尚未构建")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/templates")
def templates() -> list[dict[str, Any]]:
    return CampusFileService.templates()


@app.post("/api/sessions")
def create_session() -> dict[str, Any]:
    return SESSION_STORE.create()


@app.post("/api/uploads")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    original = Path(file.filename or "upload").name
    suffix = Path(original).suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(415, "仅支持 docx、xlsx、pptx、pdf")
    payload = await file.read(MAX_UPLOAD + 1)
    if len(payload) > MAX_UPLOAD:
        raise HTTPException(413, "文件不能超过 25 MB")
    file_id = uuid.uuid4().hex
    path = UPLOAD_ROOT / f"{file_id}{suffix}"
    path.write_bytes(payload)
    records = registry()
    records[file_id] = {
        "kind": "upload", "path": str(path), "filename": original,
        "media_type": file.content_type or mimetypes.guess_type(original)[0],
        "created_at": datetime.now(timezone.utc).isoformat(), "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }
    save_registry(records)
    return {"file_id": file_id, "filename": original, "size_bytes": len(payload), "format": suffix.lstrip(".")}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    state = SESSION_STORE.load(request.session_id)
    effective_query, context = SESSION_STORE.prepare_query(state, request.message)
    uploads = [safe_record(file_id, expected_kind="upload")["path"] for file_id in request.upload_ids]
    route = CampusToolRouter().route(effective_query, uploads)
    options: dict[str, Any] = {"include_uploaded_content": True}
    if route.route == "file_tool" and route.action != "read":
        fmt = (request.output_format or route.output_format or "docx").lower().lstrip(".")
        if fmt not in {"docx", "xlsx", "pptx", "pdf"}:
            raise HTTPException(422, "不支持的输出格式")
        options["output_path"] = str(OUTPUT_ROOT / f"{uuid.uuid4().hex}.{fmt}")
        options["output_format"] = fmt
    if request.template_key:
        options["template_key"] = request.template_key
    if request.use_rag is not None:
        options["use_rag"] = request.use_rag
    try:
        path_override = None if request.retrieval_mode == "auto" else request.retrieval_mode.upper()
        value = await asyncio.to_thread(
            agent().handle, effective_query, uploaded_files=uploads, file_options=options,
            context=context, path_override=path_override,
        )
        value["input_message"] = request.message
        value["session_id"] = state["session_id"]
        SESSION_STORE.record(state, user_message=request.message, effective_query=effective_query, result=value)
        response = value.get("response", {})
        tasks = TASK_STORE.merge_action_plan(state["session_id"], response.get("action_plan"), value.get("case_id"))
        value["workspace"] = {"tasks": tasks, "task_count": len(tasks)}
        if value.get("case_id"):
            TRACE_STORE.append(value, session_id=state["session_id"])
        return public_result(value)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"本地智能体执行失败：{type(exc).__name__}: {exc}") from exc


async def _run_job(job_id: str, request: ChatRequest) -> None:
    _jobs[job_id]["status"] = "running"
    try:
        _jobs[job_id]["result"] = await chat(request)
        _jobs[job_id]["status"] = "completed"
    except HTTPException as exc:
        _jobs[job_id].update({"status": "failed", "error": str(exc.detail)})
    except Exception as exc:
        _jobs[job_id].update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
    _jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


@app.post("/api/jobs", status_code=202)
async def create_job(request: ChatRequest) -> dict[str, Any]:
    uploads = [safe_record(file_id, expected_kind="upload")["path"] for file_id in request.upload_ids]
    if CampusToolRouter().route(request.message, uploads).route != "file_tool":
        raise HTTPException(422, "异步任务接口仅用于较慢的文件生成或修改任务")
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"job_id": job_id, "status": "queued", "created_at": datetime.now(timezone.utc).isoformat()}
    asyncio.create_task(_run_job(job_id, request))
    return _jobs[job_id]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id) or job_id not in _jobs:
        raise HTTPException(404, "任务不存在或服务重启后已失效")
    return _jobs[job_id]


@app.get("/api/sessions/{session_id}/tasks")
def tasks(session_id: str) -> list[dict[str, Any]]:
    SESSION_STORE.load(session_id)
    return TASK_STORE.list(session_id)


@app.patch("/api/sessions/{session_id}/tasks/{task_id}")
def update_task(session_id: str, task_id: str, request: TaskUpdate) -> dict[str, Any]:
    try:
        return TASK_STORE.update(session_id, task_id, request.status)
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/sessions/{session_id}/calendar.ics")
def calendar(session_id: str) -> Any:
    from fastapi.responses import Response
    return Response(TASK_STORE.to_ics(session_id), media_type="text/calendar", headers={"Content-Disposition": "attachment; filename=tsingask-tasks.ics"})


@app.get("/api/traces")
def recent_traces(limit: int = 30) -> list[dict[str, Any]]:
    return TRACE_STORE.recent(limit)


@app.get("/api/traces/{case_id}")
def trace(case_id: str) -> dict[str, Any]:
    value = TRACE_STORE.get(case_id)
    if value is None:
        raise HTTPException(404, "回放记录不存在")
    return value


@app.post("/api/traces/{case_id}/replay")
async def replay(case_id: str, request: ReplayRequest) -> dict[str, Any]:
    trace_value = TRACE_STORE.get(case_id)
    if trace_value is None:
        raise HTTPException(404, "回放记录不存在")
    state = SESSION_STORE.load(request.session_id)
    value = await asyncio.to_thread(
        agent().ask, trace_value["query"], context=state.get("profile", {}),
        path_override=trace_value.get("path"),
    )
    value["replayed_from"] = case_id
    value["session_id"] = state["session_id"]
    TRACE_STORE.append(value, session_id=state["session_id"])
    return public_result(value)


@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict[str, Any]:
    if request.kind not in {"irrelevant_source", "outdated", "wrong_deadline", "missing_step", "bad_file_format", "other"}:
        raise HTTPException(422, "不支持的反馈类型")
    row = {"at": datetime.now(timezone.utc).isoformat(), "case_id": request.case_id, "kind": request.kind, "detail": redact(request.detail), "status": "isolated_queue"}
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"accepted": True, "applied_to_knowledge_base": False, "status": "isolated_queue"}


@app.post("/api/warmup")
async def warmup() -> dict[str, Any]:
    dense, model = await asyncio.gather(
        asyncio.to_thread(agent().warmup_full_path),
        asyncio.to_thread(default_local_runtime().health, load=True),
    )
    return {"dense": dense, "model": model}


@app.get("/api/files/{file_id}")
def download(file_id: str) -> FileResponse:
    if not re.fullmatch(r"[0-9a-f]{32}", file_id):
        raise HTTPException(404, "文件不存在")
    record = safe_record(file_id, expected_kind="output")
    return FileResponse(record["path"], media_type=record.get("media_type"), filename=record["filename"])


FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
