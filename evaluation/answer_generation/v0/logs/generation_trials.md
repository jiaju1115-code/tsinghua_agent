# Generation interface trials

These trials tested only the local prompt/output interface before the frozen 38-query run. No trial output entered metrics.

1. **JSON-schema answer envelope** — rejected. The 1.5B model frequently exhausted the token budget before closing valid JSON.
2. **Plain text, smaller prompt batch** — technically valid but slower and still failed citation compliance.
3. **Frozen baseline** — plain text answer, full Dense Top-5 context, deterministic decoding, explicit `[C#]` constraint, `n_batch=2048`. All 38 outputs were kept exactly as generated.

The final run was not selectively regenerated after observing bad answers. Missing citations, overconfident completions, and correct refusals are all preserved.
