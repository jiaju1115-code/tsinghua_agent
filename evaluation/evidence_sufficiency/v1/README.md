# Evidence Sufficiency Runtime V1

## Purpose

This runtime consumes a completed frozen `RAG_RETRIEVAL_V1` Top-5 result and emits an auditable three-state evidence decision. It does not retrieve, generate an answer, or implement citation alignment.

## Public interface

```python
from src.evidence_sufficiency_v1 import evaluate_evidence

decision = evaluate_evidence(query, case_id, retrieval_result)
```

Required retrieval versions are `RAG_RETRIEVAL_V1` and `KNOWLEDGE_BASE_V1`; `ordered_top5_chunks` must contain exactly five schema-valid chunks in ranks 1 through 5.

## Decisions

- `SUFFICIENT` / `ALLOW_FULL_ANSWER`: every parsed minimal core point is supported and every explicitly requested attribute is present.
- `PARTIAL` / `ALLOW_PARTIAL_ANSWER`: at least one core point has usable support, but a core point or requested attribute remains incomplete.
- `INSUFFICIENT` / `REQUIRE_REFUSAL`: no core point is safely supported, input validation fails, evidence conflicts, or the result otherwise cannot safely support an answer.

Optional information is separated before core decomposition and does not lower sufficiency when absent.

## Actual method

The implementation is a deterministic lexical/structural support proxy with sentence-span provenance, entity viability checks, requested-attribute checks, and conservative conflict handling. It is not semantic entailment. `confidence` is therefore always null, and diagnostics always declare `semantic_entailment: false`.

## Frozen configuration

Thresholds and reason-code vocabulary are in `config/runtime_v1.json`. Runtime code loads no trained model and performs no network calls. Historical regression is diagnostic only and was run after the configuration was declared; it did not tune the configuration.
