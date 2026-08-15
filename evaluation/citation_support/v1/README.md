# Citation / Support Runtime V1

Public API:

```python
from src.citation_support_v1 import build_support_package

package = build_support_package(query, case_id, retrieval_result, evidence_result)
```

The runtime is a deterministic, fail-closed consumer of completed
`RAG_RETRIEVAL_V1` and `EVIDENCE_SUFFICIENCY_V1` outputs. It validates exact
Top-5 provenance, maps normalized Evidence spans back to raw chunk offsets,
deduplicates and safely merges support, aggregates chunks by canonical source,
and produces required-point mappings and machine-readable candidates.

It performs no retrieval, KB search, network access, Evidence evaluation,
answer generation, claim extraction, semantic entailment, citation correctness
scoring, or citation rendering.

## Status meanings

- `READY`: Evidence is `SUFFICIENT` and every required point has validated support.
- `PARTIAL`: Evidence is `PARTIAL` and at least one validated supported piece remains.
- `BLOCKED`: Evidence is `INSUFFICIENT` or any required integrity condition fails.

Restricted sources are identified only by their frozen canonical source-ID prefix.
Only allowlisted source provenance is emitted; acquisition and authentication
metadata are never copied.

Configuration is under `config/`, validation artifacts under `validation/`, and
lineage/integrity/freeze artifacts under `audit/`.
