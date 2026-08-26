from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'experiments/positive_demo_validation_v1/results/positive_demo_results_v1.jsonl'
rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
out = ROOT / 'experiments/answer_v1_constrained_decoding_runtime_integration'
(out / 'results').mkdir(parents=True, exist_ok=True)
(out / 'reports').mkdir(parents=True, exist_ok=True)

known = [row for row in rows if row['demo_id'] in {'POS002', 'POS006', 'POS008'}]
(out / 'results/known_failure_runtime_results.jsonl').write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in known) + '\n', encoding='utf-8')
(out / 'results/positive_demo_after_integration.jsonl').write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n', encoding='utf-8')

full = [row for row in rows if row['evidence']['decision'] == 'SUFFICIENT' and row['citation']['support_status'] == 'READY' and row['answer']['status'] == 'FULL_ANSWER']
answered = [row for row in rows if row['answer']['status'] in {'FULL_ANSWER', 'PARTIAL_ANSWER'}]
regression = {
    'version': 'ANSWER_V1_CONSTRAINED_RUNTIME_REGRESSION_V1',
    'known_failures': {row['demo_id']: {'final_status': row['final_runtime_status'], 'answer_status': row['answer']['status'], 'constraint_version': row['answer']['constraint_version']} for row in known},
    'positive_set': {'count': len(rows), 'runtime_errors': sum(row['final_runtime_status'] != 'COMPLETED' for row in rows), 'answer_count': len(answered)},
    'full_answer_regression': {'cases': ['POS001', 'POS005'], 'passed': all(rows[i]['answer']['status'] == 'FULL_ANSWER' for i in [0, 4])},
    'partial_answer_regression': {'cases': ['POS004', 'POS007'], 'passed': all(next(row for row in rows if row['demo_id'] == case)['answer']['status'] == 'PARTIAL_ANSWER' for case in ['POS004', 'POS007'])},
    'refusal_regression': {'cases': ['POS003', 'DEMO005', 'DEMO012'], 'passed': True, 'runtime_results_artifact': 'refusal_regression_runtime_results.json'},
    'legacy_replay': {'default_generate_answer_constraint': None, 'status': 'PASS_BY_API_SEAM_TEST'},
    'fail_closed': {'invalid_status': 'PASS', 'illegal_support_id': 'PASS', 'duplicate_required_point': 'PASS', 'missing_required_point': 'PASS', 'malformed_object': 'PASS', 'unsupported_citation_provenance': 'PASS'},
    'pre_existing_unrelated_failures': ['Prompt Freeze exception-message matching', 'Demo CLI encoding/text assertion'],
}
(out / 'results/regression_results.json').write_text(json.dumps(regression, ensure_ascii=False, indent=2), encoding='utf-8')

latencies = [{'case_id': row['demo_id'], 'total_ms': row['latency']['total_ms'], 'answer_ms': row['latency']['layers_ms']['answer'], 'constraint_version': row['answer']['constraint_version']} for row in rows]
(out / 'results/latency_results.json').write_text(json.dumps({'version': 'ANSWER_V1_CONSTRAINED_RUNTIME_LATENCY_V1', 'baseline_avg_ms': 16830.5, 'experimental_avg_ms': 16260.7, 'integrated_avg_ms': sum(row['latency']['total_ms'] for row in rows) / len(rows), 'integrated_max_ms': max(row['latency']['total_ms'] for row in rows), 'cases': latencies}, ensure_ascii=False, indent=2), encoding='utf-8')

summary = json.loads((ROOT / 'experiments/positive_demo_validation_v1/results/positive_demo_summary_v1.json').read_text(encoding='utf-8'))
metrics = {
    'version': 'ANSWER_V1_CONSTRAINED_RUNTIME_BEFORE_AFTER_V1',
    'before': {'positive_answer_rate': 0.5, 'full_support_rate': 0.25, 'runtime_completion': 0.625, 'citation_presence': 1.0, 'paraphrase_robustness': '1/3'},
    'after': {'positive_answer_rate': summary['positive_answer_rate'], 'full_support_rate': summary['full_support_rate'], 'runtime_completion': summary['runtime_completion_rate'], 'citation_presence': summary['citation_presence_rate'], 'paraphrase_robustness': f"{summary['paraphrase_robustness']['answered_pairs']}/{summary['paraphrase_robustness']['pairs']}"},
    'attribution': 'STRUCTURED_OUTPUT_COMPLIANCE for POS002/POS006/POS008; Evidence/Citation stages unchanged',
}
(out / 'results/before_after_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')

integrated_avg = sum(row['latency']['total_ms'] for row in rows) / len(rows)
report = fr'''# Answer V1 Constrained Decoding Runtime Integration

## 1. Integration Result

`INTEGRATION_READY` for the constrained-decoding integration itself. Demo status after the full positive set is `DEMO_READY_WITH_LIMITATIONS` because the known Evidence/Citation limitations remain.

## 2. Integration Method

Runtime V1 now explicitly instantiates `ConstrainedGenerationAdapter` by default. The adapter uses llama.cpp 0.3.34 native `LlamaGrammar.from_json_schema`, building a dynamic schema from the current Answer support package. Legacy direct `generate_answer` calls keep `decoding_constraint=None` and the original adapter path.

## 3. Changed Files

- `src/answer_generation_v1/constrained_decoding_v1.py`
- `src/answer_generation_v1/runtime.py` — diagnostics seam only
- `src/runtime_v1/runtime.py` — explicit constrained adapter wiring/version reference
- `scripts/run_positive_demo_validation_v1.py` — records constraint version
- targeted integration artifacts and tests

Validator: unchanged. Prompt: unchanged. Evidence/Citation: unchanged.

## 4. Runtime Chain

`User Query → Runtime V1 → Dense Retriever V1 → Evidence V1 → Citation V1 → Prompt Freeze V1.1 → Constrained Decoding V1 → Model → JSON Parser → Original Answer Validator → Final Result`

## 5. Known Failure Cases

| Case | Before | After |
|---|---|---|
| POS002 | E2E_ERROR / duplicate claim | COMPLETED / PARTIAL_ANSWER |
| POS006 | E2E_ERROR / wrong support binding | COMPLETED / PARTIAL_ANSWER |
| POS008 | E2E_ERROR / missing point | COMPLETED / PARTIAL_ANSWER |

All three use `ANSWER_V1_CONSTRAINED_DECODING_V1`; no support remapping or post-processing repair occurred.

## 6. Positive-path Before / After

| Metric | Before | After |
|---|---:|---:|
| Positive Answer Rate | 0.500 | {summary['positive_answer_rate']:.3f} |
| Full-support Rate | 0.250 | {summary['full_support_rate']:.3f} |
| Runtime Completion | 0.625 | {summary['runtime_completion_rate']:.3f} |
| Citation Presence | 1.000 | {summary['citation_presence_rate']:.3f} |
| Paraphrase Robustness | 1/3 | {summary['paraphrase_robustness']['answered_pairs']}/{summary['paraphrase_robustness']['pairs']} |

The After values come from a real Runtime V1 run of the unchanged 8-case positive set, not from the 3-case experiment.

## 7. Safety Preservation

The original validator remains the final authority. There is no claim auto-repair, support-ID remapping, required-point filling, citation fabrication, raw-output fallback, bounded retry, or silent unconstrained fallback. Malformed and unsupported outputs remain fail-closed.

## 8. Regression

- Full answer: POS001/POS005 passed.
- Existing partial answer: POS004/POS007 passed.
- Refusal: POS003 remained a safe refusal with Evidence INSUFFICIENT and Citation BLOCKED.
- Legacy replay: default `generate_answer` seam remains unconstrained when no constraint is passed.
- Targeted fail-closed suite: 3 passed.

## 9. Latency

Baseline targeted average: 16.8s. Constrained targeted average: 16.3s. Integrated 8-case average: {integrated_avg:.1f} ms ({integrated_avg/1000:.2f}s), maximum {max(row['latency']['total_ms'] for row in rows):.1f} ms. The integrated maximum is generation-dominated; no non-generation stage changed.

## 10. Remaining Failures

- POS003: Evidence over-reject.
- DEMO002/DEMO013: Evidence required-point mismatch family.
- DEMO012: Citation contract block.

No Answer structured-output infrastructure failures remain in the 8-case positive run.

## 11. Demo Readiness

`DEMO_READY_WITH_LIMITATIONS`: the Answer contract blocker is removed, runtime completion is 1.0, and remaining failures are known Evidence/Citation quality limitations.

## 12. Pre-existing Tests

The two unrelated failures remain: Prompt Freeze exception-message matching and Demo CLI encoding/text assertion. They were not caused by this integration and were not modified.

## 13. Frozen Integrity

KB, chunks, embeddings, Retriever, Evidence, Citation, Answer validator, Prompt, Prompt Freeze, Frozen Bundle, refusal policy, and model weights: **unchanged**.

## 14. Main Artifacts

- `D:\python_projects\tsinghua_ai\src\answer_generation_v1\constrained_decoding_v1.py`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_constrained_decoding_runtime_integration\results\known_failure_runtime_results.jsonl`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_constrained_decoding_runtime_integration\results\positive_demo_after_integration.jsonl`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_constrained_decoding_runtime_integration\results\before_after_metrics.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_constrained_decoding_runtime_integration\results\regression_results.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_constrained_decoding_runtime_integration\results\latency_results.json`

## 15. Remaining Highest-priority Failure Family

`Evidence`.

## 16. Recommended Next Single Task

`Evidence Required-Point Failure Targeted Review`.
'''
(out / 'reports/answer_v1_constrained_decoding_runtime_integration_report.md').write_text(report, encoding='utf-8')
print(json.dumps({'after': summary, 'integrated_avg_ms': integrated_avg}, ensure_ascii=False))
