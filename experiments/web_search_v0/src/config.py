from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    api_key: str | None
    max_search_results: int = 5
    max_extract_results: int = 3
    min_content_length: int = 120

def load_settings() -> Settings:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.getenv("TAVILY_API_KEY", "").strip() or None
    return Settings(api_key=key)
