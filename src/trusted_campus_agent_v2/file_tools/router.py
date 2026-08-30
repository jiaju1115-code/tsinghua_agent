from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import FileRoute
from .templates import infer_template_key


FORMAT_MARKERS = {
    "docx": ("word", "docx", "文档", "报告", "申请书", "策划书", "纪要"),
    "xlsx": ("excel", "xlsx", "表格", "工作簿", "统计表", "清单表"),
    "pptx": ("ppt", "pptx", "幻灯片", "演示文稿", "汇报稿"),
    "pdf": ("pdf",),
}
FILE_VERBS = ("生成", "创建", "制作", "导出", "另存", "修改", "编辑", "润色", "替换", "处理文件", "读取文件")
MODIFY_VERBS = ("修改", "编辑", "润色", "替换", "补充", "更新", "改成", "另存")
READ_VERBS = ("读取", "解析", "提取", "总结这个文件", "看看这个文件")


class CampusToolRouter:
    """Deterministic fallback router; callers may override it with an LLM tool call."""

    def route(self, request: str, uploaded_files: Iterable[str | Path] = ()) -> FileRoute:
        query = request.strip().lower()
        uploads = [Path(item) for item in uploaded_files]
        reasons: list[str] = []
        fmt = None
        for candidate, markers in FORMAT_MARKERS.items():
            if any(marker in query for marker in markers):
                fmt = candidate
                reasons.append(f"format_marker:{candidate}")
                break
        if uploads:
            suffix = uploads[0].suffix.lower().lstrip(".")
            if suffix in FORMAT_MARKERS and fmt is None:
                fmt = suffix
            reasons.append("uploaded_file")

        file_intent = bool(uploads) or any(verb in query for verb in FILE_VERBS)
        if not file_intent:
            return FileRoute(route="rag_qa", reasons=("no_file_intent",))
        fmt = fmt or "docx"
        if uploads and any(verb in query for verb in READ_VERBS) and not any(verb in query for verb in MODIFY_VERBS):
            action = "read"
        elif uploads and any(marker in query for marker in ("作为模板", "用这个模板", "根据模板", "套用模板", "按此模板")):
            action = "create"
        elif uploads or any(verb in query for verb in MODIFY_VERBS):
            action = "modify"
        else:
            action = "create"
        tool_name = {"docx": "word_file_tool", "xlsx": "excel_file_tool", "pptx": "powerpoint_file_tool", "pdf": "pdf_file_tool"}[fmt]
        return FileRoute(
            route="file_tool",
            action=action,  # type: ignore[arg-type]
            output_format=fmt,  # type: ignore[arg-type]
            tool_name=tool_name,
            template_key=infer_template_key(request),
            reasons=tuple(reasons or ["file_verb"]),
        )

    @staticmethod
    def tool_schemas(openai_wrapper: bool = False) -> list[dict]:
        section_schema = {
            "type": "object",
            "required": ["heading"],
            "properties": {
                "heading": {"type": "string"},
                "paragraphs": {"type": "array", "items": {"type": "string"}},
                "bullets": {"type": "array", "items": {"type": "string"}},
                "table": {
                    "type": "array",
                    "items": {"type": "array", "items": {}},
                },
            },
        }
        structured_schema = {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "author": {"type": "string"},
                "metadata": {"type": "object"},
                "sections": {"type": "array", "items": section_schema},
                "workbook_sheets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "rows"],
                        "properties": {
                            "name": {"type": "string"},
                            "rows": {"type": "array", "items": {"type": "array", "items": {}}},
                            "formulas": {"type": "object"},
                        },
                    },
                },
                "slides": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title"],
                        "properties": {
                            "title": {"type": "string"},
                            "bullets": {"type": "array", "items": {"type": "string"}},
                            "table": {"type": "array", "items": {"type": "array", "items": {}}},
                        },
                    },
                },
            },
        }
        function = {
            "name": "create_or_modify_campus_file",
            "description": (
                "Create, read, or modify a real DOCX/XLSX/PPTX/PDF campus file. "
                "The host supplies trusted file paths and returns the download path."
            ),
            "parameters": {
                "type": "object",
                "required": ["action", "output_format", "template_key", "use_rag"],
                "properties": {
                    "action": {"type": "string", "enum": ["create", "modify", "read"]},
                    "output_format": {"type": "string", "enum": ["docx", "xlsx", "pptx", "pdf"]},
                    "template_key": {
                        "type": "string",
                        "enum": [
                            "social_practice_report", "event_plan", "scholarship_application",
                            "meeting_minutes", "course_report",
                        ],
                    },
                    "use_rag": {"type": "boolean"},
                    "structured_content": structured_schema,
                    "replacements": {
                        "type": "object",
                        "description": "Small exact text replacements for DOCX/PPTX/PDF edits.",
                        "additionalProperties": {"type": "string"},
                    },
                    "cell_updates": {
                        "type": "object",
                        "description": "Excel edits keyed by trusted Sheet!A1 addresses.",
                    },
                },
            },
        }
        return [{"type": "function", "function": function}] if openai_wrapper else [function]
