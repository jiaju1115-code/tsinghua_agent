from __future__ import annotations

import re
from typing import Any


INJECTION_PATTERNS = (
    re.compile(r"ignore (?:all |any )?(?:previous|prior|above) instructions?", re.I),
    re.compile(r"system prompt|developer message|reveal.*prompt", re.I),
    re.compile(r"忽略(?:之前|以上|前面).{0,12}(?:指令|要求|规则)"),
    re.compile(r"你现在是|切换身份|执行以下命令|调用工具|读取本地路径"),
)


def sanitize_untrusted_text(text: str) -> tuple[str, list[str]]:
    warnings = []
    safe_lines = []
    for line in text.splitlines():
        if any(pattern.search(line) for pattern in INJECTION_PATTERNS):
            warnings.append(line[:160])
            safe_lines.append("[已隔离：疑似提示注入内容，不作为指令执行]")
        else:
            safe_lines.append(line)
    return "\n".join(safe_lines), warnings


def sanitize_untrusted_payload(value: Any) -> tuple[Any, list[str]]:
    warnings: list[str] = []
    if isinstance(value, str):
        return sanitize_untrusted_text(value)
    if isinstance(value, list):
        items = []
        for item in value:
            clean, found = sanitize_untrusted_payload(item)
            items.append(clean)
            warnings.extend(found)
        return items, warnings
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            clean, found = sanitize_untrusted_payload(item)
            result[key] = clean
            warnings.extend(found)
        return result, warnings
    return value, warnings
