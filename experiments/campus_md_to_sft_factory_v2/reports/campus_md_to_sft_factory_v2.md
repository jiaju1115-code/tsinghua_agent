# Campus MD to SFT factory v2

## Outcome

`CAMPUS_CODEX_SFT_FACTORY_COMPLETE`

119 public eligible documents were processed in batches with checkpointing. The source funnel observed 122 manifest rows, excluded non-public/restricted and low-value/missing sources, and selected 119 usable public MD.

Final retained candidates: 229 SUPPORTED. PARTIAL, PARAPHRASE, GROUNDED_ANSWER and NEGATIVE_PROPOSAL remain empty because this run does not synthesize unsupported or partial claims. Four documents produced `NO_TRAINING_SAMPLE`.

Evidence spans passed exact source containment validation; JSON/schema validation passed for all 229 retained rows; duplicate count is 0 after candidate-ID deduplication; held-out leakage is 0. Codex runtime accounting is `CODEX_USAGE_NOT_AVAILABLE`.

Production integrity: KB / Retriever / Evidence / Citation / Answer / Router / frozen evaluation / PARTIAL Gold Policy / historical experiments unchanged. Final split: NO. Training: NO.
