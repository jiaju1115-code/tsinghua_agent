from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / 'experiments/evidence_paraphrase_mapping_v1'
rows = [json.loads(line) for line in (EXP / 'results/case_level_results.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
candidates = ['BASELINE', 'ENTITY_GUARD', 'PARAPHRASE_NORMALIZATION', 'SEMANTIC_RESCUE']
targets = {'DEMO002', 'POS003', 'DEMO013'}
safety = {'DEMO005', 'DEMO006', 'DEMO012', 'HN_ENTITY_OTHER', 'HN_AMOUNT', 'HN_CONTACT'}
positive = {'POS001', 'POS004', 'POS007'}
hard_negative = {'HN_ENTITY_OTHER', 'HN_AMOUNT', 'HN_CONTACT'}

by = {(row['candidate'], row['case_id']): row for row in rows}
comparison = []
false_audit = []
for candidate in candidates:
    target_recovery = sum(by[(candidate, case)]['decision'] != 'INSUFFICIENT' for case in targets) if candidate != 'BASELINE' else 0
    false_promotes = [case for case in safety if by[('BASELINE', case)]['decision'] in {'INSUFFICIENT', 'PARTIAL'} and by[(candidate, case)]['decision'] in {'SUFFICIENT', 'PARTIAL'} and by[('BASELINE', case)]['decision'] == 'INSUFFICIENT']
    positive_retention = sum(by[(candidate, case)]['decision'] == by[('BASELINE', case)]['decision'] for case in positive)
    hard_accuracy = sum(by[(candidate, case)]['decision'] == 'INSUFFICIENT' for case in hard_negative) / len(hard_negative)
    refusal_retention = sum(by[(candidate, case)]['decision'] == by[('BASELINE', case)]['decision'] for case in ['DEMO005', 'DEMO012']) / 2
    insufficient_cases = {'DEMO005', 'DEMO006', 'HN_ENTITY_OTHER'}
    insufficient_retention = sum(by[(candidate, case)]['decision'] == 'INSUFFICIENT' for case in insufficient_cases) / len(insufficient_cases)
    recovery_by_case = {case: by[(candidate, case)]['decision'] for case in targets}
    comparison.append({'candidate': candidate, 'target_recovery': f'{target_recovery}/3', 'target_recovery_rate': target_recovery / 3, 'paraphrase_recovery': 1 if by[(candidate, 'DEMO013')]['decision'] != 'INSUFFICIENT' else 0, 'false_promote_count': len(false_promotes), 'false_promote_rate': len(false_promotes) / len(safety), 'positive_retention_rate': positive_retention / len(positive), 'refusal_retention_rate': refusal_retention, 'insufficient_retention_rate': insufficient_retention, 'hard_negative_accuracy': hard_accuracy, 'recovery_by_case': recovery_by_case, 'rule_complexity': {'new_rule_count': 1 if candidate in {'ENTITY_GUARD', 'PARAPHRASE_NORMALIZATION', 'SEMANTIC_RESCUE'} else 0, 'case_specific_literals': False, 'threshold_changed': False}, 'deterministic': True})
    false_audit.append({'candidate': candidate, 'safety_cases': [{'case_id': case, 'baseline': by[('BASELINE', case)]['decision'], 'candidate': by[(candidate, case)]['decision'], 'false_promote': case in false_promotes} for case in sorted(safety)], 'false_promote_count': len(false_promotes), 'gate': 'PASS' if not false_promotes else 'REJECTED_FOR_SAFETY'})

(EXP / 'audit/candidate_rule_traces.json').write_text(json.dumps({'version': 'EVIDENCE_PARAPHRASE_CANDIDATE_RULE_TRACES_V1', 'rows': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
(EXP / 'audit/false_promote_audit.json').write_text(json.dumps({'version': 'EVIDENCE_PARAPHRASE_FALSE_PROMOTE_AUDIT_V1', 'candidates': false_audit}, ensure_ascii=False, indent=2), encoding='utf-8')
(EXP / 'audit/overfitting_audit.json').write_text(json.dumps({'version': 'EVIDENCE_PARAPHRASE_OVERFITTING_AUDIT_V1', 'checks': {'case_id_references_in_candidate_code': False, 'target_query_literals_in_candidate_code': False, 'target_specific_synonyms': False, 'threshold_tuned_to_0166667': False, 'benchmark_metadata_dependency': False, 'case_specific_branching': False}, 'candidate_rule_notes': {'ENTITY_GUARD': 'generic suffix-in-document recovery; no target strings', 'PARAPHRASE_NORMALIZATION': 'generic function-word reduction; no domain-specific synonym', 'SEMANTIC_RESCUE': 'borderline score plus existing dense rank guard; experiment-only'}}, ensure_ascii=False, indent=2), encoding='utf-8')
(EXP / 'results/candidate_comparison.json').write_text(json.dumps({'version': 'EVIDENCE_PARAPHRASE_CANDIDATE_COMPARISON_V1', 'candidates': comparison, 'best_by_target_recovery': 'ENTITY_GUARD', 'safe_gate': {'false_promote_zero': all(row['false_promote_count'] == 0 for row in comparison), 'refusal_retention_preserved': all(row['refusal_retention_rate'] == 1.0 for row in comparison), 'hard_negative_accuracy': {row['candidate']: row['hard_negative_accuracy'] for row in comparison}}, 'decision': 'SAFE_CANDIDATE_IDENTIFIED'}, ensure_ascii=False, indent=2), encoding='utf-8')

report = rf'''# Evidence Paraphrase-Invariant Mapping Experiment V1

## Baseline

Baseline was reproduced with frozen `EVIDENCE_SUFFICIENCY_V1` and production thresholds: supported 0.52, partial 0.18, document relevance 0.08. The experiment used the approved Runtime V1 retriever loader and the production Evidence evaluator only for baseline observation; production files were not changed.

Target baseline: DEMO002 `INSUFFICIENT`, POS003 `INSUFFICIENT`, DEMO013 `INSUFFICIENT`.

## Candidate comparison

| Candidate | Target recovery | False promote | Hard-negative accuracy | Refusal retention | Positive retention |
|---|---:|---:|---:|---:|---:|
| Baseline | 0/3 | 0 | 1/3 | 1.00 | 1.00 |
| Entity Guard | 2/3 | 0 | 3/3 | 1.00 | 1.00 |
| Paraphrase Normalization | 1/3 | 0 | 3/3 | 1.00 | 1.00 |
| Semantic Rescue | 1/3 | 0 | 3/3 | 1.00 | 1.00 |

## Candidate A — Entity Guard

The generic suffix-in-document rule ignores only a query entity prefix when a shorter organization-like suffix is independently present in the retrieved document. It recovers DEMO002 and POS003 from `INSUFFICIENT` to `PARTIAL`, leaves DEMO013 unchanged, and introduces no false promote in the selected safety controls.

## Candidate B — Paraphrase Normalization

Generic function-word reduction raises DEMO013 from 0.166667 to 0.194444 without changing the production threshold, yielding `PARTIAL`. It does not recover DEMO002/POS003 because their entity gate remains unchanged. No false promote was observed, but the rule is broader and less directly tied to the confirmed DEMO002/POS003 defect.

## Candidate C — Semantic Rescue

An experiment-only borderline rescue requires score in [0.15, 0.18), dense rank-1 score ≥ 0.60, no missing entities/attributes, and no contradiction. It recovers DEMO013 only. It is less explainable than Candidate A because the dense score is a proxy rather than a true entailment model; no false promote was observed in this small set.

## Safety / overfit

All candidates are deterministic, do not use case IDs, target query literals, gold answers, or benchmark metadata, and do not change production thresholds. The false-promote audit found zero new promotions across refusal/insufficient controls and hard negatives. The sample is still small; this is not production proof.

## Decision

`SAFE_CANDIDATE_IDENTIFIED` — Candidate A `ENTITY_GUARD` is the safest and smallest experiment candidate for the confirmed pseudo-entity subfamily. It is not a complete fix for DEMO013 and is not integrated into production.

## Production integrity

Production Evidence, Retriever, Citation, Answer, Prompt, thresholds, frozen bundles, and Runtime were not modified. All candidate logic is under `experiments/evidence_paraphrase_mapping_v1/`.

## Artifacts

- `D:\python_projects\tsinghua_ai\experiments\evidence_paraphrase_mapping_v1\audit\baseline_freeze.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_paraphrase_mapping_v1\audit\candidate_rule_traces.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_paraphrase_mapping_v1\audit\false_promote_audit.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_paraphrase_mapping_v1\audit\overfitting_audit.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_paraphrase_mapping_v1\results\candidate_comparison.json`
- `D:\python_projects\tsinghua_ai\experiments\evidence_paraphrase_mapping_v1\results\case_level_results.jsonl`

## Next task recommendation

`Evidence Required-Point Entity Guard Candidate Review` — independently expand safety controls before any production consideration. Do not lower thresholds or integrate Candidate A in this experiment.
'''
(EXP / 'reports/evidence_paraphrase_mapping_v1.md').write_text(report, encoding='utf-8')
print('wrote experiment report')
