# Evidence Paraphrase-Invariant Mapping Experiment V1

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
