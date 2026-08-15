# Historical Answer Generation Lineage -> Answer Generation Runtime V1

This audit cross-checks source code, configuration, prompts, generated outputs,
reports, workbooks, model files, runtime metadata, and the exclusion registry.
Historical report prose and automatic evaluator labels are not treated as truth.

## Answer Generation V0

- Generator: `Qwen/Qwen2.5-1.5B-Instruct-GGUF`, Hugging Face snapshot
  `91cad51170dc346986eccefdc2dd33a9da36ead9`, file
  `qwen2.5-1.5b-instruct-q4_k_m.gguf`, Q4_K_M.
- Local artifact: present outside the repository under the Hugging Face cache,
  1,117,320,736 bytes, SHA-256
  `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- GGUF metadata: `qwen2.5-1.5b-instruct`, architecture `qwen2`, file type 15,
  quantization version 2, trained context 32768, embedded GPT-2 tokenizer and
  embedded Qwen chat template.
- Engine: repository-vendored `llama-cpp-python 0.3.34`, CPU. Historical
  context 6144, maximum 128 new tokens, temperature 0, seed 20260813,
  repeat penalty 1.05, 12 generation threads, 16 batch threads.
- Input: the complete historical Dense Retriever Top-5, not Evidence V1 or
  Citation Support V1. It therefore bypasses both current gates.
- Prompt: plain-text answer plus `[C1]`-`[C5]` markers. An attempted JSON
  envelope was abandoned after frequent unclosed output at the token limit.
- Refusal: model-generated phrase detection; no upstream three-state policy.
- Evaluation: same small model plus deterministic citation/source proxies.
  Human correctness, faithfulness, hallucination, error type, and comment
  fields are blank in the 38-row workbook.

## Historical Prompt A/B V1

The A/B experiment reused the exact 38 questions, full Dense Top-5, model,
engine, decoding, and provisional same-model evaluator. Prompt A reproduced V0
38/38. Prompt B strengthened prose constraints but produced zero citation
compliance, no correct refusals, and more provisional hallucination signals.
The experiment explicitly did not recommend Prompt B. Neither prompt consumes
the current Citation Support contract.

## Generation and Citation Evaluation V0

This diagnostic joined 38 Answer V0 rows and 12 saved E2E rows. Its unsupported
claim, task-completion, refusal, and citation labels are deterministic or
secondary-AI proxies, not independently human-adjudicated semantic labels.
The 38 Answer V0 normalized queries are all present in the exclusion registry.
They are `SEEN_HISTORICAL`, not held-out Answer performance.

## Correctness, faithfulness, and leakage findings

- Historical reported correctness, faithfulness, unsupported-claim, and
  citation numbers are provisional same-model/lexical proxies.
- The Answer V0 workbook contains five human-review columns; all are blank.
- A model declaring `[C#]` never established citation correctness.
- Historical claim segmentation was evaluator-oriented, inconsistent with the
  new structured required-point contract, and not suitable as a runtime truth
  mechanism.
- All 38 Answer V0 queries are explicitly excluded from future held-out use.
- Historical answers and evidence were used for prompt/citation calibration and
  cannot be used to tune or score Runtime V1.

## Runtime inheritance boundary

Runtime V1 may reuse the verified local model artifact, vendored engine,
greedy/seeded decoding, bounded output, conservative refusal wording, and the
principle that evidence is untrusted data. It must adapt them to accept only a
Citation Support V1 package and to emit structured claim provenance.

Runtime V1 rejects direct Top-5 input, historical `[C#]` rendering, free-form
plain-text acceptance, same-model correctness scoring, historical automatic
claim labels, Prompt B, unrestricted paraphrase, benchmark-answer access, and
any claim of semantic unsupported-claim detection.
