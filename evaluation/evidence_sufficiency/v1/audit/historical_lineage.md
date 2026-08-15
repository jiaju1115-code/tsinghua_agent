# Evidence Sufficiency lineage: V0.1 -> V0.2 -> V0.3 -> V0.4 -> Runtime V1

This is an artifact/code/data cross-check, not a restatement of README claims.

| Version | Actual implementation and data | Verified result type | Runtime disposition |
|---|---|---|---|
| V0.1 | Offline deterministic query decomposition plus character-term overlap; fixed mismatch tokens and navigation heuristics; no ML. 12 development, 5 adjudicated holdout, 40 development-derived synthetic cases. | Historical tiny holdout 5/5; development 9/12; synthetic 18/40 with 7 false-sufficient. | Three-state coverage rule: `REUSE_AS_IS`. Basic decomposition/traceability: `REUSE_WITH_ADAPTATION`. Sample-specific mismatch token list and V0.1 thresholds: `REJECT_FOR_RUNTIME`. Metrics: `EVALUATION_ONLY`. |
| V0.2 | Deterministic sentence-span n-gram coverage, entity/document overlap, contamination and short-fragment rules; selected v0.2-d. It names a score "semantic" but uses no semantic model. | Historical internal holdout 7/8; synthetic holdout 15/24; wrong-document holdout 0/3; Partial 1/3. | Span extraction, conservative entity check: `REUSE_WITH_ADAPTATION`. Thresholds and the "semantic span" claim: `REJECT_FOR_RUNTIME`. Results: `EVALUATION_ONLY`. |
| V0.3 | Minimal-point parser, requested-attribute feature and 15 lexical/shape features feeding a Random Forest; final threshold 0.58. 147 unique Query+Evidence rows = 49 real adjudicated + 98 synthetic, but only 49 unique queries and extensive overlap groups. | Nested CV on seen calibration families: real 34/49, Macro-F1 0.611, false-sufficient 4/15; synthetic 85/98, Macro-F1 0.830, false-sufficient 2/78. Explicit `NOT_READY_FOR_NEW_BLIND`. | Minimal-core/attribute/optional concepts: `REUSE_WITH_ADAPTATION`. Candidate model, thresholds and claimed "semantic entailment" policy: `REJECT_FOR_RUNTIME`. Historical model metrics: `EVALUATION_ONLY`. |
| V0.4 | Frozen offline prototype intended to call local `deepseek-r1:7b` for core points and a support matrix. The first real prompt exceeded the served 4096 context and returned HTTP 502. No schema-valid sample, semantic matrix, CV, regression, or model comparison exists. | `SEMANTIC_ENGINE_UNAVAILABLE`; `NOT_READY_FOR_NEW_BLIND`. | Core/requested/optional schema concepts: `REUSE_WITH_ADAPTATION`. Local engine, prompt, scores and proposed RF: `REJECT_FOR_RUNTIME`. Semantic entailment status: not implemented. |
| Runtime V1 | New transparent deterministic policy consuming only `RAG_RETRIEVAL_V1` Top-5. No classifier, LLM, network, retrieval retry, generation or citation. | Unit, compatibility regression, integration and determinism diagnostics are recorded separately. | Conservative lexical/structural support proxy, explicitly not semantic entailment. Fail-closed behavior is the production objective. |

## Label lineage

Historical labels are `EVIDENCE_SUFFICIENT`, `EVIDENCE_PARTIAL`, and `EVIDENCE_INSUFFICIENT`. Runtime V1 maps them without changing semantics to `SUFFICIENT`, `PARTIAL`, and `INSUFFICIENT`: all minimal core points and requested attributes supported; only a supported subset; or no safe core answer, respectively.

## Data status and leakage

- Real labels are historical human-adjudicated references, not absolute gold truth.
- Synthetic cases are construction/proxy data and are reported separately.
- V0.3 states `ALL_INPUTS_ARE_SEEN_CALIBRATION_DATA`; its final model is trained on all 147 rows.
- V0.3 reports 23 exact-pair duplicate groups before canonicalization; direct recomputation on the 147 retained rows gives 21 duplicated query-evidence hash groups. It has 44 normalized-query overlap groups.
- Forty of 49 normalized-query families and 28 of 44 source-query variant families crossed historical V0.3 CV folds.
- All 38 RAG V1 and Answer V0 normalized queries, 11/42 Router blind-shadow queries, and 11/12 E2E12 queries overlap V0.3 normalized queries.
- V0.4 reused the same 147 rows and did not create an independent blind set.
- No historical metric may be described as official held-out E2E performance.

## Production exclusions

Runtime V1 must not load `candidate_model.joblib`, reuse 0.58 as a production probability threshold, call the V0.4 Ollama prompt, emit fabricated entailment probabilities, use benchmark labels/IDs as features, or infer support from retrieval similarity alone.
