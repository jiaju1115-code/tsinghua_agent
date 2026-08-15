# Citation / Support Runtime V1 Formalization Report

Date: 2026-08-15

## 1. Historical Citation Audit

Repository-wide lineage review covered historical Citation V1/V2, Answer Generation & Citation Evaluation V0, RAG citation mapping, prompts, scripts, datasets, reports, proxy labels, workbooks, and the exclusion registry. Historical Citation V1/V2 are post-generation systems over the same 38 frozen answers: V1 used deterministic claim segmentation plus dense/lexical assignment; V2 added 6,405 extracted spans and a relevance reranker. Neither has completed human claim-to-citation correctness labels. The V2 workbook's 36 human fields are blank, and the 17-row adjudication packet is secondary-AI review rather than human gold.

Top-5 containment, deterministic provenance, exact source/chunk mapping, normalization, deduplication, and source aggregation were retained with adaptation. Answer claim extraction, BGE/reranker thresholds, automatic support labels, unsupported-claim/faithfulness scoring, marker rendering, and the historical 100% precision proxy were rejected for runtime use. All 38 historical normalized queries overlap the exclusion registry, so the assets are not held-out. Full dispositions are in `evaluation/citation_support/v1/audit/historical_logic_disposition.json`.

## 2. Runtime Architecture

The formal chain is `query -> RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> structured support package`. The public API is `build_support_package(query, case_id, retrieval_result, evidence_result)`. Citation V1 is a pure downstream consumer: it performs no retrieval, KB search, network access, Evidence rerun, answer generation, claim extraction, or rendering.

## 3. Input Contract

Inputs must be non-empty and agree on query/case ID. Versions must be exactly `KNOWLEDGE_BASE_V1`, `RAG_RETRIEVAL_V1`, and `EVIDENCE_SUFFICIENCY_V1`. Retriever input must contain five uniquely identified chunks ranked 1-5. Evidence must match its complete V1 schema; decision/policy and required-point status lists must be internally consistent. Supporting chunks must be in Top-5, source IDs must match chunk metadata, and critical errors fail closed.

## 4. Output Contract

The output includes all version and policy fields; `READY | PARTIAL | BLOCKED`; required-point mappings; support units; source-level citation candidates; excluded candidates with finite reason codes; source groups; usable IDs; diagnostics; latency; and error. Exact top-level and nested field sets are frozen in `src/citation_support_v1/schema.py`; parameters and vocabularies are versioned in `evaluation/citation_support/v1/config/citation_support_v1.json`.

## 5. Support Unit

Each stable `CSU-*` unit records required-point IDs, canonical source/chunk IDs, allowlisted source provenance, raw zero-based end-exclusive offsets, raw and normalized span text, original Evidence span text, normalization reasons, primary/supplementary role, Retriever rank, Evidence span IDs, and match multiplicity. IDs are deterministic SHA-256 prefixes, never random UUIDs.

## 6. Span Normalization

Evidence spans are mapped back to raw chunk text using NFKC, whitespace collapse, Markdown-label preservation, and HTML-tag removal while retaining raw offsets. Empty, punctuation-only, title-only, too-short, missing, or invalid spans are excluded. Immediate terminal punctuation may be safely restored; sentence-boundary status is recorded; duplicate positions collapse; nearby spans merge only across a short whitespace/punctuation gap and retain every original span and reason. No new text or semantic evidence is created.

## 7. Source Aggregation

Units remain chunk-addressable but group by canonical source ID. One source can contribute multiple chunks without becoming multiple independent citation sources. Source groups retain contributing chunks, point coverage, unit IDs, and source-level minimum Retriever rank. Candidate ordering is deterministic: point coverage descending, rank ascending, source ID ascending. Necessary support is not deleted to reduce source count.

## 8. Required-point Mapping

Every Evidence required point receives `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `UNSUPPORTED` mapping plus exact support-unit/source IDs and any integrity issue. Citation V1 validates provenance but does not overturn the upstream Evidence decision. A blocked package clears usable support references so downstream consumers cannot bypass the gate.

## 9. Support Gate

- Evidence `SUFFICIENT` becomes `READY` only when every required point maps to validated support; otherwise `BLOCKED`.
- Evidence `PARTIAL` becomes `PARTIAL` only when at least one validated supported piece remains; only those pieces are exposed.
- Evidence `INSUFFICIENT` always remains `BLOCKED`; Citation V1 never searches for rescue evidence.

The live SUFFICIENT integration case correctly became `BLOCKED` because Evidence exposed only title spans, demonstrating the integrity gate rather than a forced pass.

## 10. Citation Correctness Status

`NO`. This runtime has no final answer or answer claims and therefore does not implement final-answer citation correctness, Citation Accuracy, Citation Recall, claim coverage, unsupported-claim detection, faithfulness, or final citation rendering. Evidence provenance and validated support units are not gold citation labels.

## 11. Validation

Unit tests: **16/16 PASS (100.00%)**, covering all 16 required scenario classes. Full-chain integration: **4/4 PASS (100.00%)** across 3 live cases plus 1 declared contract fixture. Live cases exercised frozen Retrieval and Evidence and naturally covered SUFFICIENT, PARTIAL, and INSUFFICIENT; the live SUFFICIENT was integrity-blocked, so a schema-valid fixture using frozen Top-5 rows covered `READY` without changing Evidence. Determinism excluding `latency_ms`: **PASS** for units, IDs, groups, candidate order, exclusions, and status. No answer, rendering, unsupported-claim detection, network, or formal E2E was invoked.

## 12. Historical Regression

No `HISTORICAL_COMPATIBILITY_REGRESSION` was executed because historical Citation V1/V2 require generated answers and do not satisfy Citation Support V1's pre-answer Evidence-result input contract. Their repeated queries are in the exclusion registry and their labels are automatic/proxy or secondary-AI, not held-out human citation correctness. They were used only for lineage and logic-disposition audit; no thresholds were tuned against them.

## 13. Integrity

Pre/post inventory comparison covered 1,467 frozen upstream files. Pre and post hashes are both `9468e847db92c5819027ec177a6d680b77c4861a609d7c152c8fb79135b1c9a4`. Upstream added = **0**, removed = **0**, modified = **0**. Knowledge Base V1, RAG Retrieval V1, and Evidence Sufficiency V1 are unchanged. Historical Evidence, Citation, Answer, human annotation, and exclusion-registry scopes are also unchanged.

## 14. Limitations

Evidence V1 remains a deterministic lexical/structural proxy without semantic entailment. Citation V1 cannot repair Evidence over-refusal, improve retrieval recall, search outside Top-5, judge source authority, validate an answer claim, detect hallucinations, or choose user-facing citation placement. Title-only Evidence provenance is conservatively blocked. Restricted-source classification relies on the frozen canonical source-ID prefix because Retriever V1 does not expose source type; output is deliberately metadata-minimal.

## 15. Freeze Status

`CITATION_SUPPORT_V1_FROZEN`

All 18 freeze gates passed, including historical audit, contracts, support schema, normalization, mapping, aggregation, fail-closed behavior, tests, determinism, upstream integrity, scope boundaries, limitations, and truthful correctness status.

## 16. Main Artifacts

- `src/citation_support_v1/`
- `evaluation/citation_support/v1/config/citation_support_v1.json`
- `evaluation/citation_support/v1/audit/historical_citation_lineage.md`
- `evaluation/citation_support/v1/audit/historical_logic_disposition.json`
- `evaluation/citation_support/v1/validation/unit_test_results.json`
- `evaluation/citation_support/v1/validation/integration_results.json`
- `evaluation/citation_support/v1/validation/integration_support_packages.jsonl`
- `evaluation/citation_support/v1/validation/engineering_metrics.json`
- `evaluation/citation_support/v1/audit/final_integrity_report.json`
- `evaluation/citation_support/v1/audit/citation_support_v1_freeze.json`
- `reports/citation_support_v1_report.md`

## 17. Recommended Next Step

`Answer Generation Runtime V1`. It should consume only Citation / Support V1 packages and obey `READY | PARTIAL | BLOCKED`; it must not bypass this gate to read Retriever Top-5 freely. This next phase was not executed.
