# Failure cases

Record all observed failures with one of: `SEARCH_NO_RESULT`, `LOW_AUTHORITY_RESULT`, `EXTRACTION_FAILURE`, `IRRELEVANT_RESULT`, `OUTDATED_RESULT`, `SOURCE_CONFLICT`, `DIRECT_ANSWER_LEAK`, `ROUTER_ERROR`, `QUERY_REWRITE_ERROR`, `DOMAIN_POLICY_ERROR`, `API_ERROR`, `RATE_LIMIT`, `TIMEOUT`.

## Historical smoke failure

- `SEARCH_NO_RESULT` — the first General smoke query (`2026年人工智能领域近期公开进展`) returned no Tavily search result. It was retained as a failure fact. A replacement General smoke query about current OpenAI official product announcements then completed Search and Extract successfully.

## Formal evaluation

All 30 frozen questions returned at least one usable source. No formal-query failure taxonomy entry was produced; this does not erase the historical smoke failure above.
