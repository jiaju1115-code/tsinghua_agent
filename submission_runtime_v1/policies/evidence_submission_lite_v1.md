# Evidence Sufficiency Submission Lite V1

Source of truth: `src/evidence_sufficiency_v1/` and `evaluation/evidence_sufficiency/v1/config/runtime_v1.json`. This document is a platform adaptation, not a replacement.

## Inputs

- User query.
- Exactly the platform Top-5 retrieval results when available.
- Retrieved text plus platform-returned title, URL, document ID, and score metadata.

## Required-point check

1. Split the query into no more than five core requested points.
2. Detect requested attributes from: TIME, DEADLINE, LOCATION, PRICE, ELIGIBILITY, PROCEDURE, ENTRY, MATERIALS, CONTACT, OBJECT, CURRENT_STATUS.
3. For each point, require relevant supporting text and every explicitly requested attribute.
4. A related topic without the requested attribute is not full support. Example: a scholarship policy without a deadline cannot answer a deadline question.
5. Conflicting values, missing current-year support, empty retrieval, malformed metadata, or an unusable result fail closed.

## Decisions

- `SUFFICIENT`: every core point and every requested attribute is supported.
- `PARTIAL`: at least one point is supported or partially supported, but another point/attribute is missing.
- `INSUFFICIENT`: no usable relevant support, a conflict blocks a safe answer, or validation fails.

## One-way actions

- `SUFFICIENT -> ALLOW_FULL_ANSWER`
- `PARTIAL -> ALLOW_PARTIAL_ANSWER`
- `INSUFFICIENT -> REQUIRE_REFUSAL`

No downstream model may upgrade `PARTIAL` or `INSUFFICIENT` based on its own knowledge. The initial platform implementation should use a Code node for deterministic empty/result-shape checks and a constrained judge only for relevance/point mapping, followed by a Selector node.
