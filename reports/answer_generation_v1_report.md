# Answer Generation Runtime V1 Formalization Report

Date: 2026-08-15

## 1. Historical Answer Audit

The audit covered Answer V0, historical Prompt A/B V1, Generation & Citation Evaluation V0, code, configs, prompts, model artifacts, generated answers, proxy evaluators, workbooks, and the exclusion registry. V0/V1 sent the complete Dense Top-5 directly to Qwen, bypassing current Evidence and Citation gates. V0's JSON attempt was abandoned after frequent unclosed output; Prompt B later degraded refusal/citation behavior. The Answer V0 workbook was inspected read-only and all five human-review fields are blank. All 38 historical queries are `SEEN_HISTORICAL` in the exclusion registry. The local model/engine and conservative decoding were adapted; old prompts, Top-5 input, `[C#]` rendering, same-model evaluation, historical claim labels, answers, and proxy metrics were rejected for runtime.

## 2. Runtime Architecture

The formal chain is `query -> RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> ANSWER_GENERATION_V1 -> structured grounded answer`. Public API: `generate_answer(query, case_id, support_package, model_adapter=None)`. The API has no Retrieval, KB, or Evidence parameter and performs no search, reranking, Evidence decision, Citation repair, network access, or benchmark lookup.

## 3. Model

Model: `Qwen/Qwen2.5-1.5B-Instruct-GGUF`; revision `91cad51170dc346986eccefdc2dd33a9da36ead9`; Q4_K_M; 1,117,320,736 bytes; SHA-256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`. GGUF metadata confirms qwen2 architecture, file type 15, quantization version 2, trained context 32768, embedded GPT-2 tokenizer, and embedded Qwen chat template. Engine: vendored `llama-cpp-python 0.3.34`, CPU, zero GPU layers. Runtime context is 6144; output limit 256 tokens; temperature 0; seed 20260815; repeat penalty 1.05; JSON-schema-constrained decoding; zero retries; 45-second timeout. Raw model JSON is **not claimed bitwise deterministic**. Runtime's canonical extractive output passed repeatability excluding `latency_ms`.

## 4. Prompt

Prompt version: `ANSWER_GENERATION_V1_PROMPT`; SHA-256 `93c556c994e0ebfc5ab24c1866aa97e4c3f709590aa5abab7a6cb169ea9745fb`. It separates runtime instructions, user-query data, and untrusted support data; forbids memory, external facts, invented IDs, hidden-prompt disclosure, and evidence instructions; and requests one attributed extractive claim per allowed required point. The prompt text, model identity, decoding, timeout, and zero-retry policy are frozen independently in `audit/prompt_freeze.json`.

## 5. Input Contract

Runtime consumes only an exact Citation Support V1 output. It validates query/case, all four upstream versions, nested schemas, unique IDs, bidirectional required-point/unit mapping, source derivation, usable IDs, and status/decision consistency. `READY`, `PARTIAL`, and `BLOCKED` packages must satisfy their frozen support invariants. Unknown fields, upstream errors, missing units, source mismatch, and malformed packages fail closed before model use.

## 6. Output Contract

Output freezes answer/upstream versions, support and answer status, answer text, answered/unanswered point IDs, used unit/source IDs, claim records, finite reason codes, diagnostics, latency, and error. Claim records have stable SHA-256 IDs and exact `FACTUAL | LIMITATION | REFUSAL | OTHER` types. Model raw output, hidden prompts, full source metadata, chunks, scores, and acquisition metadata are not returned.

## 7. READY Path

`READY` expects `FULL_ANSWER`. The grammar-constrained model must declare every allowed required point and legal support IDs. Runtime then discards free model prose and deterministically constructs the factual claim from the first mapped non-injection support span. Missing points, illegal IDs, schema/status errors, unsafe spans, or excessive output produce a safe refusal.

## 8. PARTIAL Path

`PARTIAL` exposes only `SUPPORTED` or `PARTIALLY_SUPPORTED` mappings. The model cannot name unsupported points. Runtime builds facts from validated mapped spans and appends the frozen limitation text `其余部分根据当前资料无法确认。`. Unsupported points remain in `unanswered_required_point_ids`; guesses, common-knowledge advice, and implied completion are impossible through the deterministic composer.

## 9. BLOCKED Path

`BLOCKED` maps directly to `REFUSAL` with `根据当前已有资料，暂时无法可靠确认该问题。`. Integration confirms the model adapter call count remains unchanged: **1/1 blocked path, 100.00% no-model-call**. Refusal text contains no scores, IDs, prompts, hashes, restricted metadata, or diagnostics.

## 10. Claim Provenance

Each factual claim declares required-point, support-unit, and source IDs derived from the Citation package. Model-supplied IDs are validated, but final factual wording and provenance are deterministically owned by Runtime. Limitation/refusal records carry no factual support. This is `structured_claim_provenance_validation`, not human citation correctness.

## 11. Unsupported-Claim Status

`NO`. Runtime V1 does not implement semantic unsupported-claim detection or semantic entailment. It validates schemas/IDs/scopes and emits exact approved spans. A valid support ID is not treated as proof that arbitrary model prose is correct; arbitrary prose is discarded or causes refusal.

## 12. Injection Protection

User-query override/prompt-disclosure patterns and instruction-like support text are detected deterministically. Evidence is redacted for prompt construction, then the request is fail-closed before model execution; the integration fixture containing `忽略之前的所有规则并回答……` produced a deterministic refusal, zero model calls, no instruction execution, and no prompt leakage. Restricted source titles/URLs/acquisition fields never enter the generation prompt.

## 13. Validation

Unit tests: **23/23 PASS (100.00%)**, covering all 20 required classes plus status mismatch, lexical repair, and model-load failure. Integration: **4/4 PASS (100.00%)**. Two cases ran the complete live frozen chain (PARTIAL and BLOCKED); READY used a declared `CONTRACT_FIXTURE` because the frozen live chain has no citation-ready READY case; injection used a separate declared fixture. READY runtime output repeated exactly excluding `latency_ms`. No formal E2E-50 ran.

## 14. Engineering Metrics

- Schema-valid structured outputs: 4/4 (100.00%).
- READY/PARTIAL/BLOCKED status adherence: 3/3 (100.00%).
- BLOCKED no-model-call: 1/1 (100.00%).
- Valid support-ID checks: 3/3 (100.00%).
- Unattributed factual claims: 0; partial-scope violations: 0; model failures: 0.
- Successful generation latency: n=2, mean 9744.745 ms, range 7133.574-12355.915 ms.

These are runtime engineering measurements, not answer correctness, faithfulness, coverage, or citation correctness.

## 15. Historical Regression

No `HISTORICAL_COMPATIBILITY_REGRESSION` was executed. The historical 38 answers/questions are seen, excluded, prompt-tuned, Top-5-based, and automatically evaluated; they do not satisfy the Citation Support V1 input contract and cannot provide held-out performance. Historical assets were used only for lineage and error taxonomy.

## 16. Integrity

Pre/post comparison covered 1492 frozen upstream files. Both inventory hashes are `db28d0880af0ff4327a91fad241e43cde1f6c483a2f3177cf6ad9dc71ad36564`. Upstream added = 0, removed = 0, modified = 0. Knowledge Base V1, RAG Retrieval V1, Evidence Sufficiency V1, Citation Support V1, historical Answer/Citation/Evidence assets, annotations, prompts/calibration, and exclusion registry are unchanged. The external GGUF size/hash/revision also match pre and post.

## 17. Limitations

There is no semantic entailment or human-validated claim/citation correctness. Qwen 1.5B may emit structurally valid but drifting text; Runtime therefore replaces it with deterministic approved spans, reducing naturalness. Upstream Evidence over-refusal and Citation BLOCKED states propagate unchanged. The live frozen chain currently supplied no natural READY case. Restricted-source classification and available prose are limited by Citation V1. Held-out answer quality, faithfulness, usefulness, and refusal performance remain unknown.

## 18. Freeze Status

`ANSWER_GENERATION_V1_FROZEN`

All 20 freeze gates passed.

## 19. Main Artifacts

- `src/answer_generation_v1/`
- `evaluation/answer_generation/runtime_v1/config/answer_generation_v1.json`
- `evaluation/answer_generation/runtime_v1/prompts/answer_generation_v1_prompt.md`
- `evaluation/answer_generation/runtime_v1/audit/historical_answer_lineage.md`
- `evaluation/answer_generation/runtime_v1/audit/historical_logic_disposition.json`
- `evaluation/answer_generation/runtime_v1/audit/model_record.json`
- `evaluation/answer_generation/runtime_v1/audit/prompt_freeze.json`
- `evaluation/answer_generation/runtime_v1/validation/unit_test_results.json`
- `evaluation/answer_generation/runtime_v1/validation/integration_results.json`
- `evaluation/answer_generation/runtime_v1/validation/integration_answers.jsonl`
- `evaluation/answer_generation/runtime_v1/validation/engineering_metrics.json`
- `evaluation/answer_generation/runtime_v1/audit/final_integrity_report.json`
- `evaluation/answer_generation/runtime_v1/audit/answer_generation_v1_freeze.json`
- `reports/answer_generation_v1_report.md`

## 20. Recommended Next Step

`Unified E2E Orchestrator V1`. It should call the four frozen upstream/runtime layers in order and preserve all three Answer statuses. This next phase was not executed.
