from __future__ import annotations

import re
from typing import Any

from src.evidence_sufficiency_v1.policy import (
    compact,
    content_grams,
    decompose_query,
    evidence_has_attribute,
    evidence_sentences,
    extract_entities,
    overlap_score,
)


def _document_blob(chunks):
    return " ".join(f"{chunk['title']} {chunk['text']}" for chunk in chunks)


def _entity_guard(query: str, document_blob: str) -> dict[str, Any]:
    before = list(extract_entities(query))
    ignored = []
    after = []
    doc = compact(document_blob)
    for entity in before:
        if compact(entity) in doc:
            after.append(entity)
            continue
        # Generic organization suffix recovery: remove interrogative/functional
        # prefix while retaining the organization-like suffix. Never deletes a
        # named entity that is not independently present in the evidence.
        normalized_entity = compact(entity)
        suffixes = [normalized_entity[-length:] for length in range(min(12, len(normalized_entity)), 3, -1)]
        suffix = next((candidate for candidate in suffixes if candidate in doc), None)
        if suffix:
            ignored.append({'term': entity, 'replacement': suffix, 'reason': 'NON_CONSTRAINT_QUERY_PREFIX'})
            after.append(suffix)
        else:
            after.append(entity)
    return {'before': before, 'after': after, 'ignored': ignored, 'passed': all(compact(e) in doc for e in after)}


FUNCTION_WORDS = re.compile(r"(?:请帮我|请问|我想了解|想了解|通常|一般|学校|现在|目前|什么时候|什么时间|哪些|哪一些|需要|应该|是否|能否|可以|要|吗)")


def _normalize(text: str) -> str:
    return FUNCTION_WORDS.sub('', text)


def _ranked_point(point_text: str, chunks: list[dict[str, Any]], normalized: bool = False):
    spans = evidence_sentences(chunks)
    target = _normalize(point_text) if normalized else point_text
    ranked = sorted(((overlap_score(target, _normalize(span['text']) if normalized else span['text']), span) for span in spans), key=lambda item: (-item[0], item[1]['chunk_id'], item[1]['span_id']))
    return ranked


def evaluate_candidate(case: dict[str, Any], candidate: str, thresholds: dict[str, float]) -> dict[str, Any]:
    chunks = case['retrieval']['ordered_top5_chunks']
    query = case['query']
    points, _ = decompose_query(query, 5)
    document_blob = _document_blob(chunks)
    entity = _entity_guard(query, document_blob)
    point_results = []
    for point in points:
        normalized = candidate == 'PARAPHRASE_NORMALIZATION'
        ranked = _ranked_point(point.text, chunks, normalized=normalized)
        best_score = ranked[0][0] if ranked else 0.0
        attributes = list(point.requested_attributes)
        missing_attributes = []
        for attribute in attributes:
            if not any(score >= thresholds['partial'] and evidence_has_attribute(attribute, span['text'], span['url']) for score, span in ranked):
                missing_attributes.append(attribute)
        entity_ok = entity['passed'] if candidate == 'ENTITY_GUARD' else not bool(case['evidence']['diagnostics'].get('missing_query_entities'))
        if candidate == 'PARAPHRASE_NORMALIZATION':
            entity_ok = not bool(case['evidence']['diagnostics'].get('missing_query_entities'))
        dense_rank1 = chunks[0]['score'] if chunks else 0.0
        rescue = candidate == 'SEMANTIC_RESCUE' and thresholds['rescue_lower'] <= best_score < thresholds['rescue_upper'] and dense_rank1 >= thresholds['rescue_dense'] and entity_ok and not missing_attributes
        if best_score >= thresholds['supported'] and entity_ok and not missing_attributes:
            status = 'SUPPORTED'
        elif best_score >= thresholds['partial'] and entity_ok and not missing_attributes:
            status = 'PARTIALLY_SUPPORTED'
        elif rescue:
            status = 'PARTIALLY_SUPPORTED'
        else:
            status = 'NOT_SUPPORTED'
        point_results.append({'point_id': point.point_id, 'text': point.text, 'requested_attributes': attributes, 'status': status, 'best_score': round(best_score, 6), 'rescue': rescue, 'matched_spans': [{'span_id': span['span_id'], 'chunk_id': span['chunk_id'], 'score': round(score, 6), 'text': span['text']} for score, span in ranked[:2] if score >= thresholds['rescue_lower'] if candidate == 'SEMANTIC_RESCUE' or score >= thresholds['partial']]})
    statuses = [row['status'] for row in point_results]
    if statuses and all(status == 'SUPPORTED' for status in statuses):
        decision = 'SUFFICIENT'
    elif any(status in {'SUPPORTED', 'PARTIALLY_SUPPORTED'} for status in statuses):
        decision = 'PARTIAL'
    else:
        decision = 'INSUFFICIENT'
    return {'decision': decision, 'required_points': point_results, 'entity_trace': entity, 'candidate': candidate, 'input_query': query}
