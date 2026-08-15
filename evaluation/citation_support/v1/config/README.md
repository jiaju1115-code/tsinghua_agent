# Citation / Support Runtime V1 configuration

This directory defines the frozen deterministic policy for `CITATION_SUPPORT_V1`.
The runtime consumes already-produced Retriever V1 and Evidence Sufficiency V1
objects. It performs no retrieval, generation, entailment, or web access.

The source metadata allowlist is a security boundary. Restricted classification
is derived only from the frozen canonical source-ID prefix; acquisition, cookie,
authentication, and internal provenance metadata are never propagated.
