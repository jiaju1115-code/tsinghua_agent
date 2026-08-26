# Content Recovery Report

## Recovery Summary

- Total: **22**
- Recovered: **0**
- Partially Recovered: **0**
- Failed: **22**
- Auth Required: **0**

## International Organization Internship

- Total: **19**
- Recovered: 0
- Failed: 19
- Auth required: 0

## Recovery Methods

- LOCAL_FIELD_RECOVERY: 22
- ORIGIN_RECORD_RECOVERY: 0
- AUTHENTICATED_FETCH: 0

## Failures

- NO_BODY_IN_SOURCE: 20
- WEB_SHELL_ONLY: 2


## Integrity

- Recovery input remains **22** records with one result per queue item.
- No network fetch was attempted because no reusable authenticated storage state was available.
- Raw source was not modified.
- KB V1, Retriever V1, embeddings, Evidence, Citation, Answer Generation, E2E, and production runtime were not modified.
- Failed records were not promoted to complete candidates. `dynamic_candidates_v1_recovered.jsonl` preserves the existing 924 candidates.
