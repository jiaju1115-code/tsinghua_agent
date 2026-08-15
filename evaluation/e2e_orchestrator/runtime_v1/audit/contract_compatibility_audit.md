# Unified E2E Orchestrator V1 Contract Compatibility Audit

## Scope

This audit covers only the four formal frozen public interfaces. It does not reinterpret business decisions, change any upstream schema, or execute held-out E2E evaluation.

## Contract map

| Boundary | Producer | Consumer | Classification | Evidence |
|---|---|---|---|---|
| Query to retrieval | `DenseRetrieverV1.retrieve(query, case_id)` | Evidence input | Direct | Retriever emits the frozen query/case/version/corpus/Top-5 contract consumed by Evidence. |
| Retrieval to Evidence | `RAG_RETRIEVAL_V1` | `evaluate_evidence` | Direct | Exact version, corpus, five ranks, chunk/source IDs and text align. |
| Evidence to Citation | `EVIDENCE_SUFFICIENCY_V1` | `build_support_package` | Direct | Citation imports and validates the full Evidence V1 field set and policy signal. |
| Citation to Answer | `CITATION_SUPPORT_V1` | `generate_answer` | Direct | Answer validates the formal support package and consumes no Retriever Top-5 directly. |
| Answer to unified output | `ANSWER_GENERATION_V1` | Orchestrator output | Mechanical adapter | Field names are compactly projected (`answer_text` to `final_answer`) without semantic transformation. |
| Existing provenance to unified provenance | Answer claims + Citation mappings/units + Retriever rows | Orchestrator provenance | Mechanical adapter | Only existing IDs are joined; no new support is inferred. Missing links fail with `PROVENANCE_LINK_UNAVAILABLE`. |

## Status compatibility

Nominal mappings are `READY -> FULL_ANSWER`, `PARTIAL -> PARTIAL_ANSWER`, and `BLOCKED -> REFUSAL`. The frozen Answer injection guard may safely turn READY/PARTIAL into REFUSAL without a model call; this is preserved and explicitly marked, not treated as a new fallback. All other status conflicts fail closed.

## Semantic conflicts

No unresolved semantic conflict was found. Citation may legitimately reduce an Evidence result to `BLOCKED` when span/provenance integrity fails; this is the already-frozen Citation responsibility, not an adapter conflict. No upstream field or policy requires modification.

## Prohibited behavior audit

The orchestrator adds no retries, re-retrieval, fallback retrieval, repair, external search, model-based router, semantic classifier, prompt modification, unsupported-claim model, or hidden answer path.
