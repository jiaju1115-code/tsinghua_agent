from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import re
import sys
import uuid
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


APP_ROOT = ROOT / "apps" / "tsingask_v2"
RUNTIME_ROOT = APP_ROOT / ".artifact_runtime"
UPLOAD_ROOT = RUNTIME_ROOT / "uploads"
OUTPUT_ROOT = RUNTIME_ROOT / "outputs"
REGISTRY_PATH = RUNTIME_ROOT / "files.json"
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


app = FastAPI(title="清问·TsingAsk V2", version="2.0.0", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent: TrustedCampusAgentV2 | None = None


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
    path = Path(record["path"]).resolve()
    allowed = UPLOAD_ROOT.resolve() if record.get("kind") == "upload" else OUTPUT_ROOT.resolve()
    if path.parent != allowed or not path.is_file():
        raise HTTPException(404, "文件不存在或已失效")
    return record


def agent() -> TrustedCampusAgentV2:
    global _agent
    if _agent is None:
        _agent = TrustedCampusAgentV2(use_public_v2=True, local_model=True)
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
        records[file_id] = {"kind": "output", "path": str(path), "filename": artifact["filename"], "media_type": artifact["media_type"]}
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
    return {
        "status": "READY" if manifest else "DEGRADED",
        "project": "TsingAsk V2 Independent",
        "online_agent_touched": False,
        "knowledge_base": {key: manifest.get(key) for key in ("bundle_version", "source_count", "chunk_count", "dense_index")},
        "model": model,
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
    records[file_id] = {"kind": "upload", "path": str(path), "filename": original, "media_type": file.content_type or mimetypes.guess_type(original)[0]}
    save_registry(records)
    return {"file_id": file_id, "filename": original, "size_bytes": len(payload), "format": suffix.lstrip(".")}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    uploads = [safe_record(file_id, expected_kind="upload")["path"] for file_id in request.upload_ids]
    route = CampusToolRouter().route(request.message, uploads)
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
        value = await asyncio.to_thread(agent().handle, request.message, uploaded_files=uploads, file_options=options)
        return public_result(value)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"本地智能体执行失败：{type(exc).__name__}: {exc}") from exc


@app.get("/api/files/{file_id}")
def download(file_id: str) -> FileResponse:
    if not re.fullmatch(r"[0-9a-f]{32}", file_id):
        raise HTTPException(404, "文件不存在")
    record = safe_record(file_id, expected_kind="output")
    return FileResponse(record["path"], media_type=record.get("media_type"), filename=record["filename"])


FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
