from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'experiments/evidence_required_point_review_v1/audit'
trace = json.loads((AUDIT / 'evidence_required_point_case_trace_v1.json').read_text(encoding='utf-8'))['cases']

classifications = {
    'DEMO002': {
        'primary_root_cause': 'LEXICAL_MATCH_OVERSTRICT',
        'secondary_causes': ['SEMANTIC_MATCH_WEAKNESS'],
        'systemic': True,
        'related_cases': ['POS003'],
        'confidence': 'HIGH',
        'finding': 'Correct scholarship eligibility chunks and spans are in Top-5, but entity extraction overcaptures the conversational prefix as an entity. missing_query_entities then makes entity_ok false and forces NOT_SUPPORTED despite document relevance 0.549020 and support spans above the partial floor.',
    },
    'DEMO013': {
        'primary_root_cause': 'LEXICAL_MATCH_OVERSTRICT',
        'secondary_causes': ['SEMANTIC_MATCH_WEAKNESS'],
        'systemic': True,
        'related_cases': ['DEMO002', 'POS003'],
        'confidence': 'MEDIUM',
        'finding': 'Relevant scholarship chunks are in Top-5, but the single required point receives best lexical score 0.166667, below the partial threshold 0.18, so no support span is admitted. No entity mismatch is present; this is a separate lexical-paraphrase subcase.',
    },
    'POS003': {
        'primary_root_cause': 'LEXICAL_MATCH_OVERSTRICT',
        'secondary_causes': ['SEMANTIC_MATCH_WEAKNESS'],
        'systemic': True,
        'related_cases': ['DEMO002'],
        'confidence': 'HIGH',
        'finding': 'Correct eligibility spans are in Top-5 with score 0.357143 and document relevance 0.547619, but entity extraction overcaptures the conversational prefix as an entity. missing_query_entities forces the point to NOT_SUPPORTED.',
    },
}

rule_rows = []
matrix = []
for case in trace:
    ev = case['evidence']
    diag = ev['diagnostics']
    point_rows = case['required_points']
    point = point_rows[0] if point_rows else {}
    c = classifications[case['case_id']]
    entity_gate = not bool(diag.get('missing_query_entities'))
    best_score = point.get('best_support_score')
    rule_rows.append({
        'case_id': case['case_id'],
        'required_point_generation': {'count': len(point_rows), 'points': [{'point_id': p.get('point_id'), 'text': p.get('text'), 'requested_attributes': p.get('requested_attributes'), 'mandatory': True} for p in point_rows]},
        'matching_inputs': {'best_support_score': best_score, 'partial_threshold': diag.get('thresholds', {}).get('partial'), 'supported_threshold': diag.get('thresholds', {}).get('supported'), 'document_relevance_score': diag.get('document_relevance_score'), 'document_relevance_threshold': diag.get('thresholds', {}).get('document_relevance'), 'missing_query_entities': diag.get('missing_query_entities', [])},
        'decision_path': [
            {'rule': 'RETRIEVAL_INPUT_ACCEPTED', 'result': 'PASS'},
            {'rule': 'REQUIRED_POINT_PARSE', 'result': 'PASS'},
            {'rule': 'DOCUMENT_RELEVANCE', 'result': 'PASS' if (diag.get('document_relevance_score') or 0) >= (diag.get('thresholds', {}).get('document_relevance') or 0) else 'FAIL'},
            {'rule': 'ENTITY_GATE', 'result': 'PASS' if entity_gate else 'FAIL', 'detail': 'missing_query_entities blocks supported classification' if not entity_gate else 'no missing query entities'},
            {'rule': 'POINT_SCORE_GATE', 'result': 'SUPPORTED_THRESHOLD_NOT_MET' if isinstance(best_score, (int, float)) and best_score < diag.get('thresholds', {}).get('supported', 1) else 'PASS'},
            {'rule': 'PARTIAL_THRESHOLD_GATE', 'result': 'PARTIAL_THRESHOLD_NOT_MET' if isinstance(best_score, (int, float)) and best_score < diag.get('thresholds', {}).get('partial', 1) else 'PASS'},
            {'rule': 'FINAL_DECISION', 'result': ev.get('decision'), 'reason_codes': ev.get('reason_codes', [])},
        ],
    })
    matrix.append({
        'case_id': case['case_id'],
        'retrieval_status': case['retrieval']['status'],
        'required_points': point_rows,
        'supported_points': ev.get('supporting_chunk_ids', []),
        'unsupported_points': [p.get('point_id') for p in point_rows if p.get('status') in {'NOT_SUPPORTED', 'CONFLICT'}],
        'primary_root_cause': c['primary_root_cause'],
        'secondary_causes': c['secondary_causes'],
        'systemic': c['systemic'],
        'related_cases': c['related_cases'],
        'confidence': c['confidence'],
        'finding': c['finding'],
    })

(AUDIT / 'evidence_decision_rule_trace_v1.json').write_text(json.dumps({'version': 'EVIDENCE_DECISION_RULE_TRACE_V1', 'cases': rule_rows}, ensure_ascii=False, indent=2), encoding='utf-8')
(AUDIT / 'evidence_required_point_root_cause_matrix.json').write_text(json.dumps({'version': 'EVIDENCE_REQUIRED_POINT_ROOT_CAUSE_MATRIX_V1', 'cases': matrix}, ensure_ascii=False, indent=2), encoding='utf-8')

review = ROOT / 'experiments/evidence_required_point_review_v1'
(review / 'data').mkdir(parents=True, exist_ok=True)
(review / 'data/targeted_evidence_review_cases.json').write_text(json.dumps([{'case_id': c['case_id'], 'query': c['query'], 'expected_behavior': c['expected_behavior']} for c in trace], ensure_ascii=False, indent=2), encoding='utf-8')

report = r'''# Evidence Required-Point Mismatch Targeted Review V1

## 1. Executive Conclusion

The dominant Evidence issue is `LEXICAL_MATCH_OVERSTRICT`, not Retriever miss. DEMO002 and POS003 are the same high-confidence entity-gate subfamily; DEMO013 is a related but distinct lexical-score subcase. Retriever returned relevant frozen-KB chunks for all three. A safe unified production fix was not identified in this diagnosis-only pass.

## 2. Case Root Causes

### DEMO002

- Retrieval: `RETRIEVAL_OK`; source `KBV1-PUB-PUBV2C-0075` appears in ranks 1–3.
- Required point: one mandatory eligibility point; no over-specification or over-fragmentation observed.
- Failure rule: `missing_query_entities` caused the entity gate to fail; best point score was 0.294118 and document relevance was 0.549020.
- Classification: `LEXICAL_MATCH_OVERSTRICT`, secondary `SEMANTIC_MATCH_WEAKNESS`; confidence HIGH.

### DEMO013

- Retrieval: `RETRIEVAL_OK`; source `KBV1-PUB-PUBV2C-0075` appears in ranks 1, 2, and 4.
- Required point: one mandatory point; no requested attribute mismatch and no entity mismatch.
- Failure rule: best score 0.166667 fell below the partial threshold 0.18, so no support span was admitted.
- Classification: `LEXICAL_MATCH_OVERSTRICT`, secondary `SEMANTIC_MATCH_WEAKNESS`; confidence MEDIUM.

### POS003

- Retrieval: `RETRIEVAL_OK`; eligibility source chunks are in ranks 1–3.
- Required point: one mandatory `ELIGIBILITY` point; correct supporting spans exist at score 0.357143.
- Failure rule: the same false entity extraction pattern as DEMO002 set `missing_query_entities`, forcing `NOT_SUPPORTED`.
- Classification: `LEXICAL_MATCH_OVERSTRICT`, secondary `SEMANTIC_MATCH_WEAKNESS`; confidence HIGH.

## 3. Original vs Paraphrase Comparison

DEMO002 and POS003 are semantically close eligibility questions. Their Retriever inputs contain the same source family and their Evidence traces diverge at the same entity gate: the query prefix is treated as an entity absent from the KB. DEMO013 follows a different path: no entity mismatch, but lexical overlap is below the partial floor. The divergence begins in Evidence matching, not Retriever ranking.

## 4. Evidence Decision Rule

The current implementation uses `deterministic_lexical_structural_support_proxy`:

1. Decompose query into required points and requested attributes.
2. Build sentence spans from usable Top-5 chunks.
3. Compute point-to-span lexical overlap.
4. Require score ≥ 0.52, entity presence, no missing requested attributes, and document relevance ≥ 0.08 for `SUPPORTED`.
5. Permit `PARTIALLY_SUPPORTED` only at score ≥ 0.18 with entity gate satisfied.
6. Aggregate all points: all supported → `SUFFICIENT`; any supported/partial → `PARTIAL`; otherwise `INSUFFICIENT`.

The decisive gates are recorded in `evidence_decision_rule_trace_v1.json`.

## 5. Failure Family Summary

The three cases share a lexical/semantic matching family, but not one identical subcause. DEMO002/POS003 share a systemic false entity-gate pattern. DEMO013 is a systemic paraphrase/lexical-score weakness. This is not a Retriever family and is separate from DEMO012 Citation blocking.

## 6. Candidate Mitigation

`NO_SAFE_EVIDENCE_FIX_IDENTIFIED` in this pass. No production threshold, required-point extraction, entity logic, or semantic matcher was changed; no experiment-only promotion was run. A future experiment must isolate one mechanism and include false-promote controls before any production consideration.

## 7. Candidate Experiment

`Not run — diagnosis only.` The trace does not justify choosing between minimal-core extraction, paraphrase-invariant mapping, semantic matching, or threshold review without changing multiple causal variables.

## 8. Safety Assessment

No under-rejecting change was made. No false promote was introduced. Evidence remains fail-closed, with no gold-answer or case-ID dependency. Retriever, Citation, Answer, and constrained decoding were not modified.

## 9. Demo Impact

These failures currently limit Full-support Rate and positive-answer quality. The Answer infrastructure blocker is already resolved; improving this Evidence family could raise full-support and positive-answer metrics, but no After estimate is claimed from diagnosis alone.

## 10. Frozen Integrity

KB, chunks, embeddings, Retriever, Evidence production semantics, Citation, Answer, Prompt, Prompt Freeze, Frozen Bundle, and Runtime production logic: unchanged.

## 11. Main Artifacts

- `D:\python_projects\tsinghua_ai\experiments\evidence_required_point_review_v1\audit\evidence_required_point_case_trace_v1.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_required_point_review_v1\audit\evidence_decision_rule_trace_v1.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_required_point_review_v1\audit\evidence_required_point_root_cause_matrix.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_required_point_review_v1\data\targeted_evidence_review_cases.json`

## 12. Remaining Highest-priority Failure Family

`Evidence Required Point`.

## 13. Recommended Next Single Task

`Evidence Paraphrase-Invariant Mapping Experiment`: experiment-only, with explicit entity-gate false-positive and false-promote controls; no production integration until DEMO002/DEMO013/POS003 and refusal controls are evaluated together.
'''
(review / 'reports').mkdir(parents=True, exist_ok=True)
(review / 'reports/evidence_required_point_review_v1.md').write_text(report, encoding='utf-8')
print('wrote evidence diagnosis artifacts')
