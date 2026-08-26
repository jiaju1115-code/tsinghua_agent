# Final Submission Integration Gate V1

## Decision

**SUBMISSION_READY**

## Frozen integrity reconciliation

**PASS_WITH_RECONCILIATION.** The apparent raw SHA256 mismatches were caused by CRLF checkout representation under `core.autocrlf=true`. Canonical LF hashes match the original frozen hashes and Git blob `75a6b89`; the embedding index raw hash matches. See `reports/frozen_integrity_reconciliation_v1.md`. No frozen artifact was changed, rewritten, or replaced.

## Non-blocking checks

- Natural Uncertainty regression: 30/30.
- Natural Runtime Adapter smoke: 6/6.
- Runtime / Answer / Prompt tests: 27 passed (two unknown-mark warnings).
- Pilot V1 adapter is readable, has `adapter_merged=false`, and records `PILOT_V1_GENERAL_REPLAY_FROZEN`.
- The local Hugging Face cache has no Qwen Base snapshot, so Base + LoRA loading was not attempted and no download was performed.
- `legacy_data_second` remains not completed because the local model runtime stalls.

## Known limitations

Pilot V1 remains a validated research candidate and is not in the submission runtime. Formal held-out E2E and `legacy_data_second` are not complete; neither is represented as a passing result. The stable submission strategy remains Frozen RAG Runtime V1 plus Natural Uncertainty Runtime Adapter V1.
