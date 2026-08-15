# Academic Retrieval V0.1 report

## Scope and integrity

V0 was read only. This V0.1 follow-up is isolated in this directory and never changes V0, RAG, Citation, prompts, Human Audit, production, or model weights.

## Router and planner

Router V0.1 combines discipline dictionaries, academic task words, mathematical/LaTex structure, campus signals, current-information signals and explainable scores. Strong academic evidence outranks a year/freshness token. The planner emits a subject, topic, problem type, knowledge needs, atomized requirements and at most two bilingual knowledge queries; submitted problems are not used as default Tavily search queries.

## Results

Frozen Academic 10 improved from 50% to 100% Router Accuracy and from 50% to 100% Knowledge Sufficiency. All 30 frozen routes are correct. Direct-answer leakage fell from 10% to 0% in the frozen academic run.

The independent 24-question Shadow Set achieved 66.67% Router Accuracy. All 24 could produce a sufficient package when forced through the Academic Retriever, but only 16/24 are sufficient end-to-end because eight were routed to General Web. This is reported as a limitation, not counted as a validation success. A subsequent generic compliance fix for the stage-specified “academic problem + year” priority was made without using any Shadow item; therefore the Shadow result is explicitly pre-change provisional, not a post-change validation claim.

The bilingual primary queries produced usable evidence for every final Frozen and Shadow academic package. Attribution of marginal evidence to Chinese versus English alone is N/A because both queries were planned/executed together and the current records do not establish a causal per-language counterfactual.

Stage 2 gap search triggered for one Frozen and one Shadow final package. Final-run API counters: 21 new Search requests, 36 new Extract requests and 49 cache hits. Including the preserved initial dry-run instrumentation, the V0.1 working history consumed 39 new Search and 46 new Extract requests.

## Recommendation

Do not enter Integration V0 yet. The minimum next repair is to expand Router V0.1’s general academic task and discipline signals for the eight Shadow routing-failure concepts, then evaluate on a new untouched shadow set. Do not run V0.2 automatically.
