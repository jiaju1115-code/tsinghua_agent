# Answer Generation Evaluation V0

This directory contains an isolated, provisional answer-generation evaluation built on the frozen RAG V1 Dense Top-5 retrieval results. It does not modify RAG V0, RAG V1, Prompt V3.2, Human Audit, production, or source corpora.

## Reproduce

Run from the project workspace with Python and the vendored CPU runtime:

1. `python scripts/freeze_inputs.py`
2. Set `PYTHONPATH` to `answer_eval_v0/vendor`, then run `python scripts/run_generation.py`.
3. Run `python scripts/run_evaluator.py`.
4. Run `python scripts/build_reports.py`.
5. Run `scripts/build_workbooks.mjs` with the bundled Node.js and `@oai/artifact-tool` runtime.
6. Run `python scripts/finalize_audit.py` after all outputs are complete.

`run_generation.py` and `run_evaluator.py` append one JSONL row at a time and can resume from completed question IDs. The frozen baseline uses local `Qwen/Qwen2.5-1.5B-Instruct-GGUF` Q4_K_M on CPU; no external model API is called.

## Scope

- 38 questions: 10 `CONFIRMED` existing smoke queries and 28 `PROVISIONAL_EVAL` queries.
- Frozen `BAAI/bge-small-zh-v1.5` Dense Top-5 evidence from RAG V1.
- All semantic auto-scores are `PROVISIONAL_AUTO_EVAL`; the generator and evaluator share the same small local model, so human review remains required.
