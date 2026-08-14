from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

ATTACHMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
SKIP_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js", ".zip", ".rar", ".7z", ".mp3", ".mp4", ".avi"}

def normalize_url(url: str, base: str | None = None, tracking: set[str] | None = None) -> str | None:
    if base:
        url = urljoin(base, url)
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return None
    try:
        host = parts.hostname.lower().rstrip(".")
        port = parts.port
    except (ValueError,AttributeError):
        return None
    netloc = host if not port or (parts.scheme == "http" and port == 80) or (parts.scheme == "https" and port == 443) else f"{host}:{port}"
    path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
    if path != "/":
        path = path.rstrip("/")
    ignored = {x.lower() for x in (tracking or set())}
    pairs = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in ignored and not k.lower().startswith("utm_"))
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(pairs, doseq=True), ""))

def is_allowed(url: str, root_domain: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    root = root_domain.lower()
    return host == root or host.endswith("." + root)

def extension(url: str) -> str:
    return PurePosixPath(urlsplit(url).path.lower()).suffix
