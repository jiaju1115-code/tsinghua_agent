# Submission Runtime V2 / V3 Draft

This directory records the submission-only runtime built on 2026-08-17. It does
not replace, mutate, or redefine Frozen Research Runtime V1.

## Deployed test assets

- Coze project: `TEST_SUBMISSION_V1_C` (`7674978993728126976`)
- Knowledge base: `TEST_SUBMISSION_V1_KB` (`7674979933138976768`)
- Workflow V2: `TEST_SUBMISSION_V1_WORKFLOW_V2` (`7674999313944018944`)
- Workflow V3 candidate: `TEST_SUBMISSION_V3_READY` (`7675204261298307072`)
- Preserved workflow V1: `TEST_SUBMISSION_V1_WORKFLOW` (`7674979535741255680`)

The deployed V2 graph is:

```text
Start
  -> Intent Recognition (7 explicit classes + default)
  -> Knowledge Retrieval (hybrid, Top-K 5, threshold 0.5, rewrite, rerank)
  -> Evidence-gated LLM answer
  -> End
```

All router exits currently converge on the same retrieval/generation chain.
The final prompt exempts clearly non-campus general conversation from evidence
requirements and keeps strict evidence rules for campus facts. This is a
working platform approximation, not the final desired split-branch design.

## Contents

- `workflow_design.md`: deployed graph and target architecture
- `gap_matrix.md`: coverage audit and source decisions
- `kb_expansion_manifest.jsonl`: 13 uploaded public/approved sources
- `policies/evidence_contract_v2.md`: three-state evidence contract
- `prompt/`: exact prompt versions and behavioral requirements
- `evidence_validator.py`: deterministic fail-closed reference validator
- `regression/`: 50-case V2 set, 20-case naturalness set, live results
- `retrieval_failure_taxonomy.md`: diagnostic categories
- `migration_log.md`: recorded changes and decisions
- `comparison_v1_v2.md`: measured V1/V2 capability and coverage comparison
- `kb_hotfix/`: 2026-08-18 public-source retrieval hotfixes for campus
  visits and campus-card replacement
- `network_fallback_readiness.md`: verified plugin status and the
  knowledge-first web-search fallback design

## V3 candidate

V3 is the isolated, unsubmitted candidate. It retains the seven-class router
and hybrid retrieval, but separates the evidence decision from final response:

```text
Start -> Intent Router -> Retrieval (hybrid, Top-K 3)
      -> Evidence Judge (SUFFICIENT / PARTIAL / INSUFFICIENT)
      -> Grounded Conversational Answer -> End
```

The answer node receives both the route and the judge output. It responds
directly to general chat, fails closed on current information without dated
evidence, refuses unsafe or injection requests, and tailors procedure answers
to the user's known identity instead of dumping every exception. Six live V3
checks are recorded in `regression/test_results_v3.md`.

## Important limitation

The local deterministic validator is implemented and tested, but it is not yet
instantiated as a Coze Code node. In the deployed workflow the LLM combines
evidence judging and answer generation. Source-level citations are also not
reliably exposed by the current retrieval output. V3 therefore permits only a
visible evidence link or the conservative fallback `依据：当前知识库相关片段`;
it never invents a citation. A deterministic Code-node validator and
source-level citation formatter are still not available in the deployed
candidate. The honest status is `SUBMISSION_RUNTIME_V3_SUBMISSION_CANDIDATE`
(draft-only), rather than a published or formally submitted version.

## 2026-08-18 retrieval hotfix validation

Four draft-only, public-source custom documents were added to the existing
knowledge base, including dense alias-rich variants to prevent important
facts from being split away from their synonymous user phrasing. They cover
parents/relatives visiting campus and lost-campus-card loss reporting and
replacement. The two reported failure cases now retrieve their correct entity
and return grounded answers. The live evidence is recorded in
`regression/test_results_v3.md`; this is still an unsubmitted platform draft.

## Coverage synchronization and semantic retrieval (2026-08-18)

All 30 locally approved public-source documents have now been synchronized to
the platform knowledge base. The platform API reports 54 documents in total,
with 53 usable documents and one pre-existing failed document. V3 was evolved
in place (still draft-only) to seven nodes:

```text
Start -> Intent Router -> Intent & Alias Normalizer -> Retrieval (Top-K 5)
      -> Evidence Judge -> Grounded Answer -> End
```

The normalizer preserves the original wording while expanding informal
relations into retrievable entities (for example, parents -> relatives /
visitors / admission appointment). This is deliberately separate from the
answer model, so it cannot turn an alias into a factual claim.
