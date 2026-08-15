from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass


_MARKDOWN_LINK = re.compile(r"!?\[([^\]]+)\]\([^)]*\)")
_HTML_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class CanonicalText:
    text: str
    raw_offsets: tuple[int, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SpanMatch:
    raw_start: int
    raw_end: int
    raw_text: str
    normalized_text: str
    occurrence_count: int
    normalization_reasons: tuple[str, ...]


def _markdown_projection(raw: str) -> tuple[list[tuple[str, int]], bool]:
    projected: list[tuple[str, int]] = []
    cursor = 0
    changed = False
    for match in _MARKDOWN_LINK.finditer(raw):
        projected.extend((char, idx) for idx, char in enumerate(raw[cursor:match.start()], cursor))
        label = match.group(1)
        label_start = match.start(1)
        projected.extend((char, label_start + idx) for idx, char in enumerate(label))
        cursor = match.end()
        changed = True
    projected.extend((char, idx) for idx, char in enumerate(raw[cursor:], cursor))
    return projected, changed


def canonicalize_with_offsets(raw: str) -> CanonicalText:
    """Normalize citation text while retaining a map to raw chunk offsets."""
    if not isinstance(raw, str):
        return CanonicalText("", (), ("SPAN_INVALID",))
    projected, markdown_changed = _markdown_projection(raw)
    output: list[str] = []
    offsets: list[int] = []
    reasons: set[str] = set()
    in_tag = False
    whitespace_pending = False
    whitespace_offset = 0
    for char, raw_idx in projected:
        if char == "<":
            in_tag = True
            reasons.add("HTML_TEXT_NORMALIZED")
            whitespace_pending = True
            whitespace_offset = raw_idx
            continue
        if in_tag:
            if char == ">":
                in_tag = False
            continue
        expanded = unicodedata.normalize("NFKC", html.unescape(char))
        if expanded != char:
            reasons.add("UNICODE_WHITESPACE_NORMALIZED")
        for normalized_char in expanded:
            if normalized_char.isspace():
                if output:
                    whitespace_pending = True
                    whitespace_offset = raw_idx
                continue
            if whitespace_pending and output and output[-1] != " ":
                output.append(" ")
                offsets.append(whitespace_offset)
                reasons.add("UNICODE_WHITESPACE_NORMALIZED")
            whitespace_pending = False
            output.append(normalized_char)
            offsets.append(raw_idx)
    if markdown_changed:
        reasons.add("MARKDOWN_TEXT_NORMALIZED")
    return CanonicalText("".join(output).strip(), tuple(offsets), tuple(sorted(reasons)))


def canonicalize(raw: str) -> str:
    return canonicalize_with_offsets(raw).text


def compact_length(text: str) -> int:
    return sum(1 for char in canonicalize(text) if not char.isspace() and not unicodedata.category(char).startswith("P"))


def is_only_punctuation(text: str) -> bool:
    normalized = canonicalize(text)
    return not normalized or all(char.isspace() or unicodedata.category(char).startswith(("P", "S")) for char in normalized)


def locate_span(raw_chunk: str, evidence_text: str) -> SpanMatch | None:
    chunk = canonicalize_with_offsets(raw_chunk)
    needle = canonicalize_with_offsets(evidence_text)
    if not needle.text:
        return None
    starts = [match.start() for match in re.finditer(re.escape(needle.text), chunk.text)]
    if not starts:
        return None
    canonical_start = starts[0]
    canonical_end = canonical_start + len(needle.text)
    raw_start = chunk.raw_offsets[canonical_start]
    raw_end = chunk.raw_offsets[canonical_end - 1] + 1
    reasons = set(chunk.reasons) | set(needle.reasons)
    if not reasons:
        reasons.add("EXACT_TEXT")
    trailing = raw_chunk[raw_end:]
    terminator = re.match(r"^[\u3002\uff01\uff1f.!?;\uff1b]", trailing)
    if terminator:
        raw_end += len(terminator.group(0))
        reasons.add("TRAILING_BOUNDARY_EXPANDED")
    preceding = raw_chunk[:raw_start].rstrip()
    following = raw_chunk[raw_end:].lstrip()
    boundary_chars = "\n\r\u3002\uff01\uff1f.!?;\uff1b:：>*#"
    if (not preceding or preceding[-1] in boundary_chars) and (not following or raw_chunk[raw_end - 1] in boundary_chars):
        reasons.add("SENTENCE_BOUNDARY_VALIDATED")
    else:
        reasons.add("PARTIAL_SENTENCE_BOUNDARY")
    raw_text = raw_chunk[raw_start:raw_end]
    return SpanMatch(
        raw_start=raw_start,
        raw_end=raw_end,
        raw_text=raw_text,
        normalized_text=canonicalize(raw_text),
        occurrence_count=len(starts),
        normalization_reasons=tuple(sorted(reasons)),
    )


def mergeable_gap(raw_gap: str, maximum: int) -> bool:
    if len(raw_gap) > maximum:
        return False
    return all(char.isspace() or unicodedata.category(char).startswith(("P", "S")) for char in raw_gap)
