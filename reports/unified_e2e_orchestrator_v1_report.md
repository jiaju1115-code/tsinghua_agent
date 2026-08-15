# Unified E2E Orchestrator V1 Formalization Report

## Scope and outcome

This task formalizes only the orchestration layer over four already-frozen runtimes:

`RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> ANSWER_GENERATION_V1`

It does not modify upstream runtime code, schemas, tests, prompts, model configuration, corpus, index, or freeze manifests. It does not execute E2E-50, a held-out benchmark, quality tuning, re-review, re-retrieval, repair, fallback, external search, or production writes.

## Contract audit

The four upstream public interfaces are directly compatible. The only adapters are mechanical projection of the Answer result into the compact orchestrator output and deterministic joins across already-existing provenance IDs. No unresolved semantic conflict was found. Full details are in `evaluation/e2e_orchestrator/runtime_v1/audit/contract_compatibility_audit.md`.

## Architecture

`run_e2e(query, case_id, ...)` validates input, calls each frozen layer exactly once and in order, validates the exact returned schema/version/query/case identity after every call, then emits a compact result. A session object additionally rejects duplicate `case_id` values. An upstream exception, error, version mismatch, schema mismatch, query/case mismatch, status conflict, or provenance gap stops the chain and produces `E2E_ERROR`; no subsequent layer is called.

The orchestrator contains no retry, fallback, repair, re-retrieval, search, prompt logic, semantic classifier, answer generation logic, or support inference.

## Frozen integrity

The pre-input audit verified the five canonical frozen statuses (Knowledge Base, Retriever, Evidence, Citation, Answer), every manifest sidecar, and every explicitly declared artifact hash. The formal inventory contains 74 unique declared files and has combined SHA-256 `825b92ba1ca30902fbbbf32289bfc256a07a65e3f2b5086056ccd96dee289b0f`.

All seven existing upstream test entry points were run unchanged with their output globals redirected to the new orchestrator validation area. They passed 7/7. This non-mutating method prevented overwriting frozen upstream test results. The same formal upstream inventory hash was observed after those tests and again during final audit.

## Status propagation

- Citation `READY` maps to Answer `FULL_ANSWER`.
- Citation `PARTIAL` maps to Answer `PARTIAL_ANSWER`.
- Citation `BLOCKED` maps to Answer `REFUSAL`, with `diagnostics.model_called == false` required.
- The frozen Answer prompt-injection guard may safely turn READY/PARTIAL into REFUSAL; the orchestrator preserves and marks this boundary.
- Other mapping conflicts fail closed as `FROZEN_CONTRACT_CONFLICT`.

Evidence, Citation and Answer blocking/refusal remain distinct output statuses and distinct engineering counts.

## Provenance

Every factual claim must join through:

`claim -> required point -> Citation support unit -> source -> retrieved chunk -> document`

Only IDs and mappings emitted by the frozen runtimes are used. No semantic linkage is invented. Any missing or inconsistent link produces `PROVENANCE_LINK_UNAVAILABLE` and `E2E_ERROR`. Restricted-source document title, URL and category are replaced with null in unified provenance; no raw prompt, chain-of-thought, support span text, Retriever Top-5 text, credentials, or restricted acquisition metadata is placed in compact traces.

## Validation

- Existing upstream entry points: 7/7 PASS.
- New orchestrator unit scenarios: 37/37 PASS (minimum requirement: 20).
- Integration cases: 4/4 PASS.
- Repeatability excluding latency/timestamps: PASS.
- Exact output field set: PASS.
- Fail-closed/no-skip/one-call/no-retry behavior: PASS.
- Prompt-injection contract fixture: deterministic REFUSAL and no model call, PASS.

## Natural runtime cases

Two natural live frozen-chain cases were executed:

1. Scholarship conditions/deadline query: Evidence `PARTIAL` -> Citation `PARTIAL` -> Answer `PARTIAL_ANSWER`.
2. Library opening-hours query: Evidence `INSUFFICIENT` -> Citation `BLOCKED` -> Answer `REFUSAL`; no model call.

Natural frozen READY coverage: 0.

The READY path used a declared contract fixture: live frozen retrieval rows plus a schema-valid Evidence SUFFICIENT fixture and deterministic schema-valid model-adapter fixture, while Citation, Answer runtime validation/construction, provenance, and orchestration remained live. This verifies interface behavior only and is not natural runtime or quality evidence.

## Engineering metrics

For the four validation outputs (two natural cases and two declared contract fixtures), pipeline completion was 4/4 (100.0%) and E2E errors were 0/4 (0.0%). Evidence `INSUFFICIENT` was 1/4 (25.0%), Citation `BLOCKED` was 1/4 (25.0%), and Answer `REFUSAL` was 2/4 (50.0%). These fixture-mixed engineering counts are not performance estimates.

Observed layer latency means were: retrieval 14.573 ms, Evidence 6.388 ms, Citation 1.772 ms, and Answer 3585.033 ms. The skewed Answer mean reflects one live local-model generation; per-case values and orchestration overhead are preserved in `engineering_metrics.json`.

## Known gaps and limitations

- Natural frozen Citation READY coverage is zero; READY is contract-fixture-only.
- Evidence V1 explicitly uses a deterministic lexical/structural proxy, not semantic entailment.
- Citation provenance integrity is not citation correctness.
- Answer V1 explicitly lacks semantic unsupported-claim detection.
- The frozen corpus/runtime output visibly contains legacy text-encoding corruption in some retrieved and generated Chinese text. This task does not repair frozen upstream content.
- Local small-model generation has materially higher and variable latency than deterministic layers and can fail its frozen status gate; the orchestrator correctly fails closed.
- No answer-quality, support-correctness, citation-correctness, unsupported-claim, or refusal-appropriateness metric was measured here.

## Held-out status

NO held-out E2E evaluation was executed. No populated held-out benchmark cases or answers were created. The protocol, case schema, review template, and freeze rules were designed only. Contract fixtures and natural engineering checks cannot be reported as held-out performance.

## Freeze decision

The freeze is authorized only if all 20 machine-checked gates pass and pre/post frozen-input inventories are identical. The only allowed manifest statuses are `UNIFIED_E2E_ORCHESTRATOR_V1_FROZEN` and `NOT_FROZEN`.

Final result: 20/20 gates passed, upstream pre/post inventory is identical, and status is `UNIFIED_E2E_ORCHESTRATOR_V1_FROZEN`.
