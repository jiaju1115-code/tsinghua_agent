# Unified E2E Orchestrator V1

Formal frozen-runtime chain:

`RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> ANSWER_GENERATION_V1`

Public entry point:

```python
from src.e2e_orchestrator_v1 import run_e2e

result = run_e2e(query, case_id)
```

The runtime validates exact layer contracts and versions, invokes each layer once in order, propagates frozen statuses, constructs compact traces and existing-link provenance, and fails closed. It performs no re-retrieval, fallback, repair, retry, web search, semantic classification, or held-out evaluation.
