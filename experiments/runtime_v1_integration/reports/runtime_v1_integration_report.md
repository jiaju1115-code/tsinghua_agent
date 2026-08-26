# Runtime V1 Integration Report

## Status

`RUNTIME_INTEGRATION_BLOCKED` — the Runtime V1 entrypoint and Frozen Bundle V1.1 loader work, but the first supported-answer path correctly fails closed at the frozen Answer V1 prompt raw-hash check.

## Implemented entrypoints

- Python: `src.runtime_v1.answer_query(query)` or `RuntimeV1().answer_query(query)`
- CLI: `python -m src.runtime_v1 "query"`

## Verified chain

`User Query → Runtime V1 → DenseRetrieverV1 portability adapter → Evidence V1 → Citation V1 → Answer V1 → structured result`

Router, Hybrid, BM25, and Dynamic retrieval are not integrated.

## V1.1 freeze integration

- Active freeze: `FROZEN_BUNDLE_V1.1`
- Text mode: `CANONICAL_TEXT_V1`
- Binary mode: `RAW_BINARY`
- Windows CRLF text check: pass for the approved Dense V1 portability adapter.
- Text and binary mutation detection: covered by `tests/runtime_v1/test_freeze_loader_v1_1.py`.

## Actual bounded test results

- Loader checks: active-reference/mode verification, LF/CRLF equivalence, text mutation, binary mutation.
- Runtime blocked/refusal smoke: two held-out historical cases passed stable-field equivalence; see `results/runtime_v1_smoke_equivalence.json`.
- Supported-answer probe: retrieval, Evidence, and Citation succeeded to `PARTIAL`; Answer V1 failed closed because the frozen prompt raw hash differed. See `results/runtime_v1_ready_path_probe.json`.

## P0 blocker

`src/answer_generation_v1/runtime.py` verifies the frozen prompt using raw SHA-256. The present Windows working-tree prompt's canonical `CANONICAL_TEXT_V1` hash equals its approved hash, while its raw hash differs due to line endings. Resolving this requires an explicitly approved Answer/Prompt freeze portability contract evolution; this integration did not modify or bypass it.

## Frozen integrity

KB, chunks, embeddings, Dense Retriever V1, Evidence V1, Citation V1, Answer V1, Prompt, Frozen Bundle V1, and Frozen Bundle V1.1 semantic content were not modified by this task.
