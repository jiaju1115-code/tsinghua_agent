# Answer Generation Runtime V1

Public API:

```python
from src.answer_generation_v1 import generate_answer

answer = generate_answer(query, case_id, support_package)
```

The API accepts only a frozen Citation Support V1 package. It has no retrieval
result, Knowledge Base, Evidence result, network, benchmark answer, or raw Top-5
parameter.

## Paths

- `READY` -> grammar-constrained model call -> validated `FULL_ANSWER`.
- `PARTIAL` -> grammar-constrained model call over only mapped points ->
  `PARTIAL_ANSWER` plus deterministic limitation text.
- `BLOCKED` -> deterministic `REFUSAL`; the generation adapter is not loaded or
  called.

The model must return one attributed claim per allowed required point. Runtime
V1 validates point/support IDs, then constructs each factual claim from the
first deterministic mapped support span. Model paraphrase or invented text is
never copied into the final answer. Evidence/user instruction injection fails
closed before model execution. Restricted source metadata is not placed in the
model prompt or answer.

Claim records are declared provenance, not semantic entailment or human
citation correctness. Runtime diagnostics explicitly state that semantic
unsupported-claim detection is unavailable.

Configuration, model identity, decoding, prompt identity, finite reason codes,
limits, timeout, zero-retry policy, refusal text, and scope rules are frozen in
`config/answer_generation_v1.json`. Historical experimental `v0/` and `v1/`
directories are preserved unchanged; the formal runtime uses `runtime_v1/` to
avoid overwriting them.
