from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


FileFormat = Literal["docx", "xlsx", "pptx", "pdf"]
FileAction = Literal["create", "modify", "read"]


@dataclass
class SectionSpec:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    table: list[list[Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SectionSpec":
        return cls(
            heading=str(value.get("heading", "")).strip(),
            paragraphs=[str(item) for item in value.get("paragraphs", [])],
            bullets=[str(item) for item in value.get("bullets", [])],
            table=[list(row) for row in value.get("table", [])],
        )


@dataclass
class FilePlan:
    """Structured contract produced by an LLM and consumed by Python tools."""

    title: str
    output_format: FileFormat
    template_key: str = "course_report"
    subtitle: str = ""
    author: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    sections: list[SectionSpec] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    workbook_sheets: list[dict[str, Any]] = field(default_factory=list)
    slides: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FilePlan":
        fmt = str(value.get("output_format", "docx")).lower().lstrip(".")
        if fmt not in {"docx", "xlsx", "pptx", "pdf"}:
            raise ValueError(f"unsupported output format: {fmt}")
        return cls(
            title=str(value.get("title", "校园文件")).strip() or "校园文件",
            output_format=fmt,  # type: ignore[arg-type]
            template_key=str(value.get("template_key", "course_report")),
            subtitle=str(value.get("subtitle", "")),
            author=str(value.get("author", "")),
            metadata=dict(value.get("metadata", {})),
            sections=[SectionSpec.from_dict(item) for item in value.get("sections", [])],
            sources=[dict(item) for item in value.get("sources", [])],
            workbook_sheets=[dict(item) for item in value.get("workbook_sheets", [])],
            slides=[dict(item) for item in value.get("slides", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FileRoute:
    route: Literal["rag_qa", "file_tool"]
    action: FileAction | None = None
    output_format: FileFormat | None = None
    tool_name: str | None = None
    template_key: str | None = None
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


@dataclass(frozen=True)
class FileArtifact:
    path: str
    format: FileFormat
    action: FileAction
    filename: str
    media_type: str
    size_bytes: int
    preserved_template: bool
    warnings: tuple[str, ...] = ()
    evidence_status: str | None = None
    sources: tuple[dict[str, str], ...] = ()

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        fmt: FileFormat,
        action: FileAction,
        preserved_template: bool = False,
        warnings: tuple[str, ...] = (),
        evidence_status: str | None = None,
        sources: tuple[dict[str, str], ...] = (),
    ) -> "FileArtifact":
        media = {
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "pdf": "application/pdf",
        }[fmt]
        resolved = path.resolve()
        return cls(
            path=str(resolved),
            format=fmt,
            action=action,
            filename=resolved.name,
            media_type=media,
            size_bytes=resolved.stat().st_size,
            preserved_template=preserved_template,
            warnings=warnings,
            evidence_status=evidence_status,
            sources=sources,
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["warnings"] = list(self.warnings)
        value["sources"] = list(self.sources)
        value["download_path"] = self.path
        return value
