from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.runtime_v1 import RuntimeV1


def compact_retrieval(value):
    return {
        'status': 'RETRIEVAL_OK' if not value.get('error') else 'RETRIEVAL_ERROR',
        'top_k': [
            {'rank': row['rank'], 'chunk_id': row['chunk_id'], 'source_id': row['source_id'], 'score': row['score'], 'title': row['title'], 'text': row['text']}
            for row in value.get('ordered_top5_chunks', [])
        ],
    }


def main():
    source = ROOT / 'experiments/demo_runtime_validation_v1/data/demo_question_set_v1.jsonl'
    rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
    wanted = {'DEMO002', 'DEMO013'}
    positive = ROOT / 'experiments/positive_demo_validation_v1/results/positive_demo_results_v1.jsonl'
    positive_rows = {json.loads(line)['demo_id']: json.loads(line) for line in positive.read_text(encoding='utf-8').splitlines() if line.strip()}
    questions = [row for row in rows if row.get('demo_id') in wanted]
    questions.append({'demo_id': 'POS003', 'query': positive_rows['POS003']['query'], 'expected_behavior': 'SHOULD_ANSWER', 'scenario': 'POSITIVE'})
    runtime = RuntimeV1()
    traces = []
    for question in questions:
        result = runtime.answer_query(question['query'], request_id=question['demo_id'])
        evidence = result.get('evidence') or {}
        citation = result.get('citation') or {}
        answer = result['diagnostics'].get('answer_runtime') or {}
        traces.append({
            'case_id': question['demo_id'],
            'query': question['query'],
            'source_case': 'demo_runtime_validation_v1' if question['demo_id'].startswith('DEMO') else 'positive_demo_validation_v1',
            'expected_behavior': question['expected_behavior'],
            'retrieval': compact_retrieval(result.get('retrieval') or {}),
            'evidence_input_chunks': [row['chunk_id'] for row in (result.get('retrieval') or {}).get('ordered_top5_chunks', [])],
            'required_points': evidence.get('required_points', []),
            'requested_attributes': evidence.get('requested_attributes', []),
            'missing_requested_attributes': evidence.get('missing_requested_attributes', []),
            'evidence': {
                'decision': evidence.get('decision'),
                'reason_codes': evidence.get('reason_codes', []),
                'supporting_chunk_ids': evidence.get('supporting_chunk_ids', []),
                'supporting_source_ids': evidence.get('supporting_source_ids', []),
                'diagnostics': evidence.get('diagnostics', {}),
            },
            'citation': {
                'status': citation.get('support_status'),
                'reason_codes': citation.get('reason_codes', []),
                'support_units': citation.get('support_units', []),
                'excluded_candidates': citation.get('excluded_candidates', []),
            },
            'answer': {
                'status': answer.get('answer_status'),
                'model_called': answer.get('diagnostics', {}).get('model_called'),
                'reason_codes': answer.get('reason_codes', []),
            },
            'runtime_final_status': result.get('status'),
        })
    out = ROOT / 'experiments/evidence_required_point_review_v1/audit'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'evidence_required_point_case_trace_v1.json').write_text(json.dumps({'version': 'EVIDENCE_REQUIRED_POINT_CASE_TRACE_V1', 'cases': traces}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'cases': [t['case_id'] for t in traces]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
