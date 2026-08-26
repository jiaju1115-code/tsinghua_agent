# Semantic Rescue Safety Expansion V1

## Baseline and scope

Baseline reproduction passed. Production Evidence uses the frozen partial lexical
threshold `0.18`; this experiment did not change it. The historical semantic-rescue
implementation hash, production Evidence/config hashes, Retriever adapter hash,
Citation runtime hash, and Answer runtime hash are in `audit/baseline_freeze.json`.
The post-run hash verification matched every frozen production input.

The experiment reproduces the historical C0 candidate as
`SEMANTIC_RESCUE_ORIGINAL`. It does **not** reuse the rejected Entity Guard
prefix-ignore behavior. C1, `SEMANTIC_RESCUE_GUARDED`, is only a secondary
lexical-fail rescue: it preserves the production primary path and blocks a rescue
when an entity, numeric, temporal, scope, negation, multi-object, required-point,
or OOD condition is present.

## Safety set

50 cases were evaluated: 5 REAL, 8 HISTORICAL, 29 SYNTHETIC, and 8 ADVERSARIAL.
The family counts are A paraphrase positive 8, B entity mismatch 6, C numeric 5,
D temporal 5, E negation/logical 5, F required-point mismatch 5, G multi-object 5,
H OOD/topic-near 5, and regression controls 6.

## Results

| Measure | C0 original | C1 guarded |
|---|---:|---:|
| DEMO013 | PARTIAL | PARTIAL |
| Paraphrase recovery | 0.875 | 0.875 |
| Rescue eligible / triggered | 1 / 1 | 1 / 1 |
| Rescue-induced false promotes | 0 | 0 |
| Final false promotes | 24 | 24 |
| Refusal retention | 0.00 | 0.00 |
| Insufficient retention | 0.40 | 0.40 |
| Positive retention | 0.80 | 0.80 |

The 24 final false promotes are inherited from the frozen production primary path:
all were already `PARTIAL` before either secondary rescue could run. They are not
rescue-induced, but they prevent this data set from satisfying the requested
end-to-end safety gate. The detailed attribution is in `audit/false_promote_audit.json`.

For C1, the strict hard-safety gate blocked 14 entity failures, 14 numeric/attribute
constraints, 5 temporal constraints, 10 scope constraints, 2 negation cases,
4 multi-object cases, 18 required-point alignment failures, and 4 OOD cases. The
only eligible case was DEMO013, which had a located frozen evidence sentence and
no hard-constraint conflict.

## Threshold robustness and latency

The dense-score bands were computed from the full observed distribution, not from
DEMO013: T1=0.628707, T2=0.642234, T3=0.683778. T1 recovers DEMO013; T2 and T3
do not. This is `THRESHOLD_FRAGILITY`, independently sufficient to reject the
candidate for shadow integration.

Mean baseline evaluation latency was 47.035 ms. The experiment-only gate added
7.763 ms for its eligible case and 9.525 ms for blocked cases (p95 12.579 ms).
No external API or generative model was used.

## Decision

**SEMANTIC_RESCUE_REJECTED_FOR_SAFETY**

Although C1 does not create a new false promotion on the tested lexical-fail path,
it depends on a threshold band that is not robust and cannot satisfy the required
end-to-end safety/retention gate in the frozen baseline environment. DEMO002 and
POS003 remain blocked as expected because their existing entity checks fail.

No production integration, threshold change, Entity Guard revival, or frozen
regression mutation was performed. Because the rejection gate was reached, a full
downstream frozen Runtime regression was not run.
