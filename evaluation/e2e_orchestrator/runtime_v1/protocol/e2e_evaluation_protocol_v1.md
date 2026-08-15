# Held-out E2E Evaluation V1 Protocol (Design Only)

Status: designed and frozen with the runtime; **not executed** in this task.

## Intended unit

One immutable benchmark row contains a unique `case_id`, the exact user query, declared evaluation slice metadata, and an independently prepared human-review rubric. Benchmark construction must be completed and hashed before any runtime answers are generated.

## Execution sequence

1. Freeze benchmark cases, sampling rationale, reviewer rubric, and exclusion policy.
2. Record the frozen orchestrator manifest hash and all five upstream freeze hashes.
3. Execute each case once with no tuning, retry, repair, re-retrieval, or case replacement.
4. Freeze raw compact outputs before human review.
5. Blind reviewers to internal status expectations; adjudicate disagreements under a separately frozen protocol.
6. Report held-out results separately from engineering validation and contract fixtures.

## Metrics to report

- Pipeline completion rate and E2E error rate.
- Evidence `INSUFFICIENT`, Citation `BLOCKED`, and Answer `REFUSAL` counts separately.
- FULL/PARTIAL/REFUSAL distributions.
- Human-reference answer adequacy, support correctness, citation correctness, unsupported-claim rate, and refusal appropriateness, each with raw counts and percentages.
- Retrieval, Evidence, Citation, Answer, orchestration-overhead, and total latency distributions separately.
- Slice results and uncertainty intervals where sample sizes permit.

Human labels are human reference labels unless an independently justified gold-label process exists. Contract fixtures are never quality-evaluation cases. No performance claim is authorized by the runtime validation artifacts.
