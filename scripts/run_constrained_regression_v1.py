from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.runtime_v1 import RuntimeV1


def main() -> None:
    source = ROOT / 'experiments/demo_runtime_validation_v1/data/demo_question_set_v1.jsonl'
    if not source.is_file():
        source = ROOT / 'experiments/demo_runtime_validation_v1/data/demo_question_set_v1.jsonl'
    rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
    wanted = {"DEMO005", "DEMO012"}
    runtime = RuntimeV1()
    results = []
    for row in rows:
        if row.get('demo_id') not in wanted:
            continue
        result = runtime.answer_query(row['query'], request_id=row['demo_id'])
        results.append({
            'case_id': row['demo_id'],
            'status': result['status'],
            'answer_status': result['diagnostics']['orchestrator']['answer_status'],
            'evidence_status': result['evidence']['decision'],
            'citation_status': result['citation']['support_status'],
            'refused': result['refusal']['refused'],
            'constraint_version': (result['diagnostics'].get('answer_runtime') or {}).get('diagnostics', {}).get('answer_generation_constraint'),
        })
    out = ROOT / 'experiments/answer_v1_constrained_decoding_runtime_integration/results/refusal_regression_runtime_results.json'
    out.write_text(json.dumps({'version': 'ANSWER_V1_CONSTRAINED_REFUSAL_REGRESSION_V1', 'cases': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
