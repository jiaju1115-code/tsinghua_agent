# Dynamic Campus Candidate V1 Report

- Input SHA256: `f2d26bb0fed32d851fd510a4483beef041fac634870c824527f31be841adde92`
- Total records: **946** (declared `946`; list `946`)
- Candidate records: **924**
- Recovery queue: **22**
- Deterministic exclusions: **0**

## Distributions

### Category
- 科研通知: 371 (40.2%)
- 办公通知: 193 (20.9%)
- 综合信息: 162 (17.5%)
- 学生社区通知: 84 (9.1%)
- 图书馆信息: 66 (7.1%)
- 教务通知: 32 (3.5%)
- 其他: 16 (1.7%)

### Content status
- FULL_CONTENT: 923
- PARTIAL_CONTENT: 1

### Stable/dynamic
- DYNAMIC: 799
- UNKNOWN: 103
- STABLE: 22

### Current status
- UNKNOWN: 924


## Quality notes

- International-organization internship records in recovery queue: 19.
- Dates are extracted only when explicitly present; unresolved temporal fields remain `UNKNOWN`.
- Duplicate groups and field-level duplicates are preserved in `audit/duplicate_groups.json`; no records were deleted.
- No approve/reject or external-model classification was performed.

## Frozen integrity

This run did not modify KB V1, Retriever V1, embeddings, Dense/Hybrid Retriever, Evidence Sufficiency, Citation Support, Answer Generation, E2E evaluation, Prompt V3.2, or production runtime.
