# Retrieval Failure Taxonomy

| Code | Diagnostic question | Typical remediation |
|---|---|---|
| COVERAGE_MISSING | Is there any approved source for the requested fact? | Add an approved public source; do not tune prompt first |
| WRONG_ENTITY | Did scholarship retrieve grant/loan, or vice versa? | Entity-aware query rewrite and negative tests |
| WRONG_DOCUMENT_TYPE | Did an organization intro answer a procedure/current-hours query? | Add procedure/current document and type-aware rerank |
| REQUESTED_ATTRIBUTE_MISSING | Does evidence omit entry, material, step, time, place, or contact requested? | Return PARTIAL and identify missing points |
| RETRIEVAL_MISS | Is the correct indexed source absent from Top-K? | Compare Top-K/threshold and chunk boundaries |
| QUERY_REWRITE_FAILURE | Did rewrite remove a critical entity or time qualifier? | Preserve named entity and temporal terms |
| RERANK_FAILURE | Was the correct candidate recalled but ranked below a wrong-topic result? | Add document type/entity features or disable rerank for a test |
| EVIDENCE_JUDGE_FAILURE | Did the judge mark incomplete/old evidence sufficient? | Strengthen requested-point and freshness checks |
| ANSWER_FAILURE | Was evidence sufficient but the final response wrong, incomplete, or mechanical? | Fix answer prompt/output mapping |
| CITATION_FAILURE | Is the citation missing, fabricated, or not among selected evidence? | Deterministic formatter from selected evidence IDs only |

Every regression failure must receive one primary code and may receive
secondary codes. Prompt changes are appropriate only for judge/answer failures,
not for missing coverage.
