import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'experiments' / 'positive_demo_validation_v1' / 'results'
OUT.mkdir(parents=True, exist_ok=True)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


positive = read_jsonl(OUT / 'positive_demo_results_v1.jsonl')
historical = {
    row['demo_id']: row
    for row in read_jsonl(ROOT / 'experiments' / 'demo_runtime_validation_v1' / 'results' / 'demo_runtime_results_v1.jsonl')
    if row['demo_id'] in {'DEMO002', 'DEMO012', 'DEMO013'}
}


def pos_trace(row, failure_type):
    evidence = row['evidence']
    citation = row['citation']
    answer = row['answer']
    return {
        'case_id': row['demo_id'],
        'source': 'positive_demo_results_v1.jsonl',
        'failure_type': failure_type,
        'systemic': failure_type == 'OTHER',
        'classification_confidence': 'high',
        'query': row['query'],
        'expected_behavior': row['expected_behavior'],
        'trace': {
            'retrieval': row['retrieval'],
            'evidence': {
                'decision': evidence['decision'],
                'reason_codes': evidence.get('reason_codes', []),
                'required_points': [
                    {
                        'point_id': p.get('point_id'),
                        'status': p.get('status'),
                        'best_support_score': p.get('best_support_score'),
                    }
                    for p in evidence.get('required_points', [])
                ],
            },
            'citation': {
                'status': citation.get('status'),
                'reason_codes': citation.get('reason_codes', []),
                'support_unit_count': len(citation.get('support_units', [])),
                'excluded_candidates': citation.get('excluded_candidates', []),
            },
            'answer': {
                'status': answer.get('status'),
                'reason_codes': answer.get('reason_codes', []),
                'model_called': answer.get('model_called'),
                'error': answer.get('error'),
            },
            'latency': row['latency'],
        },
        'root_cause': {
            'boundary': 'answer_contract' if failure_type == 'OTHER' else 'evidence_decision',
            'finding': (
                'Answer V1 was called after partial support but rejected the model output as an invalid '
                'claim/reference/scope shape; this is an Answer contract failure, not a retrieval miss.'
                if failure_type == 'OTHER' else
                'Retriever returned related frozen-KB material, but the Evidence decision did not map the '
                'requested point to supported evidence, so Citation and Answer were safely blocked.'
            ),
        },
    }


traces = [
    pos_trace(next(r for r in positive if r['demo_id'] == 'POS002'), 'OTHER'),
    pos_trace(next(r for r in positive if r['demo_id'] == 'POS003'), 'EVIDENCE_OVER_REJECT'),
    pos_trace(next(r for r in positive if r['demo_id'] == 'POS006'), 'OTHER'),
    pos_trace(next(r for r in positive if r['demo_id'] == 'POS008'), 'OTHER'),
]

for demo_id, failure_type, systemic, finding in [
    ('DEMO002', 'EVIDENCE_REQUIRED_POINT_MISMATCH', True,
     'Historical public trace shows successful retrieval followed by INSUFFICIENT evidence and blocked citation/refusal; the available validation record does not expose required-point internals, so the precise mismatch is bounded to the Evidence decision boundary.'),
    ('DEMO013', 'EVIDENCE_REQUIRED_POINT_MISMATCH', True,
     'Historical public trace has the same retrieval-success → insufficient-evidence → blocked-citation/refusal pattern as DEMO002; classify as the same family with bounded confidence because the public record lacks point-level evidence details.'),
    ('DEMO012', 'CITATION_CONTRACT_BLOCK', False,
     'Historical public trace shows successful retrieval and a blocked citation/refusal. The stored historical record does not include support units or excluded-candidate details, so the exact citation integrity reason cannot be recovered from this artifact; this is a citation/data-contract boundary, not an Answer model call.'),
]:
    row = historical[demo_id]
    traces.append({
        'case_id': demo_id,
        'source': 'demo_runtime_results_v1.jsonl',
        'failure_type': failure_type,
        'systemic': systemic,
        'classification_confidence': 'medium' if demo_id != 'DEMO012' else 'low',
        'query': row['query'],
        'expected_behavior': row['expected_behavior'],
        'trace': {
            'retrieval_status': row['retrieval_status'],
            'source_count': row['source_count'],
            'evidence_status': row['evidence_status'],
            'citation_status': row['citation_status'],
            'answer_status': row['answer_status'],
            'refusal': row['refusal'],
            'latency': {'total_ms': row['latency_ms'], 'layers_ms': row['layer_latencies_ms']},
            'historical_trace_limit': 'Public demo result has no point-level Evidence/Citation package.',
        },
        'root_cause': {'boundary': 'evidence_decision' if demo_id != 'DEMO012' else 'citation_contract', 'finding': finding},
    })

(OUT / 'demo_failure_trace_v1.json').write_text(
    json.dumps({'version': 'DEMO_FAILURE_TRACE_V1', 'traces': traces}, ensure_ascii=False, indent=2),
    encoding='utf-8',
)

slowest = max(positive, key=lambda r: r['latency']['total_ms'])
layer = slowest['latency']['layers_ms']
(OUT / 'latency_trace_v1.json').write_text(json.dumps({
    'version': 'LATENCY_TRACE_V1',
    'scope': 'positive_demo_validation_v1',
    'slowest_case': slowest['demo_id'],
    'total_ms': slowest['latency']['total_ms'],
    'layers_ms': layer,
    'model_called': slowest['answer']['model_called'],
    'diagnosis': 'Answer/model inference dominates; retrieval, Evidence, and Citation are each below 0.2 seconds. This run does not expose a separate cold-start timer, and the repeated model-call pattern indicates model inference rather than retrieval or citation latency.',
    'cold_warm_boundary': 'not separately instrumented; no evidence of a retriever cold-start bottleneck in the recorded layer timings',
}, ensure_ascii=False, indent=2), encoding='utf-8')

summary = json.loads((OUT / 'positive_demo_summary_v1.json').read_text(encoding='utf-8'))
report = f'''# Positive-path Demo Validation V1

## Positive-path Readiness

结论：`DEMO_BLOCKED`（正向路径）。8 个 `SHOULD_ANSWER` 案例中只有 4 个进入可交付回答状态，3 个在 Answer 层产生 `E2E_ERROR`，1 个被 Evidence 阻断拒答。现有整体 Demo 结论仍为上一轮的 `DEMO_READY_WITH_LIMITATIONS`，但正向路径本身未达到可演示门槛。

## Metrics

| 指标 | 结果 |
|---|---:|
| Positive Answer Rate | {summary['positive_answer_rate']:.3f} (4/8) |
| Full-support rate | {summary['full_support_rate']:.3f} (2/8) |
| Paraphrase Robustness | {summary['paraphrase_robustness']['answered_pairs']}/{summary['paraphrase_robustness']['pairs']} pairs answered |
| Citation Presence | {summary['citation_presence_rate']:.3f} |
| Runtime completion | {summary['runtime_completion_rate']:.3f} (5/8) |

## Stage matrix

| 案例 | Retrieval | Evidence | Citation | Answer | 最终 |
|---|---|---|---|---|---|
| POS001 | SUCCESS | SUFFICIENT | READY | FULL_ANSWER | COMPLETED |
| POS002 | SUCCESS | PARTIAL | PARTIAL | ERROR: ANSWER_SCHEMA_INVALID | E2E_ERROR |
| POS003 | SUCCESS | INSUFFICIENT | BLOCKED | REFUSAL | COMPLETED |
| POS004 | SUCCESS | PARTIAL | PARTIAL | PARTIAL_ANSWER | COMPLETED |
| POS005 | SUCCESS | SUFFICIENT | READY | FULL_ANSWER | COMPLETED |
| POS006 | SUCCESS | PARTIAL | PARTIAL | ERROR: INVALID_SUPPORT_REFERENCE | E2E_ERROR |
| POS007 | SUCCESS | PARTIAL | PARTIAL | PARTIAL_ANSWER | COMPLETED |
| POS008 | SUCCESS | PARTIAL | PARTIAL | ERROR: PARTIAL_SCOPE_VIOLATION | E2E_ERROR |

## Failure root causes

- `DEMO002` / `DEMO013`: same Evidence-boundary family, classified `EVIDENCE_REQUIRED_POINT_MISMATCH`; retrieval succeeded but public trace records insufficient Evidence, blocked Citation, and refusal. Point-level internals are not present in the historical artifact, so exact sub-cause is bounded.
- `DEMO012`: isolated `CITATION_CONTRACT_BLOCK`; historical trace records Citation blocked after retrieval success and no Answer model call. The old public artifact lacks support units/excluded candidates, so exact integrity reason cannot be recovered; this is a data/contract boundary, not an Answer-generation failure.
- `POS003`: `EVIDENCE_OVER_REJECT`; related frozen-KB spans were retrieved, but the eligibility point was marked `NOT_SUPPORTED` at score 0.357143 and candidates were excluded, causing safe refusal.
- `POS002`, `POS006`, `POS008`: `OTHER`, Answer contract family. Model was called after partial support, then output validation failed respectively for multiple claims, an unknown support ID, and omitted allowed points. These are runtime Answer-contract errors, not retrieval misses.

## Failure-family summary

The dominant positive-path blocker is the Answer contract under `PARTIAL` support (3/8 cases). Evidence over-rejection is a separate positive-path issue (1/8). DEMO002 and DEMO013 are the same bounded Evidence family; DEMO012 is a separate Citation boundary.

## Latency

Slowest positive case: `{slowest['demo_id']}`, {slowest['latency']['total_ms']:.1f} ms. Layer timings: retrieval {layer['retrieval']:.1f} ms, Evidence {layer['evidence']:.1f} ms, Citation {layer['citation']:.1f} ms, Answer {layer['answer']:.1f} ms. The Answer/model layer dominates; this is not a Retriever/Citation latency bottleneck. Separate cold/warm initialization was not instrumented in this validation run.

## Readiness and frozen integrity

Positive-path status: `DEMO_BLOCKED`. No KB/chunk/embedding/Retriever/Evidence/Citation/Answer/Prompt/frozen-bundle/runtime-decision logic was modified in this validation pass; only validation inputs, runners, traces, and reports were added.

## Artifacts

- `data/positive_demo_question_set_v1.jsonl`
- `results/positive_case_provenance_v1.json`
- `results/positive_demo_results_v1.jsonl`
- `results/positive_demo_summary_v1.json`
- `results/demo_failure_trace_v1.json`
- `results/latency_trace_v1.json`

## Limitations

Historical DEMO002/012/013 results expose stage statuses but not the point-level Evidence/Citation package, so their exact sub-root causes cannot be reconstructed beyond the recorded boundary. Answer model timing is observational for this run and does not provide a separate cold/warm initialization metric.

## One next task

执行一次 **Answer V1 partial-support contract review**：仅围绕 POS002/POS006/POS008 的 schema/reference/scope 错误，复核模型输出与既有 Answer contract 的边界，并先补齐可重复的诊断测试；本轮不修改 KB、Retriever、Evidence、Citation 或 Prompt。
'''
(ROOT / 'experiments' / 'positive_demo_validation_v1' / 'reports').mkdir(parents=True, exist_ok=True)
(ROOT / 'experiments' / 'positive_demo_validation_v1' / 'reports' / 'positive_demo_validation_report_v1.md').write_text(report, encoding='utf-8')
print('wrote', OUT / 'demo_failure_trace_v1.json')
print('wrote', OUT / 'latency_trace_v1.json')
print('wrote', ROOT / 'experiments' / 'positive_demo_validation_v1' / 'reports' / 'positive_demo_validation_report_v1.md')
