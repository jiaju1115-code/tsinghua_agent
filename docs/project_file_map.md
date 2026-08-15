# Project file map

| Old path | New path | Purpose | Status |
| --- | --- | --- | --- |
| `data_first/` | `data/01_public_baseline/` | Initial public/portal baseline pipeline and evidence | frozen |
| `data_second/public_expansion_v1/` | `data/02_public_expansion/v1/` | Historical public expansion runs | historical |
| `data_second/public_expansion_v2/` | `data/02_public_expansion/v2/` | Audited public expansion | frozen |
| — | `data/03_knowledge_base/v1/` | **Canonical Knowledge Base V1 and the only formal RAG Retrieval V1 runtime bundle** | **active / frozen** |
| `data_second/staging_public_baseline_v1/` | `data/04_public_staging/` | Current public staging corpus | frozen |
| `data_second/restricted_expansion_v1/` | `data/05_restricted_expansion/v1/` | Restricted-stage research assets | frozen |
| `data_second/human_audit/`, `knowledge/` | `data/06_human_annotation/` | Human audit and review states | active review |
| `data_second/rag_v*/` | `evaluation/rag/v*/` | Retrieval/RAG experiments | experimental |
| -- | `src/evidence_sufficiency_v1/` | Evidence Sufficiency Runtime V1 implementation | active / frozen |
| -- | `evaluation/evidence_sufficiency/v1/` | Runtime V1 audit, tests, regression diagnostics, and freeze artifacts | active / frozen |
| -- | `src/citation_support_v1/` | Citation / Support Runtime V1 implementation; validates Evidence provenance into pre-answer support packages | active / frozen |
| -- | `evaluation/citation_support/v1/` | Citation / Support V1 config, lineage audit, validation, integrity, and freeze artifacts | active / frozen |
| -- | `src/answer_generation_v1/` | Answer Generation Runtime V1 implementation; consumes only Citation Support V1 packages | active / frozen |
| -- | `evaluation/answer_generation/runtime_v1/` | Formal Answer Generation V1 config, prompt, audit, validation, and freeze artifacts | active / frozen |
| -- | `src/e2e_orchestrator_v1/` | Unified E2E Orchestrator V1; strictly sequences the four frozen runtime layers | active / frozen |
| -- | `evaluation/e2e_orchestrator/runtime_v1/` | Orchestrator contract audit, schema, validation, protocol, integrity, and freeze artifacts | active / frozen |
| -- | `evaluation/e2e_heldout/v1/` | Held-out E2E Evaluation V1 dataset, contamination audit, human review protocol, and one-shot runner | active / frozen, not run |
| — | `evaluation/e2e/v1/benchmark/exclusion_registry.jsonl` | Historical QA exclusion registry for a future held-out E2E benchmark; not a benchmark itself | active preparation |
| `data_second/answer_eval_v*/` | `evaluation/answer_generation/v*/` | Answer-generation evaluation | experimental |
| `data_second/prompt_v3_2_blind_test_v1/` | `evaluation/prompt_v3_2_blind_test_v1/` | Frozen Prompt V3.2 blind test | frozen |
| `data_second/citation_pipeline_v*/` | `evaluation/citation/v*/` | Citation experiments | experimental |
| `data_second/public_rebuild_v1/` | `experiments/public_rebuild_v1/` | Rebuild experiment | historical experiment |
| legacy prompt tests and residual files | `archive/deprecated_or_legacy/` | Retained non-mainline research history | archived |
| root Codex scripts | `scripts/` | Historical operational scripts | historical |

No final directory is named `data_first` or `data_second`.

## Active vs. legacy runtime boundary

- **ACTIVE runtime corpus/retriever:** `data/03_knowledge_base/v1/` only. It contains `KNOWLEDGE_BASE_V1` and `RAG_RETRIEVAL_V1` freeze manifests, canonical sources, chunks, index, provenance, and runtime configuration. Future runtime code must resolve this root-relative path and must not read staging directly.
- **ACTIVE evidence gate:** `src/evidence_sufficiency_v1/` consumes only the frozen Retriever V1 Top-5 result. Its audit, validation, and freeze artifacts are under `evaluation/evidence_sufficiency/v1/`; it does not perform retrieval, answer generation, or citation alignment.
- **ACTIVE citation/support gate:** `src/citation_support_v1/` consumes completed Retriever V1 and Evidence V1 objects. It validates and groups provenance into citation-ready support units but does not generate answers, evaluate answer claims, or render final citations.
- **ACTIVE answer generation gate:** `src/answer_generation_v1/` consumes only Citation Support V1 packages and maps `READY / PARTIAL / BLOCKED` to structured `FULL_ANSWER / PARTIAL_ANSWER / REFUSAL`. Historical `evaluation/answer_generation/v0/` and `/v1/` remain experimental lineage and are not runtime dependencies.
- **ACTIVE unified orchestrator:** `src/e2e_orchestrator_v1/` validates and calls `RAG_RETRIEVAL_V1 -> EVIDENCE_SUFFICIENCY_V1 -> CITATION_SUPPORT_V1 -> ANSWER_GENERATION_V1` exactly once in order. Its formal artifacts are under `evaluation/e2e_orchestrator/runtime_v1/`; it adds no fallback, repair, retry, re-retrieval, semantic classifier, or held-out case execution.
- **ACTIVE upstream candidates:** Router V0.2 (`experiments/router_v0_2/`) and the Answer Generation candidate remain separately evaluated candidates; they are not part of the Retrieval V1 bundle.
- **LEGACY / historical / provenance only:** `data/04_public_staging/`, `evaluation/rag/v0/`, `evaluation/rag/v1/`, historical answer/citation evaluations, and any references to `data_second`. They remain preserved for audit and regression diagnostics but are not runtime dependencies of Knowledge Base V1.
- Changes to corpus, chunking, index, embedding model, retriever configuration, or source admission require a new Knowledge Base V2 / RAG Retrieval V2; V1 must not be modified in place.
