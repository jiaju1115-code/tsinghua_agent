# Runtime V1

Production-candidate chain: `Runtime V1 → Dense Retriever V1 → Evidence V1 → Citation V1 → Answer V1`.

- Active freeze: `FROZEN_BUNDLE_V1.1`
- Text hash: `CANONICAL_TEXT_V1`
- Binary hash: `RAW_BINARY`
- Not integrated: Router, Hybrid, BM25, Dynamic retrieval.

Use the user-facing entrypoint:

```powershell
python -m src.runtime_v1 "你的问题"
```

The command prints a JSON-serializable structured result. `answer_query(query)` is the matching Python API. It is a thin wrapper around the frozen V1 components and fails closed when the approved freeze reference or an artifact check fails.

Runtime V1 explicitly injects the approved `ANSWER_V1_PROMPT_FREEZE_V1.1` verifier into Answer V1. The default `generate_answer()` path still uses its historical raw verifier for replay compatibility; only Runtime V1 consumes the versioned canonical-text contract. No Prompt wording or Answer generation semantics are changed.
