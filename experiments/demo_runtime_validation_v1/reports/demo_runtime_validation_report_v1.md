# Demo-facing Runtime Validation V1

## 1. Demo Readiness

`DEMO_READY_WITH_LIMITATIONS`

The 15-question bounded validation completed the full Runtime V1 chain for every case. The interface is suitable for a controlled demonstration, with three known behavior-coverage limitations recorded below. No infrastructure blocker or unsafe answer was observed.

## 2. Validation Set

- Total: 15
- PARTIAL-oriented: 6
- Information-insufficient: 7
- Out-of-scope/OOD: 2
- Categories: campus affairs, natural-language rewrites, insufficient information, out-of-scope requests
- Source: current Core KB coverage, held-out campus scenarios, and natural rewrites; no gold answers injected into Runtime.

## 3. Runtime Results

- Runtime completion rate: `1.0`
- Expected behavior match: `0.8`
- Refusals: `12/15`
- Citation presence among answered cases: `1.0`
- Total latency: min `17.643 ms`, median `24.711 ms`, max `15927.731 ms`
- No `RUNTIME_ERROR` cases

## 4. Demo Quality Review

- Readability: answers are short and the wrapper hides raw diagnostics by default.
- Citations: source title and URL are shown only when Citation V1 provides usable source IDs.
- Refusals: rendered as a clear “当前资料不足” message; no traceback is exposed.
- Partial answers: preserve the Runtime answer and show the existing limitation text.
- Main limitation: local model generation can reach roughly 16 seconds on the slowest case.

## 5. Failure Inventory

Three `EXPECTED_BEHAVIOR_MISMATCH` cases were recorded, all safe fail-closed behaviors:

- `DEMO002`: scholarship basic-condition rewrite was classified `INSUFFICIENT` and refused.
- `DEMO012`: evidence was `SUFFICIENT`, but Citation V1 returned `BLOCKED`, so Answer correctly refused.
- `DEMO013`: scholarship award follow-up rewrite was classified `INSUFFICIENT` and refused.

These are validation findings only. This task does not retune Retriever, Evidence, Citation, Answer, thresholds, or Prompt.

## 6. Minimal Demo Interface

Selected: **Enhanced CLI**.

```powershell
python -m src.runtime_v1.demo_cli --query "清华大学在奖学金评选当年如何表彰获奖者？"
```

Interactive mode:

```powershell
python -m src.runtime_v1.demo_cli
```

The wrapper calls only `answer_query`, formats answer/status/citations/latency, and does not modify Runtime decisions or answer text.

## 7. Runtime/UI Separation

- UI changes: line breaks, labels, source presentation, and diagnostic visibility only.
- Answer text: unchanged.
- Runtime decisions: unchanged.
- Evidence/Citation thresholds: unchanged.
- Router, Hybrid, BM25, and Dynamic Retrieval: not integrated.

## 8. Frozen Integrity

KB, chunks, embeddings, Retriever, Evidence, Citation, Answer semantics, Prompt, Frozen Bundle V1.1, and Prompt Freeze V1.1 were not modified by Demo validation.
