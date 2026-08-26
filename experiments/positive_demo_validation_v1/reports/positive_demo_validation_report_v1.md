# Positive-path Demo Validation V1

## Positive-path Readiness

结论：`DEMO_BLOCKED`（正向路径）。8 个 `SHOULD_ANSWER` 案例中只有 4 个进入可交付回答状态，3 个在 Answer 层产生 `E2E_ERROR`，1 个被 Evidence 阻断拒答。现有整体 Demo 结论仍为上一轮的 `DEMO_READY_WITH_LIMITATIONS`，但正向路径本身未达到可演示门槛。

## Metrics

| 指标 | 结果 |
|---|---:|
| Positive Answer Rate | 0.500 (4/8) |
| Full-support rate | 0.250 (2/8) |
| Paraphrase Robustness | 1/3 paraphrase cases answered |
| Citation Presence | 1.000 |
| Runtime completion | 0.625 (5/8) |

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

Slowest positive case: `POS008`, 18836.4 ms. Layer timings: retrieval 24.2 ms, Evidence 19.4 ms, Citation 8.1 ms, Answer 18783.5 ms. The Answer/model layer dominates; this is not a Retriever/Citation latency bottleneck. Separate cold/warm initialization was not instrumented in this validation run.

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
