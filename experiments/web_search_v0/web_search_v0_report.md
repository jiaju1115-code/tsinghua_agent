# Web Search V0 report

## Status

Implementation is complete and isolated. The first execution was safely blocked because `TAVILY_API_KEY` was absent. After the user configured the local `.env`, the key was read without logging it and Tavily Search/Extract completed real calls.

## Architecture

`Query → Router V0 → mode policy → academic rewrite (when applicable) → Tavily Search → ranking → Tavily Extract → quality gate → compact evidence spans`.

## Security and scope

The key is read only from `TAVILY_API_KEY` / local `.env`, is excluded from Git, and is redacted from errors. The module uses public web only; no portal login, account automation, answer-generation integration, RAG ingestion, model training, or protected-path mutation occurs.

## Live evaluation

Three-mode smoke validation passed after the General smoke query was replaced with a stable current public-information query; the first General query's `SEARCH_NO_RESULT` remains recorded in `analysis/failure_cases.md`. The frozen 30-question set then completed in full.

| Metric | Result |
|---|---:|
| Router accuracy proxy | 83.33% |
| Search success rate | 100.00% |
| Extraction success rate | 96.67% |
| Campus official source rate | 100.00% |
| High-authority source rate | 52.87% |
| Academic knowledge sufficiency proxy | 50.00% |
| Direct-answer leakage rate | 10.00% |
| Average Search latency | 5.355 s |
| Average Extract latency | 3.749 s |
| Average total retrieval latency | 8.756 s |
| Formal API requests | 59 |

The transport source gap was resolved by public official Tsinghua sources; details are in `analysis/traffic_source_gap_diagnostic.md`.

## Evaluation and recommendation

The independent workbook contains 30 questions: 10 campus, 10 academic, and 10 general web. The current Router V0 misses five academic prompts and the Academic Knowledge Sufficiency Proxy is only 50%; therefore Web Search V1 is not yet recommended. Integration V0 should remain a separate decision after Router V1 and academic quality improvements are audited.
