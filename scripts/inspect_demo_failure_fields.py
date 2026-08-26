import json
from pathlib import Path

paths = [
    Path('experiments/demo_runtime_validation_v1/results/demo_runtime_results_v1.jsonl'),
    Path('experiments/positive_demo_validation_v1/results/positive_demo_results_v1.jsonl'),
]
for path in paths:
    print(path)
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    for row in rows:
        ident = row.get('demo_id')
        if ident not in {'DEMO002', 'DEMO012', 'DEMO013'} and not ident.startswith('POS'):
            continue
        evidence = row.get('evidence', {})
        citation = row.get('citation', {})
        answer = row.get('answer', {})
        if not isinstance(answer, dict):
            answer = {'status': answer}
        print(json.dumps({
            'id': ident,
            'final': row.get('final_runtime_status', row.get('status')),
            'evidence_decision': evidence.get('decision'),
            'evidence_reasons': evidence.get('reason_codes'),
            'points': [
                {
                    'id': p.get('point_id'),
                    'status': p.get('status', p.get('support_status')),
                    'score': p.get('best_support_score'),
                }
                for p in evidence.get('required_points', [])
            ],
            'citation_status': citation.get('status'),
            'citation_reasons': citation.get('reason_codes'),
            'support_unit_count': len(citation.get('support_units', [])),
            'excluded': citation.get('excluded_candidates', []),
            'answer_status': answer.get('status'),
            'answer_reasons': answer.get('reason_codes'),
            'answer_error': answer.get('error'),
            'model_called': answer.get('model_called'),
            'latency': row.get('latency', {}),
        }, ensure_ascii=False))
