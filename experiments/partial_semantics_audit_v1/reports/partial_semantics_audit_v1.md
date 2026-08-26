# Production PARTIAL False-Promote Semantics Audit V1

## Source freeze

The source freeze passed and records all 24 target IDs, source hashes, current
production decisions, and safety-set labels. The target list contains 23 current
production `PARTIAL` cases and one provenance exception: F04 is currently
`INSUFFICIENT` in the production primary path but was listed because the previous
Guarded semantic-rescue candidate produced `PARTIAL`.

## Reconstructed production semantics

The frozen runtime has three Evidence decisions: `SUFFICIENT`, `PARTIAL`, and
`INSUFFICIENT`; downstream refusal is the behavior for `INSUFFICIENT`, not a
separate Evidence enum. `PARTIAL` maps to `ALLOW_PARTIAL_ANSWER`, and
Citation/Answer may answer only mapped `SUPPORTED` or `PARTIALLY_SUPPORTED`
point units.

The decisive implementation behavior is that a point becomes
`PARTIALLY_SUPPORTED` when its lexical score is at least 0.18 and no *extracted*
entity is missing. Missing requested attributes do not prevent that point status.
The README also permits a PARTIAL answer when a requested attribute remains
incomplete, but does not define when topic-level lexical overlap is sufficiently
"usable". This is recorded as `PARTIAL_SEMANTICS_CONFLICT` / underspecification.

## Adjudication

| Audit class | Count | Future use |
|---|---:|---|
| CONFIRMED_PRODUCTION_FALSE_PROMOTE | 16 | HARD_NEGATIVE_CANDIDATE |
| VALID_PARTIAL | 0 | VALID_PARTIAL_TRAINING_CANDIDATE |
| LABEL_POLICY_MISMATCH | 7 | EVAL_POLICY_FIX_REQUIRED |
| HUMAN_REVIEW_REQUIRED | 1 | HUMAN_REVIEW |

The seven label-policy mismatches are explicit requested-attribute omissions
(amount, deadline, contact, location, or time) where frozen documentation allows
the incomplete `PARTIAL` semantics but the safety gold uses an all-or-nothing
`NOT_SUPPORTED` semantics. They are not automatically re-labelled or offered as
hard negatives.

The 16 confirmed false promotes are dominated by single-required-point lexical
partials with critical scope/value/direction/OOD conditions absent from the
production constraint model. Root causes include scope/degree, numeric value,
negation/logical direction, multi-object decomposition, and OOD topic-nearness.

## Systemic finding

`SYSTEMATIC_PARTIAL_BOUNDARY_WEAKNESS` is present. The current runtime can emit
`PARTIAL` from moderate lexical overlap without representing several critical
constraints (degree, scope, numeric values, negation, objects) as entities or
conflicts. This report records the baseline weakness only; it does not propose or
implement a rule, threshold, model, or training-data fix.

## Decision

**MIXED_PARTIAL_SEMANTICS**

There are confirmed production false promotes and a distinct label-policy mismatch
subset. One source-provenance discrepancy requires human review. No production,
frozen evaluation, or historical Semantic Rescue artifact was modified. No
fine-tuning dataset was created.
