from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .models import FilePlan, FileRoute
from .router import CampusToolRouter
from .templates import TEMPLATES


TOOL_NAME = "create_or_modify_campus_file"


class ToolCallingError(RuntimeError):
    """The model response did not satisfy the file-tool contract."""


@dataclass(frozen=True)
class FileToolCall:
    action: str
    output_format: str
    template_key: str
    use_rag: bool
    plan: FilePlan | None = None
    replacements: dict[str, str] = field(default_factory=dict)
    cell_updates: dict[str, Any] = field(default_factory=dict)
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["plan"] = self.plan.to_dict() if self.plan else None
        return value


class FileToolPlanner(Protocol):
    external: bool

    def plan(
        self,
        request: str,
        route: FileRoute,
        *,
        evidence_context: list[dict[str, Any]] | None = None,
        uploaded_content: dict[str, Any] | None = None,
    ) -> FileToolCall: ...


@dataclass(frozen=True)
class LLMToolConfig:
    api_base: str
    api_key: str
    model: str
    timeout: float = 90.0
    max_retries: int = 2
    retry_delay: float = 1.0

    @classmethod
    def from_env(cls, prefix: str = "MOMO") -> "LLMToolConfig":
        try:
            from dotenv import load_dotenv

            load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
        except ImportError:
            pass
        base = os.getenv(f"{prefix}_API_BASE", "").strip().rstrip("/")
        key = os.getenv(f"{prefix}_API_KEY", "").strip()
        model = os.getenv(f"{prefix}_MODEL", "").strip()
        if not base or not key or not model:
            raise RuntimeError(
                f"{prefix}_API_BASE, {prefix}_API_KEY and {prefix}_MODEL are required for LLM file Tool Calling"
            )
        return cls(api_base=base, api_key=key, model=model)


def _redact(value: object) -> str:
    text = str(value)
    if "Bearer " in text:
        text = text.split("Bearer ", 1)[0] + "Bearer [REDACTED]"
    return text[:500]


def _bounded_context(value: Any, *, max_chars: int = 16000) -> str:
    encoded = json.dumps(value, ensure_ascii=False, default=str)
    return encoded[:max_chars]


class OpenAICompatibleFileToolPlanner:
    """Binds the FilePlan contract to OpenAI-compatible chat tool calls."""

    external = True

    def __init__(
        self,
        config: LLMToolConfig,
        *,
        session: Any | None = None,
        completion: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._completion = completion
        self._sleep = sleep
        if session is None and completion is None:
            import requests

            session = requests.Session()
        self.session = session

    @classmethod
    def from_env(cls, prefix: str = "MOMO", **kwargs: Any) -> "OpenAICompatibleFileToolPlanner":
        return cls(LLMToolConfig.from_env(prefix), **kwargs)

    def _complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._completion is not None:
            return self._completion(payload)
        url = f"{self.config.api_base}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.session.post(url, headers=headers, json=payload, timeout=self.config.timeout)
            except Exception as exc:
                if attempt >= self.config.max_retries:
                    raise ToolCallingError(f"LLM request failed: {_redact(exc)}") from exc
                self._sleep(self.config.retry_delay * (2**attempt))
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.config.max_retries:
                self._sleep(self.config.retry_delay * (2**attempt))
                continue
            if not response.ok:
                raise ToolCallingError(f"LLM HTTP {response.status_code}: {_redact(response.text)}")
            return response.json()
        raise ToolCallingError("LLM request exhausted retries")

    @staticmethod
    def _parse(response: dict[str, Any], route: FileRoute, model: str) -> FileToolCall:
        try:
            message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ToolCallingError("LLM response is missing choices[0].message") from exc
        calls = message.get("tool_calls") or []
        if not calls and message.get("function_call"):
            calls = [{"function": message["function_call"]}]
        if len(calls) != 1:
            raise ToolCallingError("exactly one file tool call is required")
        function = calls[0].get("function", {})
        if function.get("name") != TOOL_NAME:
            raise ToolCallingError(f"unexpected tool name: {function.get('name')}")
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ToolCallingError("tool arguments are not valid JSON") from exc
        if not isinstance(arguments, dict):
            raise ToolCallingError("tool arguments must be an object")

        action = str(arguments.get("action") or route.action or "create")
        output_format = str(arguments.get("output_format") or route.output_format or "docx").lower()
        template_key = str(arguments.get("template_key") or route.template_key or "course_report")
        if action not in {"create", "modify", "read"}:
            raise ToolCallingError(f"invalid action: {action}")
        if output_format not in {"docx", "xlsx", "pptx", "pdf"}:
            raise ToolCallingError(f"invalid output format: {output_format}")
        if template_key not in TEMPLATES:
            raise ToolCallingError(f"invalid template key: {template_key}")
        if route.action and action != route.action:
            raise ToolCallingError(f"model action {action} conflicts with trusted route {route.action}")
        if route.output_format and output_format != route.output_format:
            raise ToolCallingError(
                f"model output format {output_format} conflicts with trusted route {route.output_format}"
            )

        structured = arguments.get("structured_content")
        plan = None
        if structured is not None:
            if not isinstance(structured, dict):
                raise ToolCallingError("structured_content must be an object")
            structured = dict(structured)
            structured["output_format"] = output_format
            structured["template_key"] = template_key
            structured["sources"] = []
            plan = FilePlan.from_dict(structured)
            if len(plan.sections) > 30 or len(plan.slides) > 40 or len(plan.workbook_sheets) > 20:
                raise ToolCallingError("structured_content exceeds safe size limits")
        replacements = arguments.get("replacements") or {}
        cell_updates = arguments.get("cell_updates") or {}
        if not isinstance(replacements, dict) or not isinstance(cell_updates, dict):
            raise ToolCallingError("replacements and cell_updates must be objects")
        if len(replacements) > 200 or len(cell_updates) > 1000:
            raise ToolCallingError("file edit operation exceeds safe size limits")
        return FileToolCall(
            action=action,
            output_format=output_format,
            template_key=template_key,
            use_rag=bool(arguments.get("use_rag", False)),
            plan=plan,
            replacements={str(key): str(value) for key, value in replacements.items()},
            cell_updates={str(key): value for key, value in cell_updates.items()},
            model=model,
        )

    def plan(
        self,
        request: str,
        route: FileRoute,
        *,
        evidence_context: list[dict[str, Any]] | None = None,
        uploaded_content: dict[str, Any] | None = None,
    ) -> FileToolCall:
        evidence = evidence_context or []
        restricted = [
            item for item in evidence
            if item.get("access_level", "public") not in {"public", None, ""}
        ]
        if restricted:
            raise PermissionError("campus-authenticated or restricted evidence cannot be sent to an external LLM")
        system = (
            "你是清问·TsingAsk V2 的文件任务规划器。只调用 create_or_modify_campus_file，"
            "不得直接输出 Markdown 文件内容。根据用户需求生成结构化 FilePlan；不要生成、猜测或修改本地路径。"
            "校园规定只能来自 evidence_context；没有证据时不得把占位内容写成学校正式要求。"
            "PARTIAL 证据只能覆盖明确支持部分。修改任务优先给 replacements 或 cell_updates，避免重写整个文件。"
        )
        user_payload = {
            "request": request,
            "trusted_route": route.to_dict(),
            "available_templates": [
                {"key": item.key, "name": item.name, "sections": list(item.sections)}
                for item in TEMPLATES.values()
            ],
            "evidence_context": evidence,
            "uploaded_content": uploaded_content,
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": _bounded_context(user_payload)},
            ],
            "tools": CampusToolRouter.tool_schemas(openai_wrapper=True),
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
            "temperature": 0.1,
            "max_tokens": 3500,
        }
        response = self._complete(payload)
        return self._parse(response, route, self.config.model)
