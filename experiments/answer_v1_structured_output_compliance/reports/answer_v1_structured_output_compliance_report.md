# Answer V1 Structured Output Compliance Strategy Audit

## 1. Root Problem

The confirmed root problem remains `MODEL_SCHEMA_NONCOMPLIANCE` in POS002, POS006, and POS008. The original validator correctly rejects duplicate required-point claims, wrong support bindings, and missing allowed-point coverage.

## 2. Generation Backend Capability

The real backend is Qwen2.5-1.5B-Instruct-GGUF through llama.cpp Python 0.3.34 on CPU. The installed API supports JSON mode, JSON Schema via `response_format`, and native `LlamaGrammar.from_json_schema`. The current config is temperature 0, fixed seed 20260815, repeat penalty 1.05, and max 256 tokens. Native grammar is available; semantic cross-field validation remains the original validator’s responsibility.

## 3. Contract Constraint Analysis

- POS002 is partly structural: a dynamic claims array can be limited to the number of allowed points, but JSON Schema alone does not generally guarantee unique `required_point_id` coverage without dynamic positional schema. The experiment used a dynamic schema and the original validator remained authoritative.
- POS006 is semantic cross-field binding: ordinary static JSON Schema cannot know which support IDs belong to which point; the experiment generated a dynamic per-point support-ID enum, then still passed the output to the original validator.
- POS008 is coverage: the dynamic experiment fixed the allowed claims array cardinality to the number of allowed points. The original validator still checked actual point coverage.

## 4. Baseline

Baseline used the existing production generation settings and the previously captured real raw outputs. All three cases parsed as JSON but failed Answer validation: contract pass `0/3`. Baseline is already deterministic by temperature 0 and fixed seed; no additional repeated baseline calls were required for this audit.

## 5. Constrained Decoding Experiment

An independent experimental adapter generated a dynamic JSON Schema from the runtime-provided allowed-point/support inventory. It constrained output shape and per-point support-ID choices only; it did not encode answers, gold text, or bypass validation.

Result: `3/3` contract pass. POS002, POS006, and POS008 completed as `PARTIAL_ANSWER`. The original validator remained the final authority. No unsupported repair, citation synthesis, provenance synthesis, or post-parser correction occurred. Latency was 8.4s, 14.5s, and 25.9s; average 16.3s, maximum 25.9s.

## 6. Bounded Retry Experiment

The experimental retry adapter made at most one retry after a machine-readable contract violation. It supplied only the violation class, original query/support package, and the frozen prompt context; it did not provide a gold answer or correct support ID.

Result: `1/3`. POS002 passed on retry; POS006 still emitted a duplicate required point; POS008 still omitted an allowed point. Three additional model calls were used, with average latency 26.6s and maximum 30.5s. No unsupported repair was observed, but the pass rate and latency are insufficient.

## 7. Deterministic Generation Experiment

Not applicable as a separate mitigation. The current baseline already uses temperature 0 and a fixed seed. Deterministic settings explain why the same failure family is reproducible, but they do not solve it.

## 8. Strategy Comparison

| Strategy | Contract Pass | Safety | Extra Calls | Avg Latency | Recommendation |
|---|---:|---|---:|---:|---|
| Baseline | 0/3 | fail-closed | 0 | 16.8s | baseline |
| Constrained decoding | 3/3 | validator preserved | 0 | 16.3s | recommend experimental-only |
| Bounded retry | 1/3 | fail-closed but incomplete | 3 | 26.6s | do not recommend |
| Deterministic settings | N/A | already active | 0 | N/A | not applicable |

## 9. Regression Check

The original successful partial, full-answer, and refusal outcomes remain represented by POS004/POS007, POS001, and POS003 in the frozen positive validation artifacts. Targeted fail-closed tests passed (`3 passed`). No production Runtime integration or full 8-case rerun was performed; the constrained adapter remains experiment-only.

## 10. Safety Assessment

The original validator was not modified and remained the final authority for every experimental output. No claim was auto-generated, no support ID was remapped, no required point was auto-filled, no citation/provenance was synthesized, and no raw-text fallback or silent fallback was introduced. Unsupported or malformed outputs still fail closed.

## 11. Recommended Mitigation

`CONSTRAINED_DECODING` — experimental-only recommendation. It is the only tested strategy with 3/3 contract pass, zero extra model calls, no semantic repair, and preserved validator authority.

This is not a production integration approval. The dynamic schema implementation requires a separate integration review, especially for coverage guarantees and backend grammar compatibility.

## 12. Demo Impact Estimate

If separately integrated and the result reproduces, the strategy could theoretically remove the three Answer contract blockers (POS002/POS006/POS008). It does not address POS003 Evidence over-reject, DEMO002/DEMO013 Evidence mismatch, or DEMO012 Citation block. Therefore the overall Demo would still be limited by known upstream failures; no new 8-case official metric is claimed.

## 13. Frozen Integrity

KB, chunks, embeddings, Retriever, Evidence, Citation, Answer validator semantics, Prompt content, Prompt Freeze, Frozen Bundle, production Runtime, model artifact, and refusal policy were not modified. The experimental adapter was not connected to production Runtime.

## 14. Main Artifacts

- `D:\python_projects\tsinghua_ai\experiments\answer_v1_structured_output_compliance\audit\generation_backend_capability_audit.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_structured_output_compliance\audit\answer_v1_structured_output_contract_inventory.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_structured_output_compliance\data\compliance_experiment_cases.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_structured_output_compliance\results\strategy_comparison.json`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_structured_output_compliance\results\constrained_decoding_results.jsonl`
- `D:\python_projects\tsinghua_ai\experiments\answer_v1_structured_output_compliance\results\bounded_retry_results.jsonl`

## 15. Recommended Next Single Task

`Answer V1 Constrained Decoding Runtime Integration` — only as a bounded integration task with dynamic-schema coverage tests, original-validator preservation tests, and a fresh official 8-case positive validation after integration. Do not integrate bounded retry based on the current 1/3 result.
