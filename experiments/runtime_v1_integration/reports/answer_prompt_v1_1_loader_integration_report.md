# Answer V1 Prompt Freeze V1.1 Loader Integration

## Integration method

`src.answer_generation_v1.runtime.generate_answer()` now has an optional keyword-only `prompt_verifier` dependency. When omitted, its historical raw SHA-256 verifier is unchanged. Runtime V1 alone supplies `verify_answer_prompt_freeze_v1_1`, which is fail-closed and validates the approved Prompt Freeze V1.1 manifest.

This is verifier-source wiring only: Prompt loading, prompt text, model invocation, generation policy, refusal policy, citation/evidence behavior, output schema, and post-processing remain unchanged.

## Actual bounded validation

- READY-oriented and PARTIAL queries both completed Retriever → Evidence PARTIAL → Citation PARTIAL → Answer `PARTIAL_ANSWER`; the Answer model was called and no prompt hash error occurred.
- A historical insufficient-evidence query completed as `REFUSAL`, with no model call.
- A real CLI invocation completed and returned a structured Runtime V1 result with the Prompt Freeze V1.1 diagnostics.
- The legacy default verifier still returns its original raw-hash mismatch on this Windows working tree, while the explicit V1.1 verifier returns the same rendered prompt messages successfully.

## Compatibility

Historical callers that omit `prompt_verifier` retain the raw verifier. Runtime V1 diagnostics record `ANSWER_V1_PROMPT_FREEZE_V1.1` and `CANONICAL_TEXT_V1` through `answer_prompt_freeze`.
