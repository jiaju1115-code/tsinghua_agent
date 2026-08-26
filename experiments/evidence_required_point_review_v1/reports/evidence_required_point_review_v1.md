# Evidence Required-Point Mismatch Targeted Review V1

## 1. Executive Conclusion

The dominant Evidence issue is `LEXICAL_MATCH_OVERSTRICT`, not Retriever miss. DEMO002 and POS003 are the same high-confidence entity-gate subfamily; DEMO013 is a related but distinct lexical-score subcase. Retriever returned relevant frozen-KB chunks for all three. A safe unified production fix was not identified in this diagnosis-only pass.

## 2. Case Root Causes

### DEMO002

- Retrieval: `RETRIEVAL_OK`; source `KBV1-PUB-PUBV2C-0075` appears in ranks 1–3.
- Required point: one mandatory eligibility point; no over-specification or over-fragmentation observed.
- Failure rule: `missing_query_entities` caused the entity gate to fail; best point score was 0.294118 and document relevance was 0.549020.
- Classification: `LEXICAL_MATCH_OVERSTRICT`, secondary `SEMANTIC_MATCH_WEAKNESS`; confidence HIGH.

### DEMO013

- Retrieval: `RETRIEVAL_OK`; source `KBV1-PUB-PUBV2C-0075` appears in ranks 1, 2, and 4.
- Required point: one mandatory point; no requested attribute mismatch and no entity mismatch.
- Failure rule: best score 0.166667 fell below the partial threshold 0.18, so no support span was admitted.
- Classification: `LEXICAL_MATCH_OVERSTRICT`, secondary `SEMANTIC_MATCH_WEAKNESS`; confidence MEDIUM.

### POS003

- Retrieval: `RETRIEVAL_OK`; eligibility source chunks are in ranks 1–3.
- Required point: one mandatory `ELIGIBILITY` point; correct supporting spans exist at score 0.357143.
- Failure rule: the same false entity extraction pattern as DEMO002 set `missing_query_entities`, forcing `NOT_SUPPORTED`.
- Classification: `LEXICAL_MATCH_OVERSTRICT`, secondary `SEMANTIC_MATCH_WEAKNESS`; confidence HIGH.

## 3. Original vs Paraphrase Comparison

DEMO002 and POS003 are semantically close eligibility questions. Their Retriever inputs contain the same source family and their Evidence traces diverge at the same entity gate: the query prefix is treated as an entity absent from the KB. DEMO013 follows a different path: no entity mismatch, but lexical overlap is below the partial floor. The divergence begins in Evidence matching, not Retriever ranking.

## 4. Evidence Decision Rule

The current implementation uses `deterministic_lexical_structural_support_proxy`:

1. Decompose query into required points and requested attributes.
2. Build sentence spans from usable Top-5 chunks.
3. Compute point-to-span lexical overlap.
4. Require score ≥ 0.52, entity presence, no missing requested attributes, and document relevance ≥ 0.08 for `SUPPORTED`.
5. Permit `PARTIALLY_SUPPORTED` only at score ≥ 0.18 with entity gate satisfied.
6. Aggregate all points: all supported → `SUFFICIENT`; any supported/partial → `PARTIAL`; otherwise `INSUFFICIENT`.

The decisive gates are recorded in `evidence_decision_rule_trace_v1.json`.

## 5. Failure Family Summary

The three cases share a lexical/semantic matching family, but not one identical subcause. DEMO002/POS003 share a systemic false entity-gate pattern. DEMO013 is a systemic paraphrase/lexical-score weakness. This is not a Retriever family and is separate from DEMO012 Citation blocking.

## 6. Candidate Mitigation

`NO_SAFE_EVIDENCE_FIX_IDENTIFIED` in this pass. No production threshold, required-point extraction, entity logic, or semantic matcher was changed; no experiment-only promotion was run. A future experiment must isolate one mechanism and include false-promote controls before any production consideration.

## 7. Candidate Experiment

`Not run — diagnosis only.` The trace does not justify choosing between minimal-core extraction, paraphrase-invariant mapping, semantic matching, or threshold review without changing multiple causal variables.

## 8. Safety Assessment

No under-rejecting change was made. No false promote was introduced. Evidence remains fail-closed, with no gold-answer or case-ID dependency. Retriever, Citation, Answer, and constrained decoding were not modified.

## 9. Demo Impact

These failures currently limit Full-support Rate and positive-answer quality. The Answer infrastructure blocker is already resolved; improving this Evidence family could raise full-support and positive-answer metrics, but no After estimate is claimed from diagnosis alone.

## 10. Frozen Integrity

KB, chunks, embeddings, Retriever, Evidence production semantics, Citation, Answer, Prompt, Prompt Freeze, Frozen Bundle, and Runtime production logic: unchanged.

## 11. Main Artifacts

- `D:\python_projects	singhua_ai\experiments\evidence_required_point_review_v1udit\evidence_required_point_case_trace_v1.json`
- `D:\python_projects	singhua_ai\experiments\evidence_required_point_review_v1udit\evidence_decision_rule_trace_v1.json`
- `D:\python_projects	singhua_ai\experiments\evidence_required_point_review_v1udit\evidence_required_point_root_cause_matrix.json`
- `D:\python_projects	singhua_ai\experiments\evidence_required_point_review_v1\data	argeted_evidence_review_cases.json`

## 12. Remaining Highest-priority Failure Family

`Evidence Required Point`.

## 13. Recommended Next Single Task

`Evidence Paraphrase-Invariant Mapping Experiment`: experiment-only, with explicit entity-gate false-positive and false-promote controls; no production integration until DEMO002/DEMO013/POS003 and refusal controls are evaluated together.
