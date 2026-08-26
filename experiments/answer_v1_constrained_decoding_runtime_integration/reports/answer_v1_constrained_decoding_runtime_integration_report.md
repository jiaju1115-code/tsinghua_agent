# Answer V1 Constrained Decoding Runtime Integration

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
| Positive Answer Rate | 0.500 | 0.875 |
| Full-support Rate | 0.250 | 0.250 |
| Runtime Completion | 0.625 | 1.000 |
| Citation Presence | 1.000 | 1.000 |
| Paraphrase Robustness | 1/3 | 3/3 |

The After values come from a real Runtime V1 run of the unchanged 8-case positive set, not from the 3-case experiment.

## 7. Safety Preservation

The original validator remains the final authority. There is no claim auto-repair, support-ID remapping, required-point filling, citation fabrication, raw-output fallback, bounded retry, or silent unconstrained fallback. Malformed and unsupported outputs remain fail-closed.

## 8. Regression

- Full answer: POS001/POS005 passed.
- Existing partial answer: POS004/POS007 passed.
- Refusal: POS003, DEMO005, and DEMO012 remained safe refusals; DEMO012 preserved the Evidence SUFFICIENT/Citation BLOCKED boundary.
- Legacy replay: default `generate_answer` seam remains unconstrained when no constraint is passed.
- Targeted fail-closed suite: 3 passed.

## 9. Latency

Baseline targeted average: 16.8s. Constrained targeted average: 16.3s. Integrated 8-case average: 10451.5 ms (10.45s), maximum 29714.9 ms. The integrated maximum is generation-dominated; no non-generation stage changed.

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
