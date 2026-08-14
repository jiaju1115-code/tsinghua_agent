import re

SECRET_PATTERNS=(
    re.compile(r"(?i)(Authorization\s*:\s*Bearer\s+)[^\s,}\]]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)

def redact(value:object)->str:
    text=str(value)
    text=SECRET_PATTERNS[0].sub(r"\1[REDACTED]",text)
    return SECRET_PATTERNS[1].sub("sk-[REDACTED]",text)

def is_portal(candidate:dict)->bool:
    return candidate.get("access_level")=="campus_authenticated" or candidate.get("source_mode")=="authenticated_portal"

def assert_external_allowed(candidate:dict,allow_portal:bool=False):
    if is_portal(candidate) and not allow_portal:raise PermissionError("Portal原文禁止发送外部LLM")

