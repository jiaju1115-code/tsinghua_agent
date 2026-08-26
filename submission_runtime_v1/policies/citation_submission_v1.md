# Citation Submission Policy V1

Source of truth: `src/citation_support_v1/`. The immutable principle is: **no real retrieved source, no citation**.

1. Build citations only from metadata returned by the current retrieval execution.
2. Preserve the platform document identifier and, when available, exact title and exact URL.
3. Never let the model synthesize a title or URL. Never convert a URL mentioned only in prose into document provenance.
4. Every factual answer claim must map to at least one retrieved support item used for that claim.
5. `SUFFICIENT` requires every answered required point to be mapped. An unmapped point blocks the full answer.
6. `PARTIAL` may cite only mapped supported points and must identify unsupported points without citations.
7. `INSUFFICIENT`, empty retrieval, metadata mismatch, missing mapping, or restricted-source exposure risk produces no citation and routes to refusal.
8. Restricted sources must never expose title, URL, chunk text, or internal identifiers to end users. The current prototype contains public sources only.

Preferred rendering:

```text
参考来源：
[1] <exact retrieved title> — <exact retrieved URL, only if returned>
```
