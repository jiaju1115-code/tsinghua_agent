from __future__ import annotations
import re
from datetime import datetime, timezone

def extract_spans(text: str, *, query: str, mode: str, url: str, title: str, authority: str, max_spans: int = 3) -> list[dict]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=[。！？.!?])\s+", text) if len(p.strip()) >= 50]
    if not paragraphs and text.strip(): paragraphs = [text.strip()]
    spans = []
    for pos, paragraph in enumerate(paragraphs[:max_spans]):
        spans.append({"evidence_id": f"web-{abs(hash((url, pos))) & 0xffffffff:08x}", "search_query": query, "mode": mode, "url": url, "title": title, "source_authority": authority, "span_text": paragraph[:500], "span_position": pos, "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return spans
