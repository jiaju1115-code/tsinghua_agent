from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2" / "generated_files"


def safe_filename(value: str, fallback: str = "campus_file") -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value).strip(" ._")
    cleaned = re.sub(r"\s+", "_", cleaned)
    return (cleaned or fallback)[:80]


def ensure_output_path(title: str, suffix: str, output_path: str | Path | None = None) -> Path:
    if output_path is not None:
        path = Path(output_path)
        if path.suffix.lower() != f".{suffix}":
            path = path.with_suffix(f".{suffix}")
    else:
        path = DEFAULT_OUTPUT_DIR / f"{safe_filename(title)}.{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def dedupe_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot allocate a unique output path near {path}")
