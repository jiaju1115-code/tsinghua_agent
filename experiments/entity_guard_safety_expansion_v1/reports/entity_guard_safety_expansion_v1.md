# Entity Guard Safety Expansion V1

## Scope and freeze

This is an experiment-only evaluation of the unchanged `ENTITY_GUARD` implementation
from `experiments/evidence_paraphrase_mapping_v1/src/mapping_candidates.py`.
Production Evidence, thresholds, Runtime, Retriever, KB, and frozen evaluation data
were not modified. The production hashes and the prior DEMO002/POS003/DEMO013
outcomes are recorded in `audit/baseline_freeze.json`.

## Safety set

The set contains 33 deterministic cases:

- A pseudo-entity positives: 7
- B true-entity-missing negatives: 7
- C mixed pseudo + true entity: 5
- D adversarial hard negatives: 7
- prior regression/retention controls: 7

Every case records its source type, required point, expected entity behavior,
pseudo entities, required entities, evidence trace, and promotion failure rationale.

## Results

| Metric | Result |
|---|---:|
| Overall accuracy | 0.3030 |
| Support precision | 0.5217 |
| Support recall | 0.9231 |
| Confirmed false promotes | 11 / 20 negatives |
| False-promote rate | 0.5500 |
| True-entity preservation | 0.8182 |
| Mixed-case accuracy | 0.6000 |
| Adversarial hard-negative accuracy | 0.0000 |
| Pseudo-entity family accuracy | 0.7143 |
| DEMO002 recovery | PARTIAL |
| POS003 recovery | PARTIAL |
| Positive retention accuracy | 0.7692 |
| Refusal/insufficient retention accuracy | 0.0000 |

The 11 confirmed false promotes are fully traced in
`audit/false_promote_audit.json`. Representative failure modes are:

1. student type, degree level, enrollment stage, application target, and year
   are not retained as hard constraints after the existing entity extraction;
2. a wrong location/entity can be reduced to the matching institution suffix;
3. negation and multi-object (奖学金 AND 助学金) requests inherit positive
   scholarship evidence;
4. an out-of-domain creative request can cross the partial threshold through
   lexical overlap.

## Decision

**ENTITY_GUARD_REJECTED_FOR_SAFETY**

The original candidate is not eligible for shadow integration. No refined
candidate was forced: the observed failures span entity extraction, attribute
and scope preservation, negation/multi-object semantics, and OOD boundary
handling. A safe repair cannot be justified as a single low-complexity
paraphrase-prefix rule from this experiment alone.

DEMO013 remains unrecovered / NOT_SUPPORTED as required. No production
integration or candidate replacement was made.
