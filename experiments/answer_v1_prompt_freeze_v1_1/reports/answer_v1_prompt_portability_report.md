# Answer Generation V1 Prompt Portability Audit

## Decision

`APPROVED` — `ANSWER_V1_PROMPT_FREEZE_V1.1` is a portability/provenance evolution of the historical raw-text freeze, not a Prompt or Answer semantic change.

## Evidence

- The runtime has one frozen prompt artifact: `evaluation/answer_generation/runtime_v1/prompts/answer_generation_v1_prompt.md`.
- Working tree: 1,679 bytes and 45 CRLF sequences; raw SHA-256 is `234be7ae54bb870399f9f8c90542b5efa76361bfe4d946c9e1a0980e3e9042bc`.
- Git HEAD blob `c76351670a680ed9ba88121d2bf466afb31098e5`: 1,634 bytes and 45 LF sequences; content SHA-256 is `93c556c994e0ebfc5ab24c1866aa97e4c3f709590aa5abab7a6cb169ea9745fb`.
- Applying only UTF-8 BOM removal, CRLF→LF, and CR→LF makes the working-tree bytes exactly equal to the Git blob and produces the approved hash.
- Prompt wording, Unicode code points, line count, literal instructions, delimiters, and template-variable inventory are unchanged. No actual template variables exist in this prompt.
- The real Answer V1 `_prompt` renderer produced equivalent model inputs for fixed READY, PARTIAL, and BLOCKED inputs when supplied Git-LF and Windows-CRLF prompt bytes.

## Contract

Prompt text uses `CANONICAL_TEXT_V1`: strict UTF-8, remove a UTF-8 BOM, CRLF→LF, CR→LF, then SHA-256. No whitespace collapsing, trimming, Unicode normalization, serialization, reordering, or content rewriting is allowed. Legacy raw hash and legacy freeze remain preserved.

## Scope boundary

The independent verifier passes for the real prompt. The existing frozen `src/answer_generation_v1` runtime still implements its historical raw-hash verifier and has no approved extension point for the V1.1 verifier. This audit does not alter, bypass, or monkey-patch that runtime; therefore the existing Runtime V1 supported-answer P0 remains until an explicitly authorized loader integration is made.
