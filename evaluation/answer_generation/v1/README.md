# Answer Generation Evaluation V1

Frozen paired prompt A/B experiment over the same 38 questions and the same RAG V1 Dense Top-5 evidence. Group A reproduces the V0 generation prompt. Group B changes only the answer-generation prompt. Model, model revision, decoding configuration, retrieval inputs, and evaluation pipeline are shared.

All semantic metrics are `PROVISIONAL_AUTO_EVAL` until the blank human-review fields are completed.

## Reproduce

1. `python scripts/freeze_inputs.py`
2. `python scripts/run_ab_generation.py`
3. `python scripts/run_ab_evaluation.py`
4. If only deterministic rule logic changes, recompute from stored evaluator JSON with `python scripts/recompute_deterministic_evaluation.py`.
5. `python scripts/build_analysis.py`
6. Build and verify the workbook with the bundled Node.js runtime: `node scripts/build_workbook.mjs`.
7. `python scripts/finalize_audit.py`

Generation and evaluation JSONL files append one completed question at a time. No external model API is used.
