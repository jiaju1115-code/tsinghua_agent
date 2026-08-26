# Migration Log

## 2026-08-17 — platform selection

- Local behavior: full Python Runtime with deterministic Evidence/Citation contracts.
- Platform implementation: AgentVerse was attempted first; the browser interaction path was unreliable at that stage, so the automatic fallback rule was applied and Coze was selected.
- Difference: this is an execution-path choice, not proof that AgentVerse lacks the required capabilities.
- Risk: AgentVerse remains unqualified rather than technically disproven.

## 2026-08-17 — test resources

- Created a draft Coze project displayed as `TEST_SUBMISSION_V1_C` (20-character UI limit), a test KB, and a test workflow.
- Uploaded only a small set of public Frozen KB source files. No restricted source, held-out gold, human label, or private portal material was uploaded.
- Concurrent uploads exposed platform index-creation conflicts; later documents were added sequentially. The KB UI showed 7 document records, 11 segments, and 6.45 KB, including failed records.
- No resource was published, submitted for review, or connected to the competition submission.

## 2026-08-17 — retriever adaptation

- Local: DenseRetrieverV1, Frozen encoder/index, Top-5.
- Platform: Coze Knowledge Retrieval, hybrid, Top-K 5, threshold 0.5, query rewrite and rerank enabled.
- Difference: platform embeddings, segmentation, scores, and reranker are opaque/different.
- Risk: actual tests showed off-topic but non-empty outputs for deadline, library-hours, network-reset, and transcript queries.

## 2026-08-17 — runtime test

- Saved flow: `Start -> Knowledge Retrieval -> End`.
- Ten trial questions were run: supported, missing-attribute, out-of-scope, injection, and citation-request cases.
- Supported dorm and scholarship questions returned material. Two clearly unsupported/injection questions returned empty output.
- Empty output is fail-closed but not a user-facing refusal. Missing-attribute cases returned related text rather than `PARTIAL`. Citation requests did not produce trustworthy document-title/URL citations.

## 2026-08-17 — LLM node experiment

- A draft LLM node using the platform default `Deepseek-R1-VolcEngine` was added while testing serial insertion.
- The editor's edge deletion behavior removed the new node when replacing the pre-existing direct retrieval-to-end edge. The stable retrieval-only flow was restored.
- No successful standalone platform LLM call occurred, so the prototype must not claim one.
- Next implementation must add Evidence/Selector/Citation nodes in a fresh workflow version or rebuild the flow in final order before connecting End.
