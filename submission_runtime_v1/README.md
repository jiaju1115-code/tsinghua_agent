# Submission Runtime V1

This directory is an isolated migration layer for the Xiaoda-hosted submission prototype. It does not replace or modify the Frozen Research Runtime.

## Current platform prototype

- Platform: Xiaoda-hosted Coze open-source edition.
- Draft project: `TEST_SUBMISSION_V1_C` (the UI truncated the requested test name to its 20-character limit), project ID `7674978993728126976`.
- Test knowledge base: `TEST_SUBMISSION_V1_KB`, ID `7674979933138976768`.
- Test workflow: `TEST_SUBMISSION_V1_WORKFLOW`, ID `7674979535741255680`.
- Actual saved flow: `Start.input -> Knowledge Retrieval -> End.output`.
- Retrieval adaptation: hybrid search, Top-K 5, threshold 0.5, query rewrite enabled, rerank enabled.
- Lifecycle: draft/test only. Nothing was published, submitted, or sent for review.

The prototype proves hosted execution and retrieval against a small public-only subset. It does **not** yet implement the Research Runtime's Evidence, Citation, and Answer contracts. In particular, an empty retrieval result is currently returned as an empty string rather than a natural refusal, and some weakly related retrievals are returned without a relevance gate.

## Frozen dependencies (references only)

- Corpus: `data/03_knowledge_base/v1/`
- Corpus freeze: `data/03_knowledge_base/v1/audit/knowledge_base_v1_freeze.json`
- Retriever freeze: `data/03_knowledge_base/v1/audit/rag_retrieval_v1_freeze.json`
- Evidence: `src/evidence_sufficiency_v1/`
- Citation: `src/citation_support_v1/`
- Answer: `src/answer_generation_v1/`
- Orchestration: `src/e2e_orchestrator_v1/`
- Natural uncertainty: `src/natural_uncertainty_response_v1/`

No Frozen data, index, encoder configuration, source, held-out gold, or human label is copied into this directory.

## Intended next flow

`Start -> Knowledge Retrieval -> Evidence Judge -> Selector(SUFFICIENT/PARTIAL/INSUFFICIENT) -> bounded Answer/Citation Formatter -> End`

The prompt and policy files here are platform-adaptation specifications, not claims that those nodes have already been deployed.
