from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from .common import DEFAULT_OUTPUT_DIR
from .models import FileArtifact, FilePlan, FileRoute, SectionSpec
from .router import CampusToolRouter
from .templates import TEMPLATES, infer_template_key, scaffold_plan


class InsufficientFileEvidenceError(RuntimeError):
    """Raised when a RAG-grounded file would require unsupported claims."""


class CampusFileService:
    """Executes structured file plans; it never asks an LLM to write OOXML/PDF bytes."""

    def __init__(self, rag_agent: Any | None = None, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> None:
        self.rag_agent = rag_agent
        self.output_dir = Path(output_dir).resolve()
        self.router = CampusToolRouter()

    @staticmethod
    def templates() -> list[dict[str, Any]]:
        return [
            {"key": item.key, "name": item.name, "description": item.description, "sections": list(item.sections)}
            for item in TEMPLATES.values()
        ]

    def _default_output(self, plan: FilePlan) -> Path:
        from .common import safe_filename

        return self.output_dir / f"{safe_filename(plan.title)}.{plan.output_format}"

    def plan_with_rag(self, request: str, output_format: str, template_key: str | None = None) -> tuple[FilePlan, dict[str, Any]]:
        if self.rag_agent is None:
            raise RuntimeError("RAG agent is required for evidence-grounded file generation")
        result = self.rag_agent.ask(request)
        status = result["evidence_status"]
        if status in {"NOT_SUPPORTED", "CONFLICT"}:
            raise InsufficientFileEvidenceError(
                f"Evidence Gate returned {status}; refusing to generate an authoritative campus file."
            )
        response = result["response"]
        plan = scaffold_plan(request, output_format, template_key=template_key)
        plan.sources = [dict(item) for item in response.get("citations", [])]
        confirmed = [item["text"] for item in response.get("confirmed_facts", [])]
        grounded_sections = [
            SectionSpec(
                heading=f"学校要求（{status}）",
                paragraphs=["以下内容仅依据检索到的有效官方证据生成；未获支持的信息保留为空。"],
                bullets=confirmed,
            )
        ]
        action = response.get("action_plan") or {}
        labels = {
            "conditions": "适用条件", "materials": "材料清单", "steps": "办理步骤",
            "deadlines": "截止时间", "official_entries": "官方入口",
        }
        for key, heading in labels.items():
            if action.get(key):
                grounded_sections.append(SectionSpec(heading=heading, bullets=list(action[key])))
        plan.sections = grounded_sections + plan.sections
        plan.metadata.update({"evidence_status": status, "rag_query": request})
        return plan, result

    def _coerce_plan(
        self,
        request: str,
        output_format: str,
        template_key: str | None,
        structured_content: FilePlan | dict[str, Any] | None,
        use_rag: bool,
    ) -> tuple[FilePlan, dict[str, Any] | None]:
        if isinstance(structured_content, FilePlan):
            plan = structured_content
        elif structured_content is not None:
            payload = dict(structured_content)
            payload.setdefault("output_format", output_format)
            payload.setdefault("template_key", infer_template_key(request, template_key))
            plan = FilePlan.from_dict(payload)
        elif use_rag:
            return self.plan_with_rag(request, output_format, template_key)
        else:
            plan = scaffold_plan(request, output_format, template_key=template_key)
        if plan.output_format != output_format:
            plan.output_format = output_format  # type: ignore[assignment]
        return plan, None

    def _rag_context(self, request: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
        if self.rag_agent is None:
            raise RuntimeError("RAG agent is required for evidence-grounded file generation")
        result = self.rag_agent.ask(request)
        status = result["evidence_status"]
        if status in {"NOT_SUPPORTED", "CONFLICT"}:
            raise InsufficientFileEvidenceError(
                f"Evidence Gate returned {status}; refusing to plan an authoritative campus file."
            )
        response = result["response"]
        hits = {
            item.get("source_id"): item
            for item in result.get("evidence", {}).get("supporting_hits", [])
        }
        citations = [dict(item) for item in response.get("citations", [])]
        access_levels = {
            (
                hits[item.get("source_id")].get("metadata", {}).get("access_level", "restricted")
                if item.get("source_id") in hits
                else "unknown"
            )
            for item in citations
        }
        access_level = "public" if access_levels <= {"public"} else "restricted"
        context = [{
            "evidence_status": status,
            "confirmed_facts": [item.get("text", "") for item in response.get("confirmed_facts", [])],
            "action_plan": response.get("action_plan"),
            "citations": citations,
            "access_level": access_level,
        }]
        return result, context, citations

    def execute_with_llm(
        self,
        request: str,
        planner: Any,
        *,
        uploaded_files: list[str | Path] | None = None,
        input_path: str | Path | None = None,
        template_path: str | Path | None = None,
        output_path: str | Path | None = None,
        output_format: str | None = None,
        template_key: str | None = None,
        use_rag: bool | None = None,
        include_uploaded_content: bool = False,
        allow_external_file_content: bool = False,
    ) -> dict[str, Any]:
        """Plan a trusted file tool call with an LLM, then execute it in Python."""
        uploads = [str(item) for item in (uploaded_files or [])]
        if input_path and str(input_path) not in uploads:
            uploads.insert(0, str(input_path))
        route = self.router.route(request, uploads)
        if output_format:
            normalized_format = output_format.lower().lstrip(".")
            if normalized_format not in {"docx", "xlsx", "pptx", "pdf"}:
                raise ValueError(f"unsupported output format: {normalized_format}")
            route = replace(route, output_format=normalized_format)
        if template_key:
            if template_key not in TEMPLATES:
                raise ValueError(f"unknown template: {template_key}")
            route = replace(route, template_key=template_key)
        if route.route != "file_tool":
            if self.rag_agent is None:
                raise ValueError("ordinary QA requires a RAG agent")
            result = self.rag_agent.ask(request)
            result["tool_route"] = route.to_dict()
            return result
        trusted_input = Path(input_path or uploads[0]).resolve() if (input_path or uploads) else None
        if trusted_input is not None and not trusted_input.is_file():
            raise FileNotFoundError(trusted_input)
        if route.action == "read":
            return self.execute(request, route=route, input_path=trusted_input)

        if use_rag is None:
            use_rag = any(marker in request for marker in ("根据学校", "学校最新要求", "官方要求", "最新规定", "按学校要求"))
        rag_result = None
        evidence_context = None
        citations: list[dict[str, str]] = []
        if use_rag:
            rag_result, evidence_context, citations = self._rag_context(request)

        uploaded_content = None
        if include_uploaded_content and trusted_input is not None:
            if getattr(planner, "external", True) and not allow_external_file_content:
                raise PermissionError(
                    "sending uploaded file content to an external LLM requires allow_external_file_content=True"
                )
            uploaded_content = self.read(trusted_input)

        call = planner.plan(
            request,
            route,
            evidence_context=evidence_context,
            uploaded_content=uploaded_content,
        )
        if call.action == "create" and call.plan is None:
            raise ValueError("LLM create tool call must include structured_content")
        plan = call.plan or scaffold_plan(request, call.output_format, template_key=call.template_key)
        plan.output_format = call.output_format
        plan.template_key = call.template_key
        plan.sources = citations
        if rag_result:
            plan.metadata["evidence_status"] = rag_result["evidence_status"]
            plan.metadata["rag_query"] = request
            if rag_result["evidence_status"] == "PARTIAL":
                plan.sections.insert(
                    0,
                    SectionSpec(
                        heading="证据边界",
                        paragraphs=["学校资料仅部分支持本文件内容；未获证据支持的要求不得视为正式规定。"],
                    ),
                )
        result = self.execute(
            request,
            route=route,
            action=call.action,
            output_format=call.output_format,
            input_path=trusted_input,
            template_path=template_path,
            template_key=call.template_key,
            structured_content=plan,
            replacements=call.replacements,
            cell_updates=call.cell_updates,
            output_path=output_path,
            use_rag=False,
        )
        if "artifact" in result:
            result["artifact"]["evidence_status"] = rag_result["evidence_status"] if rag_result else None
            result["artifact"]["sources"] = citations
        result["llm_tool_call"] = call.to_dict()
        result["llm_tool_call"]["trusted_input_path_supplied_by_host"] = str(trusted_input) if trusted_input else None
        result["llm_tool_call"]["model_paths_accepted"] = False
        result["evidence"] = rag_result
        return result

    def execute(
        self,
        request: str,
        *,
        route: FileRoute | None = None,
        action: str | None = None,
        output_format: str | None = None,
        input_path: str | Path | None = None,
        template_path: str | Path | None = None,
        template_key: str | None = None,
        structured_content: FilePlan | dict[str, Any] | None = None,
        replacements: dict[str, str] | None = None,
        cell_updates: dict[str, Any] | None = None,
        output_path: str | Path | None = None,
        use_rag: bool | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        route = route or self.router.route(request, [input_path] if input_path else [])
        if route.route != "file_tool" and action is None:
            raise ValueError("request does not route to a file tool")
        action = action or route.action or "create"
        fmt = (output_format or route.output_format or (Path(input_path).suffix.lstrip(".") if input_path else "docx")).lower()
        if fmt not in {"docx", "xlsx", "pptx", "pdf"}:
            raise ValueError(f"unsupported file format: {fmt}")
        if action in {"read", "modify"} and not input_path:
            raise ValueError(f"{action} requires input_path")
        if input_path and not Path(input_path).is_file():
            raise FileNotFoundError(input_path)
        if use_rag is None:
            use_rag = any(marker in request for marker in ("根据学校", "学校最新要求", "官方要求", "最新规定", "按学校要求"))

        if action == "read":
            content = self.read(input_path)  # type: ignore[arg-type]
            return {
                "route": route.to_dict(), "action": "read", "format": fmt,
                "content": content, "candidate_only": True, "published": False,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }

        plan, rag_result = self._coerce_plan(request, fmt, template_key or route.template_key, structured_content, bool(use_rag))
        target = Path(output_path).resolve() if output_path else self._default_output(plan)
        preserved = bool(template_path or input_path)
        warnings: tuple[str, ...] = ()
        if action == "create":
            if fmt == "docx":
                from .word import create_docx
                path = create_docx(plan, target, template_path)
            elif fmt == "xlsx":
                from .excel import create_xlsx
                path = create_xlsx(plan, target, template_path)
            elif fmt == "pptx":
                from .powerpoint import create_pptx
                path = create_pptx(plan, target, template_path)
            else:
                from .pdf import create_pdf
                path = create_pdf(plan, target)
        else:
            if fmt == "docx":
                from .word import modify_docx
                path, changed = modify_docx(input_path, replacements=replacements, append_plan=plan if structured_content else None, output_path=target)  # type: ignore[arg-type]
            elif fmt == "xlsx":
                from .excel import modify_xlsx
                path, changed = modify_xlsx(input_path, cell_updates=cell_updates, replacements=replacements, output_path=target)  # type: ignore[arg-type]
            elif fmt == "pptx":
                from .powerpoint import modify_pptx
                path, changed = modify_pptx(input_path, replacements=replacements, output_path=target)  # type: ignore[arg-type]
            else:
                from .pdf import modify_pdf
                path, changed, warnings = modify_pdf(input_path, replacements=replacements, output_path=target)  # type: ignore[arg-type]
            if changed == 0:
                warnings = (*warnings, "未找到可修改的匹配内容；已导出独立副本。")
        evidence_status = rag_result["evidence_status"] if rag_result else None
        artifact = FileArtifact.from_path(
            path,
            fmt=fmt,  # type: ignore[arg-type]
            action=action,  # type: ignore[arg-type]
            preserved_template=preserved,
            warnings=warnings,
            evidence_status=evidence_status,
            sources=tuple(plan.sources),
        )
        return {
            "route": route.to_dict(), "artifact": artifact.to_dict(), "plan": plan.to_dict(),
            "candidate_only": True, "published": False,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    @staticmethod
    def read(path: str | Path) -> dict[str, Any]:
        suffix = Path(path).suffix.lower()
        if suffix == ".docx":
            from .word import read_docx
            return read_docx(path)
        if suffix == ".xlsx":
            from .excel import read_xlsx
            return read_xlsx(path)
        if suffix == ".pptx":
            from .powerpoint import read_pptx
            return read_pptx(path)
        if suffix == ".pdf":
            from .pdf import read_pdf
            return read_pdf(path)
        raise ValueError(f"unsupported input format: {suffix}")
