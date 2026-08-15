# Citation historical lineage -> Citation Support Runtime V1

This audit cross-checks historical code, configs, result artifacts, workbooks, reports, and exclusion records. It does not treat report prose as sufficient evidence.

| Asset | Actual input and implementation | Label / metric status | Runtime disposition |
|---|---|---|---|
| Generation & Citation Evaluation V0 | Offline diagnosis over 38 frozen Answer V0 records plus 12 saved E2E records. Deterministic claim and completeness proxies; 143 claim rows and 17 review-queue cases. | Proxy claim support and citation-gap labels. The adjudicated workbook contains secondary AI adjudication, not human claim-to-citation gold. | Source/citation ID validity concepts: `REUSE_WITH_ADAPTATION`. Unsupported-claim detection and answer scoring: `REJECT_FOR_RUNTIME`. Metrics: `EVALUATION_ONLY`. |
| Citation Pipeline V1 | Post-generation pipeline over 38 frozen A answers. Deterministic claim segmentation, BGE claim embeddings, Dense Top-5-only matching, lexical/numeric/entity/procedure rules, citation assignment, and marker rendering. | 104 factual claims, 12 assignments, 11.54% auto coverage, 100% precision proxy. Human-validated correctness is null and workbook human fields are blank. | Top-5 containment and deterministic provenance: `REUSE_WITH_ADAPTATION`. Embedding thresholds, claim classification, rendering, and precision proxy: `REJECT_FOR_RUNTIME`. Results: `EVALUATION_ONLY`. |
| Citation Pipeline V2 | Reuses the same 38 frozen answers/claims. Extracts 6,405 spans, embeds claims/spans, applies lexical safety rules and a BGE reranker relevance gate, then renders markers. | V2-C auto labels: 37 supported, 17 partial, 50 unsupported of 104 factual claims. Human-validated precision is null. All 36 human calibration fields are blank. The reranker has 20/20 hard-negative false-positive anchors at threshold 0.95 and is explicitly not entailment. | Sentence-boundary extraction and normalization concepts: `REUSE_WITH_ADAPTATION`. BGE/reranker scores, thresholds, automatic support labels, and answer rendering: `REJECT_FOR_RUNTIME`. Metrics: `EVALUATION_ONLY`. |
| Secondary AI adjudication packet | Seventeen selected generation cases reviewed in a workbook by `GPT-5.6 Sol Secondary AI Adjudication`; includes evidence reassessment and answer/citation comments. | Useful qualitative diagnosis, but neither human adjudication nor independent claim-to-citation correctness labels. | `EVALUATION_ONLY`; never used as Runtime V1 truth or tuning data. |
| Citation Support Runtime V1 | Pre-answer consumer of frozen Retriever V1 Top-5 plus Evidence V1 provenance. Validates, normalizes, deduplicates, aggregates, and maps support units. | Engineering validation only. No answer claims and no final-answer citation correctness. | New deterministic fail-closed runtime. |

## Historical dependency and correctness findings

- Historical Citation V1/V2 require an already generated answer and therefore solve a different, post-generation problem.
- Neither V1 nor V2 contains completed human citation labels. V2 calibration has 36 rows with blank `human_support_label`, `human_citation_correct`, and `human_comment` fields.
- Historical `citation_precision_proxy = 1.0` only means assignments passed their own automatic rules. It is not citation accuracy.
- V2's cross-encoder is a relevance model, not entailment. Its sanity result is `VERIFIER_NOT_RELIABLE_AS_ENTAILMENT`.
- Historical unsupported-claim and faithfulness labels depend on answer claims. They cannot exist in this pre-answer runtime.
- Citation V1 and V2 each reuse the same 38 query family and all 38 normalized queries are in the exclusion registry. They are not held-out evidence.

## Production boundary

Runtime V1 may reuse only deterministic containment, validation, normalization, deduplication, source aggregation, and stable ordering principles. It must not load historical claim embeddings or verifier weights; reuse tuned thresholds; inspect a generated answer; extract claims; score faithfulness; render `[n]` markers; or report historical proxy metrics as correctness.
