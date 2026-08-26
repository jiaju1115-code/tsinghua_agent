# Answer V1 Partial-Support Output Contract Review

## 1. Root Cause

POS002, POS006, and POS008 are one failure family: `MODEL_SCHEMA_NONCOMPLIANCE`.

- POS002: the raw JSON is parseable, but emits two claims for `P1`; `P2` is not an allowed point in that partial package. Failure stage: claim validation, duplicate required-point rule.
- POS006: the raw JSON is parseable, but the `P2` claim declares a support unit mapped to another point. Failure stage: support-reference validation.
- POS008: the raw JSON is parseable, but omits allowed `P2`. Failure stage: partial-scope completeness validation.

All three reached Runtime V1 → Answer V1 → prompt construction → model invocation → raw generation → JSON parsing. They failed in Answer claim validation and were returned as `E2E_ERROR` by the current orchestrator.

## 2. Contract Mismatch

No Prompt/parser/validator contract drift was found.

- Prompt: one exact factual claim per allowed required point, with a support ID mapped to that point.
- Parser: requires the frozen top-level keys and claim keys, unique point IDs, legal support IDs, and complete allowed scope.
- Validator: converts invalid or unsupported output to fail-closed refusal.
- Runtime: treats Answer `ERROR` as an orchestration error rather than a completed `PARTIAL_ANSWER`.

The mismatch is between the model’s emitted claims and the existing contract, not between Prompt and parser. The detailed evidence is in `answer_v1_partial_contract_failure_matrix.json`.

## 3. Fix Implemented

No production fix was applied. A parser relaxation would need to discard a duplicate claim, remap a support ID, or invent a missing claim; each would violate the fail-closed requirements. Prompt wording, generation semantics, model, sampling, safety policy, and upstream stages remain unchanged.

Result: `ANSWER_PARTIAL_CONTRACT_FIX_BLOCKED`.

## 4. Changed Files

This turn added only audit, targeted-test, and report artifacts:

- `scripts/trace_answer_v1_partial_contract_v1.py`
- `scripts/build_answer_v1_partial_contract_matrix_v1.py`
- `tests/answer_v1_partial_contract/test_partial_contract_fail_closed.py`
- `experiments/answer_v1_partial_contract_fix/audit/answer_v1_partial_contract_runtime_trace_v1.json`
- `experiments/answer_v1_partial_contract_fix/audit/answer_v1_partial_contract_failure_matrix.json`
- `experiments/answer_v1_partial_contract_fix/results/answer_v1_partial_contract_regression_results.json`
- `experiments/answer_v1_partial_contract_fix/results/before_after_metrics.json`

## 5. Fail-Closed Preservation

Preserved and tested:

- malformed JSON remains rejected;
- duplicate or missing required fields remain rejected;
- invalid status remains rejected;
- unsupported support references remain rejected;
- incomplete partial scope remains rejected;
- valid `PARTIAL_ANSWER` shape remains accepted without widening support scope.

## 6. Targeted Regression

The three real cases were rerun through Runtime V1 with a recording adapter. Their raw outputs, parser/validation outcomes, and final statuses are captured. The targeted regression suite passed: `3 passed`.

Full-answer, refusal, and malformed-output production cases were not rerun after a fix because no production fix was applied; rerunning them would not change the blocked decision. Existing unrelated failures remain recorded separately as `PRE_EXISTING_UNRELATED_TEST_FAILURE`.

## 7. Positive-path Before / After

| Metric | Before | After |
|---|---:|---:|
| Positive Answer Rate | 0.500 | N/A — blocked |
| Full-support Rate | 0.250 | N/A — blocked |
| Runtime Completion | 0.625 | N/A — blocked |
| Citation Presence | 1.000 | N/A — blocked |
| Paraphrase Robustness | 1/3 | N/A — blocked |

## 8. Remaining Failures

This turn did not alter and does not reclassify the known upstream/adjacent failures:

- POS003: Evidence over-reject;
- DEMO002 and DEMO013: Evidence required-point mismatch family;
- DEMO012: Citation contract block.

## 9. Pre-existing Tests

The two previously observed failures remain unrelated to this Answer partial-contract review:

1. Prompt Freeze exception-message matching;
2. Demo CLI encoding/text assertion.

They were not modified.

## 10. Demo Readiness

`DEMO_BLOCKED`: the three partial-support contract failures remain runtime correctness blockers, although the Answer validator itself remains safely fail-closed.

## 11. Frozen Integrity

KB, chunks, embeddings, Retriever, Evidence decision semantics, Citation decision semantics, Prompt content, Prompt Freeze, Frozen Bundle, generation model, and refusal policy: **not modified**.

Answer generation semantics: **not modified**. Only diagnostic/audit and targeted-test artifacts were added.

## 12. Main Artifacts

- `D:\python_projects\tsinghua_ai\experiments\answer_v1_partial_contract_fix\audit\answer_v1_partial_contract_runtime_trace_v1.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_partial_contract_fix\audit\answer_v1_partial_contract_failure_matrix.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_partial_contract_fix\results\answer_v1_partial_contract_regression_results.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_partial_contract_fix\results\before_after_metrics.json`

## 13. Remaining Highest-priority Failure Family

`Other`: model-output contract compliance under partial support. It is the only family that directly blocks the Answer runtime after Evidence and Citation have produced a valid partial package.

## 14. Recommended Next Single Task

`Answer model-output compliance investigation`: use the captured raw outputs to determine whether the frozen local model can be made contract-compliant without changing Prompt semantics, model, sampling, or fail-closed validation. If not, explicitly approve an upstream/model change; do not weaken the parser.
