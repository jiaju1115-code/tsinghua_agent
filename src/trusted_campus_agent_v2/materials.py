from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_flatten(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(_flatten(item) for item in value.values())
    return str(value or "")


class MaterialInspector:
    """Checks surface completeness only; it never decides eligibility."""

    def __init__(self, rag_agent: Any) -> None:
        self.rag_agent = rag_agent

    def inspect(self, matter: str, paths: list[str | Path], *, context: dict[str, Any] | None = None) -> dict[str, Any]:
        from .file_tools import CampusFileService

        rag = self.rag_agent.ask(f"{matter}需要提交哪些材料、签字盖章和截止时间？", context=context)
        required = list((rag.get("response", {}).get("action_plan") or {}).get("materials", []))
        contents = []
        for path in paths:
            contents.append({"filename": Path(path).name, "content": CampusFileService.read(path)})
        joined = "\n".join(item["filename"] + "\n" + _flatten(item["content"]) for item in contents)
        missing = []
        found = []
        for requirement in required:
            keywords = [word for word in re.findall(r"[\u4e00-\u9fff]{2,8}", requirement) if word not in {"申请材料", "相关材料", "提交材料"}]
            if any(word in joined for word in keywords[:8]):
                found.append(requirement)
            else:
                missing.append(requirement)
        warnings = []
        if re.search(r"(?:签字|签名)[：:]?\s*(?:$|___|未填写)", joined, re.M):
            warnings.append("发现可能未填写的签字/签名栏。")
        if re.search(r"(?:盖章|公章)[：:]?\s*(?:$|___|未盖章)", joined, re.M):
            warnings.append("发现可能缺少盖章的字段。")
        if re.search(r"\{\{[^}]+\}\}|\[[^]]*请填写[^]]*\]|_{4,}", joined):
            warnings.append("发现模板占位符或空白字段，请逐项确认。")
        return {
            "kind": "material_surface_check", "matter": matter, "files": [item["filename"] for item in contents],
            "evidence_status": rag["evidence_status"], "required_materials": required,
            "found": found, "possibly_missing": missing, "warnings": warnings,
            "disclaimer": "仅检查材料表面完整性、字段和文本线索，不代表学校已认定申请资格或材料有效。",
            "response": rag.get("response"), "case_id": rag.get("case_id"),
        }
