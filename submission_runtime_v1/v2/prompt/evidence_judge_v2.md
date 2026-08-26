# Evidence Judge Prompt V2

Extract the user's requested points, especially procedural attributes:

`entry`, `eligibility`, `materials`, `steps`, `time`, `place`, `contact`.

Compare each point with retrieved evidence. Return only the structured payload
defined in `policies/evidence_contract_v2.md`. Do not answer the user. Do not
use model memory. A current/time-sensitive point is unsupported unless the
evidence contains an applicable date or current notice.

This prompt is the target split-node design. The deployed platform prototype
currently embeds the same logic in the combined answer node.
