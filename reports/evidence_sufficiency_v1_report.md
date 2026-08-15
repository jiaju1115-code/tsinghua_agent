# Evidence Sufficiency Runtime V1 Formalization Report

Date: 2026-08-15

## 1. Historical Audit

The lineage audit cross-checked code, configuration, datasets, results, reports, and frozen artifacts rather than relying on README claims.

- V0.1 was a deterministic lexical coverage gate. Its three-state semantics are retained; sample-specific mismatch tokens and thresholds are rejected.
- V0.2 added sentence-span traces, n-gram coverage, entity/document overlap, and contamination rules. Span provenance is adapted, but its so-called semantic score is rejected because no semantic model exists.
- V0.3 introduced minimal core points, requested-attribute features, 15 lexical/shape features, a Random Forest, and a 0.58 sufficient threshold. Minimal-core/requested-attribute/optional concepts are adapted. The trained model, threshold, and semantic-entailment claim are rejected because all 147 rows are seen calibration data and family leakage exists.
- V0.4 was an offline Ollama prototype. Its first real prompt failed with HTTP 502 after exceeding the served context; it produced no valid semantic support matrix or evaluation. The engine is rejected. Its support-matrix concept remains unresolved for a future genuine entailment implementation.

The complete per-item disposition is in `evaluation/evidence_sufficiency/v1/audit/historical_logic_disposition.json`.

## 2. Runtime Architecture

The frozen chain is:

`query -> RAG_RETRIEVAL_V1 ordered Top-5 -> evaluate_evidence -> structured three-state decision`

Runtime V1 is a standalone, deterministic, fail-closed lexical/structural support proxy. It performs query decomposition, requested-attribute extraction, sentence-span comparison, entity viability checks, attribute presence checks, limited conflict detection, provenance aggregation, and policy mapping. It does not run retrieval, call a network or model, generate an answer, or align citations.

## 3. Input / Output Contract

Public API: `evaluate_evidence(query, case_id, retrieval_result)`.

The input must declare `RAG_RETRIEVAL_V1` and `KNOWLEDGE_BASE_V1` and contain exactly five ranked, uniquely identified chunks with the frozen retrieval fields. Validation errors, retrieval errors, version mismatches, unusable evidence, and parse failures fail closed.

The output includes query/case/version fields; decision and policy signal; nullable confidence; required points and per-point support spans; supported, partially supported, and unsupported point IDs; requested and missing attributes; optional information; supporting chunk/source IDs; finite reason codes; diagnostics; latency; and error. `confidence` is always null because no calibrated probability model is used.

## 4. Decision Policy

- `SUFFICIENT` / `ALLOW_FULL_ANSWER`: all minimal core points are supported, requested attributes are present, and no unresolved conflict exists.
- `PARTIAL` / `ALLOW_PARTIAL_ANSWER`: at least one core point has usable support, but another core point or requested attribute remains incomplete.
- `INSUFFICIENT` / `REQUIRE_REFUSAL`: no core point is safely supported, evidence conflicts, or validation/evaluation cannot safely complete.

The fixed reason vocabulary has 14 values: `CORE_POINTS_SUPPORTED`, `CORE_POINT_MISSING`, `REQUESTED_ATTRIBUTE_MISSING`, `EVIDENCE_ONLY_PARTIAL`, `EVIDENCE_IRRELEVANT`, `EVIDENCE_CONFLICT`, `TEMPORAL_SUPPORT_UNCLEAR`, `SOURCE_SUPPORT_TOO_WEAK`, `NO_USABLE_EVIDENCE`, `RETRIEVAL_ERROR`, `INPUT_SCHEMA_INVALID`, `VERSION_MISMATCH`, `REQUIRED_POINT_PARSE_FAILED`, and `LEXICAL_PROXY_LIMITATION`.

## 5. Required Points

The parser separates optional tails before decomposing the remaining query into at most five minimal core points. Requested attributes use a frozen vocabulary: time, deadline, location, price, eligibility, procedure, entry, materials, contact, object, and current status. Missing requested attributes prevent `SUFFICIENT`. Missing optional information does not lower the decision.

This is transparent rule-based decomposition, not a learned query planner. Its parse output and supporting spans are included for audit.

## 6. Semantic Entailment Status

Runtime V1 does **not** implement semantic entailment. V0.1-V0.3 are lexical/structural proxies; V0.4 did not produce a reproducible valid semantic result. Runtime diagnostics explicitly set `semantic_entailment: false`, the method is named `deterministic_lexical_structural_support_proxy`, and every completed decision contains `LEXICAL_PROXY_LIMITATION`.

No model was downloaded, no historical Random Forest was loaded, and no entailment probability is fabricated.

## 7. Validation

- Unit tests: PASS, 10 run, 0 failures, 0 errors, 0 skipped. Required cases include all three decisions, missing attribute, optional-only missing, empty/irrelevant/conflicting evidence, malformed input, version mismatch, and repeatability.
- Interface integration: PASS on 3 live calls through the frozen `DenseRetrieverV1`; every call returned strict Top-5, passed schema/version checks, and produced a structured Evidence V1 result. Answer and citation runtimes were not called.
- Determinism: PASS. Evidence results are identical after excluding latency. Repeated Retriever V1 output is also identical after excluding latency.
- Historical regression: completed on 101/147 rows that already had exactly five frozen evidence items. The other 46 were excluded without truncation, padding, or reretrieval.

## 8. Metrics

These are `HISTORICAL_CALIBRATION_COMPATIBILITY_REGRESSION` metrics, not held-out, production, semantic-entailment, or E2E metrics. Historical human-adjudicated labels are references, not absolute gold truth; synthetic rows are proxy constructions.

| Data | N | Exact agreement | Macro F1 | False sufficient | Over-refusal / missed sufficient | PARTIAL boundary errors |
|---|---:|---:|---:|---:|---:|---:|
| All eligible historical | 101 | 44/101 (43.56%) | 0.3453 (34.53%) | 0/101 (0.00%) | 48/101 (47.52%); 48/51 reference sufficient (94.12%) | 44/101 (43.56%) |
| Real human-adjudicated reference | 38 | 8/38 (21.05%) | 0.2033 (20.33%) | 0/38 (0.00%); 0/7 reference non-sufficient (0.00%) | 28/38 (73.68%); 28/31 reference sufficient (90.32%) | 22/38 (57.89%) |
| Synthetic constructed proxy | 63 | 36/63 (57.14%) | 0.2857 (28.57%) | 0/63 (0.00%); 0/43 reference non-sufficient (0.00%) | 20/63 (31.75%); 20/20 reference sufficient (100.00%) | 22/63 (34.92%) |

All-eligible confusion matrix (rows = historical reference, columns = runtime):

| Reference \ Runtime | SUFFICIENT | PARTIAL | INSUFFICIENT |
|---|---:|---:|---:|
| SUFFICIENT | 3 | 35 | 13 |
| PARTIAL | 0 | 4 | 2 |
| INSUFFICIENT | 0 | 7 | 37 |

Per-class all-eligible precision / recall / F1: SUFFICIENT 100.00% / 5.88% / 11.11%; PARTIAL 8.70% / 66.67% / 15.38%; INSUFFICIENT 71.15% / 84.09% / 77.08%.

## 9. False Sufficient

False sufficient is 0/101 (0.00%) on the eligible historical regression: 0/7 (0.00%) among real human-reference non-sufficient cases and 0/43 (0.00%) among synthetic non-sufficient cases. This is encouraging for fail-closed safety but is not a held-out false-sufficient estimate. It coexists with severe over-refusal and must not be interpreted as generalization proof.

## 10. Leakage Audit

All 147 V0.3 rows are marked `SEEN_CALIBRATION` and 147/147 are registered in the future-E2E exclusion registry. They collapse to only 49 unique normalized queries; 44 duplicate-query groups contain 142 rows. Direct recomputation finds 21 duplicated query-evidence hash groups containing 42 rows. Forty of 49 normalized-query families and 28 of 44 source-query variant families crossed V0.3 CV folds because partitioning used record IDs rather than family groups.

Registry-level normalized-query overlap with V0.3 is 38/38 for RAG V1 evaluation, 38/38 for Answer V0, 11/42 for Router blind-shadow, and 11/12 for E2E12. Therefore historical CV and regression are not independent performance evidence. Runtime V1 used no training data and its declared thresholds were not changed after regression.

## 11. Integrity

Pre/post inventories cover Knowledge Base V1, Retriever V1 adapter, Evidence V0.1-V0.4, human annotation, Router history, Answer/Citation history, and the exclusion registry. Both inventories contain 919 files and have the identical inventory SHA256 `58f562d6a6f561d6c5df31614bd93d2c375452da6412fd3e71597f057e680f3f`.

No frozen upstream file was added, removed, or changed. `data/03_knowledge_base/v1/` and `src/retrieval_v1/adapter.py` remain unmodified. No `UPSTREAM_FROZEN_BLOCKER` was identified.

## 12. Limitations

- No genuine semantic entailment or paraphrase reasoning exists.
- Rule-based decomposition and entity extraction can over-split, under-split, or miss implicit requirements.
- Lexical support does not prove factual entailment, negation handling, causal support, or complete temporal validity.
- Conflict detection covers only limited structured value types and may conservatively flag multiple legitimate values.
- Historical regression shows severe over-refusal: 28/31 human-reference sufficient rows were not classified sufficient.
- The 38-row human-reference subset is historical, overlapping, and highly imbalanced; it cannot establish full-pool or production performance.
- Supporting spans/IDs are Evidence provenance only, not sentence-level citation correctness.

The freeze therefore establishes a stable auditable fail-closed baseline, not a claim of acceptable held-out accuracy or answer coverage.

## 13. Freeze Status

`EVIDENCE_SUFFICIENCY_V1_FROZEN`

All eleven technical freeze conditions pass: lineage audit, explicit semantics, implementation, Retriever integration, unit tests, determinism, hashes, upstream invariance, limitations, and honest metric naming. The high over-refusal rate is retained as a material operational limitation rather than hidden or tuned away on overlapping historical data.

## 14. Main Artifacts

- Runtime: `src/evidence_sufficiency_v1/{runtime.py,policy.py,schema.py,__init__.py}`
- Configuration: `evaluation/evidence_sufficiency/v1/config/runtime_v1.json`
- Contract: `evaluation/evidence_sufficiency/v1/README.md`
- Historical audit: `evaluation/evidence_sufficiency/v1/audit/historical_lineage.md`
- Logic disposition: `evaluation/evidence_sufficiency/v1/audit/historical_logic_disposition.json`
- Leakage audit: `evaluation/evidence_sufficiency/v1/audit/leakage_audit.json`
- Input snapshots: `evaluation/evidence_sufficiency/v1/audit/{pre_input_snapshot.json,post_input_snapshot.json}`
- Tests: `evaluation/evidence_sufficiency/v1/tests/{test_runtime.py,unit_test_results.json,integration_results.json}`
- Regression: `evaluation/evidence_sufficiency/v1/results/{historical_regression_metrics.json,historical_regression_predictions.jsonl}`
- Freeze: `evaluation/evidence_sufficiency/v1/audit/evidence_sufficiency_v1_freeze.json` and sidecar SHA256
- Formal report: `reports/evidence_sufficiency_v1_report.md`

## 15. Recommended Next Step

Proceed next with `Citation / Support Runtime V1`, consuming only the supporting chunk/source provenance exposed here. Do not treat Evidence V1 support spans as citation correctness, and do not start answer generation or formal E2E as part of this step. A separate future V1.x/V2 track should evaluate genuine offline entailment and family-grouped held-out Evidence cases before relaxing the conservative gate.
