# Project file map

| Old path | New path | Purpose | Status |
| --- | --- | --- | --- |
| `data_first/` | `data/01_public_baseline/` | Initial public/portal baseline pipeline and evidence | frozen |
| `data_second/public_expansion_v1/` | `data/02_public_expansion/v1/` | Historical public expansion runs | historical |
| `data_second/public_expansion_v2/` | `data/02_public_expansion/v2/` | Audited public expansion | frozen |
| `data_second/staging_public_baseline_v1/` | `data/04_public_staging/` | Current public staging corpus | frozen |
| `data_second/restricted_expansion_v1/` | `data/05_restricted_expansion/v1/` | Restricted-stage research assets | frozen |
| `data_second/human_audit/`, `knowledge/` | `data/06_human_annotation/` | Human audit and review states | active review |
| `data_second/rag_v*/` | `evaluation/rag/v*/` | Retrieval/RAG experiments | experimental |
| `data_second/answer_eval_v*/` | `evaluation/answer_generation/v*/` | Answer-generation evaluation | experimental |
| `data_second/prompt_v3_2_blind_test_v1/` | `evaluation/prompt_v3_2_blind_test_v1/` | Frozen Prompt V3.2 blind test | frozen |
| `data_second/citation_pipeline_v*/` | `evaluation/citation/v*/` | Citation experiments | experimental |
| `data_second/public_rebuild_v1/` | `experiments/public_rebuild_v1/` | Rebuild experiment | historical experiment |
| legacy prompt tests and residual files | `archive/deprecated_or_legacy/` | Retained non-mainline research history | archived |
| root Codex scripts | `scripts/` | Historical operational scripts | historical |

No final directory is named `data_first` or `data_second`.
