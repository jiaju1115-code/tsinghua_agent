from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


QUESTION_STOP = (
    "\u8bf7\u95ee", "\u5982\u4f55", "\u600e\u4e48", "\u600e\u6837", "\u4ec0\u4e48", "\u54ea\u4e9b",
    "\u662f\u5426", "\u80fd\u5426", "\u53ef\u4ee5", "\u9700\u8981", "\u6709\u5173", "\u76f8\u5173",
)
OPTIONAL_MARKER = re.compile(
    r"(?:\u987a\u4fbf|\u5982\u679c\u65b9\u4fbf|\u53ef\u9009\u5730|\u53e6\u5916\u53ef\u9009|\u9644\u5e26)"
    r"(?:\u4ecb\u7ecd|\u8bf4\u660e|\u63d0\u4f9b|\u8bf4\u8bf4)?(.+)$"
)
ENTITY_PATTERN = re.compile(
    r"(?:\u6e05\u534e\u5927\u5b66|\u6e05\u534e|\u5317\u4eac)?[\u4e00-\u9fffA-Za-z0-9]{0,10}"
    r"(?:\u5927\u5b66|\u5b66\u9662|\u533b\u9662|\u56fe\u4e66\u9986|\u4e2d\u5fc3|\u5e73\u53f0|\u7cfb\u7edf)"
)

ATTRIBUTE_QUERY_PATTERNS = {
    "DEADLINE": (r"\u622a\u6b62(?:\u65e5\u671f|\u65f6\u95f4)?", r"\u671f\u9650", r"\u6700\u665a"),
    "TIME": (r"\u5f00\u653e\u65f6\u95f4", r"\u529e\u7406\u65f6\u95f4", r"\u670d\u52a1\u65f6\u95f4", r"\u4ec0\u4e48\u65f6\u5019", r"\u4f55\u65f6", r"\u51e0\u70b9", r"\u65f6\u6bb5", r"\u65f6\u95f4"),
    "LOCATION": (r"\u5730\u70b9", r"\u5730\u5740", r"\u5728\u54ea\u91cc", r"\u54ea\u513f", r"\u4f4d\u7f6e"),
    "PRICE": (r"\u4ef7\u683c", r"\u91d1\u989d", r"\u8d39\u7528", r"\u6536\u8d39", r"\u591a\u5c11\u94b1", r"\u662f\u5426\u514d\u8d39"),
    "ELIGIBILITY": (r"\u8d44\u683c", r"\u6761\u4ef6", r"\u8c01\u53ef\u4ee5", r"\u80fd\u5426\u7533\u8bf7", r"\u7b26\u5408\u4ec0\u4e48"),
    "PROCEDURE": (r"\u6d41\u7a0b", r"\u6b65\u9aa4", r"\u600e\u4e48\u529e\u7406", r"\u5982\u4f55\u529e\u7406", r"\u624b\u7eed"),
    "ENTRY": (r"\u5165\u53e3", r"\u94fe\u63a5", r"\u7f51\u5740", r"\u5728\u54ea\u7533\u8bf7", r"\u7533\u8bf7\u5e73\u53f0", r"\u529e\u7406\u5e73\u53f0"),
    "MATERIALS": (r"\u6750\u6599", r"\u8bc1\u4ef6", r"\u9700\u5e26", r"\u63d0\u4ea4\u4ec0\u4e48", r"\u51c6\u5907\u4ec0\u4e48"),
    "CONTACT": (r"\u8054\u7cfb\u65b9\u5f0f", r"\u8054\u7cfb\u7535\u8bdd", r"\u7535\u8bdd", r"\u90ae\u7bb1", r"\u600e\u4e48\u8054\u7cfb"),
    "OBJECT": (r"\u9002\u7528\u5bf9\u8c61", r"\u9762\u5411\u8c01", r"\u670d\u52a1\u5bf9\u8c61", r"\u5bf9\u8c61"),
    "CURRENT_STATUS": (r"\u76ee\u524d", r"\u5f53\u524d", r"\u73b0\u5728", r"\u6700\u65b0", r"\u4eca\u5e74"),
}

ATTRIBUTE_EVIDENCE_PATTERNS = {
    "DEADLINE": (r"\u622a\u6b62", r"\u671f\u9650", r"\u6700\u665a", r"20\d{2}[\u5e74/-]\d{1,2}"),
    "TIME": (r"\u65f6\u95f4", r"\u5f00\u653e", r"\u5de5\u4f5c\u65e5", r"\u5468[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5]", r"\d{1,2}[:\uff1a]\d{2}"),
    "LOCATION": (r"\u5730\u70b9", r"\u5730\u5740", r"\u4f4d\u4e8e", r"\u5927\u697c", r"\u5ba4", r"\u6821\u533a"),
    "PRICE": (r"\u8d39\u7528", r"\u6536\u8d39", r"\u514d\u8d39", r"\d+(?:\.\d+)?\s*(?:\u5143|\u4eba\u6c11\u5e01)"),
    "ELIGIBILITY": (r"\u8d44\u683c", r"\u6761\u4ef6", r"\u7533\u8bf7\u4eba", r"\u53ef\u7533\u8bf7", r"\u7b26\u5408", r"\u5bf9\u8c61"),
    "PROCEDURE": (r"\u6d41\u7a0b", r"\u6b65\u9aa4", r"\u529e\u7406", r"\u7533\u8bf7", r"\u63d0\u4ea4", r"\u767b\u5f55"),
    "ENTRY": (r"\u5165\u53e3", r"\u94fe\u63a5", r"\u7f51\u5740", r"\u5e73\u53f0", r"\u7cfb\u7edf", r"\u767b\u5f55", r"https?://"),
    "MATERIALS": (r"\u6750\u6599", r"\u8bc1\u4ef6", r"\u8eab\u4efd\u8bc1", r"\u5b66\u751f\u8bc1", r"\u7533\u8bf7\u8868", r"\u63d0\u4ea4"),
    "CONTACT": (r"\u8054\u7cfb", r"\u7535\u8bdd", r"\u90ae\u7bb1", r"\d{3,4}[- ]?\d{6,8}", r"[\w.+-]+@[\w.-]+"),
    "OBJECT": (r"\u5bf9\u8c61", r"\u9762\u5411", r"\u7533\u8bf7\u4eba", r"\u5b66\u751f", r"\u6559\u5e08", r"\u6821\u53cb", r"\u804c\u5de5"),
    "CURRENT_STATUS": (r"\u76ee\u524d", r"\u5f53\u524d", r"\u73b0\u884c", r"\u6700\u65b0", r"2026"),
}

VALUE_PATTERNS = {
    "DEADLINE": re.compile(r"20\d{2}[\u5e74/-]\d{1,2}(?:[\u6708/-]\d{1,2}\u65e5?)?"),
    "TIME": re.compile(r"\d{1,2}[:\uff1a]\d{2}(?:\s*[-\u2013\u2014\u81f3]\s*\d{1,2}[:\uff1a]\d{2})?"),
    "PRICE": re.compile(r"\d+(?:\.\d+)?\s*(?:\u5143|\u4eba\u6c11\u5e01)"),
    "CONTACT": re.compile(r"(?:\d{3,4}[- ]?)?\d{6,8}|[\w.+-]+@[\w.-]+"),
}


@dataclass(frozen=True)
class RequiredPoint:
    point_id: str
    text: str
    requested_attributes: tuple[str, ...]


def clean_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", clean_text(text)).lower()


def content_grams(text: str) -> set[str]:
    value = compact(text)
    for word in QUESTION_STOP:
        value = value.replace(word, "")
    grams: set[str] = set()
    for width in (2, 3, 4):
        grams.update(value[index:index + width] for index in range(max(0, len(value) - width + 1)))
    return grams


def overlap_score(query_part: str, evidence_span: str) -> float:
    expected = content_grams(query_part)
    actual = content_grams(evidence_span)
    return len(expected & actual) / max(1, len(expected))


def requested_attributes(text: str) -> tuple[str, ...]:
    found = []
    for name, patterns in ATTRIBUTE_QUERY_PATTERNS.items():
        if name == "TIME" and re.search(r"\u622a\u6b62(?:\u65e5\u671f|\u65f6\u95f4)?", text):
            continue
        if any(re.search(pattern, text, flags=re.I) for pattern in patterns):
            found.append(name)
    return tuple(found)


def decompose_query(query: str, max_points: int) -> tuple[list[RequiredPoint], list[str]]:
    value = unicodedata.normalize("NFKC", query).strip().rstrip("?\uff1f\u3002")
    optional: list[str] = []
    marker = OPTIONAL_MARKER.search(value)
    if marker:
        candidate = marker.group(1).strip(" \uff0c,\u3002")
        if len(candidate) >= 2:
            optional.append(candidate)
        value = value[:marker.start()].strip(" \uff0c,")
    split_pattern = r"\u3001|\uff0c|,|\u4ee5\u53ca|\u5e76\u4e14|\u540c\u65f6|\u548c|\u4e0e|\u53ca"
    parts = [part.strip(" \uff0c,") for part in re.split(split_pattern, value) if part.strip(" \uff0c,")]
    if len(parts) <= 1 or any(len(compact(part)) < 4 for part in parts):
        parts = [value] if value else []
    if not parts or len(parts) > max_points or any(len(compact(part)) < 2 for part in parts):
        return [], optional
    return [RequiredPoint(f"P{index}", part, requested_attributes(part)) for index, part in enumerate(parts, 1)], optional


def extract_entities(text: str) -> tuple[str, ...]:
    entities = []
    for match in ENTITY_PATTERN.finditer(text):
        value = match.group(0)
        value = re.sub(r"^(?:\u8fdb\u5165|\u4f7f\u7528|\u67e5\u8be2|\u901a\u8fc7|\u5173\u4e8e|\u5728|\u5411)", "", value)
        if len(value) >= 2 and value not in entities:
            entities.append(value)
    return tuple(entities)


def evidence_has_attribute(attribute: str, text: str, url: str = "") -> bool:
    target = f"{text} {url}"
    return any(re.search(pattern, target, flags=re.I) for pattern in ATTRIBUTE_EVIDENCE_PATTERNS[attribute])


def attribute_values(attribute: str, text: str) -> set[str]:
    pattern = VALUE_PATTERNS.get(attribute)
    return {compact(value) for value in pattern.findall(text)} if pattern else set()


def evidence_sentences(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans = []
    for chunk in chunks:
        text = clean_text(chunk.get("text", ""))
        for sentence_index, sentence in enumerate(re.split(r"[\u3002\uff01\uff1f!?\n\uff1b]", text), 1):
            sentence = sentence.strip()
            if len(sentence) >= 6:
                spans.append({"chunk_id": chunk["chunk_id"], "source_id": chunk["source_id"], "url": chunk.get("url", ""), "span_id": f"{chunk['chunk_id']}#S{sentence_index}", "text": sentence})
        title = clean_text(chunk.get("title", ""))
        if title:
            spans.append({"chunk_id": chunk["chunk_id"], "source_id": chunk["source_id"], "url": chunk.get("url", ""), "span_id": f"{chunk['chunk_id']}#TITLE", "text": title})
    return spans
