# Runtime V1 Architecture Audit

- Audit version: `RUNTIME_ARCHITECTURE_AUDIT_V1`
- Date: 2026-08-16
- Scope: read-only architecture and wiring audit. No production runtime, prompt, KB, retriever, evidence, citation, or answer changes.

## Executive conclusion

The current internal runtime is `run_e2e → DenseRetrieverV1 → Evidence Sufficiency V1 → Citation Support V1 → Answer Generation V1`. Router and Dynamic/Hybrid are not wired into it. There is no user-facing CLI/API/chat entrypoint for this chain. The recommended demo is therefore a thin user-facing adapter over the frozen V1 orchestrator, after connecting the already-approved Frozen Bundle V1.1 portability reference.

The architecture is structurally complete but operationally blocked at the default retriever's bundle integrity verification. Keep Dense V1 as the main retriever for now; Dynamic/Hybrid remains evaluation-only.

## Current actual runtime

```text
Direct Python caller (no unified user-facing entrypoint)
  -> src.e2e_orchestrator_v1.run_e2e(query, case_id)
  -> src.retrieval_v1.DenseRetrieverV1.retrieve
  -> src.evidence_sufficiency_v1.evaluate_evidence
  -> src.citation_support_v1.build_support_package
  -> src.answer_generation_v1.generate_answer
  -> structured final answer object
```

The actual call graph is present in `src/e2e_orchestrator_v1/runtime.py`. The current working-tree execution is blocked before retrieval output when `DenseRetrieverV1._verify_bundle()` sees the Windows raw-file/hash portability mismatch. Existing proxy/shadow results must not be described as actual user runtime.

## Recommended Demo Runtime V1

```text
Demo CLI/API adapter (new integration task)
  -> approved Frozen Bundle V1.1 portability-aware retriever loading
  -> UnifiedE2EOrchestratorV1.run_e2e
  -> Evidence Sufficiency V1
  -> Citation Support V1
  -> Answer Generation V1
  -> rendered answer + citations + status
```

Router is intentionally outside the main path until its contract is approved. Dynamic/Hybrid is a shadow branch only.

## Module status matrix

| Module | Status | Current role | Key finding |
|---|---|---|---|
| `Core Knowledge Base V1` | `FROZEN_PRODUCTION_READY` | frozen retrieval corpus | Formal frozen Core KB; legacy frozen paths preserved. |
| `Frozen Bundle V1.1 approved candidate` | `FROZEN_PRODUCTION_READY` | recommended portability reference | Approved active reference, but not yet wired into the original DenseRetrieverV1 loader. |
| `Dense Retriever V1` | `FROZEN_PRODUCTION_READY` | current orchestrator retriever | Frozen contract; current working-tree execution is BLOCKED by bundle raw hash verification. |
| `Router V0.2` | `EXPERIMENTAL` | none | Evaluated experiment; no import/wiring into e2e_orchestrator_v1. |
| `Dynamic/BM25/Hybrid Retriever family` | `EXPERIMENTAL` | none | Candidate and shadow-only; not the main production retriever. |
| `Dynamic Campus Candidate V1` | `EVALUATION_ONLY` | none | Candidate-only corpus; never merged into Core KB V1. |
| `Evidence Sufficiency V1` | `FROZEN_PRODUCTION_READY` | orchestrator stage | Deterministic contract layer; current direct caller is UnifiedE2EOrchestratorV1. |
| `Citation Support V1` | `FROZEN_PRODUCTION_READY` | orchestrator stage | Maps required points to support units and source metadata. |
| `Answer Generation V1` | `FROZEN_PRODUCTION_READY` | orchestrator stage | Uses local frozen Qwen GGUF adapter when model_adapter is absent; no external API. |
| `Unified E2E Orchestrator V1` | `PRODUCTION_CANDIDATE` | complete internal chain | Real internal wiring exists, but no user-facing caller and current default retriever verification is blocked. |
| `Unified user-facing runtime` | `BLOCKED` | none | No current CLI, API, chat loop, Streamlit, FastAPI, or Gradio entrypoint was found for the frozen QA chain. |
| `Dynamic/Core shadow evaluations` | `EVALUATION_ONLY` | none | Proxy and blocked runtime evidence; not user-facing production runtime. |

Allowed status vocabulary used: `FROZEN_PRODUCTION_READY`, `PRODUCTION_CANDIDATE`, `EXPERIMENTAL`, `EVALUATION_ONLY`, `LEGACY`, `BLOCKED`, `UNKNOWN`.

## Wiring audit

| Edge | Status | Evidence |
|---|---|---|
| Router → Retriever | `NOT_WIRED` | No current import/call from experiments/router_v0_2 into src/e2e_orchestrator_v1; orchestrator directly instantiates DenseRetrieverV1. |
| Retriever → Evidence | `WIRED_BUT_RUNTIME_BLOCKED` | UnifiedE2EOrchestratorV1.run_e2e calls evaluate_evidence after retrieval; default DenseRetrieverV1 currently fails bundle verification before producing output. |
| Evidence → Citation | `WIRED` | run_e2e passes retrieval and evidence results to build_support_package with frozen contract validation. |
| Citation → Answer | `WIRED` | run_e2e passes support package to generate_answer and enforces status propagation/no-model-call behavior on BLOCKED. |
| Answer → user runtime | `NOT_WIRED` | run_e2e returns a structured result to its caller; no current user-facing caller/renderer exists. |

## Duplicate and ambiguous runtime inventory

- Router V0/V0.1/V0.2 and web-search routers coexist under experiments; retain as history/experiments, do not import into the current chain.
- Dense, BM25, Dynamic and Hybrid retrievers coexist; Dense V1 is the current frozen-chain choice, while Dynamic/Hybrid remains evaluation-only.
- Evidence/Citation/Answer historical versions coexist with `src/*_v1`; only the V1 source runtime is called by the orchestrator.
- Proxy and actual runtime shadow evaluations are separate evidence classes; neither is a user-facing runtime.

## Hybrid decision

**KEEP_DENSE_V1_FOR_NOW.** Dynamic/Hybrid has no approved production wiring and no gold-regression evidence showing superiority. It is also not connected to the frozen Evidence/Citation/Answer contracts.

## Minimum integration gap

### P0

1. Add one user-facing demo entrypoint that calls `run_e2e`.
2. Connect the approved Frozen Bundle V1.1 portability-aware loader so the default retriever passes integrity verification.

### P1

1. Run actual Frozen Runtime E2E through the repaired loader.
2. Define and evaluate a Router→Retriever contract before enabling routing.

### P2

1. Re-evaluate Dynamic/Hybrid against the frozen gold set before any promotion.
2. Add observability and rendering around the structured result.

## Answer Generation special audit

Answer Generation V1 consumes the Frozen Citation Support V1 package, uses the local Qwen Qwen2.5 1.5B GGUF adapter when no adapter is injected, and has no external API dependency. The orchestrator enforces status propagation, provenance links, prompt-injection refusal, and no-model-call behavior when support is blocked. Its remaining gap is not a new answer algorithm: it lacks a user-facing caller and is currently upstream-blocked by retriever integrity verification.

## Agent/runtime audit

No agent loop, tool-use loop, planning layer, or memory subsystem was found in the current frozen chain. Runtime V1 should remain a deterministic orchestrator call; do not introduce agent autonomy in the integration task.

## Frozen integrity

- Core frozen paths: PASS — untouched by this audit.
- Legacy frozen paths: PASS — preserved.
- Approved Frozen Bundle V1.1 reference: PASS — preserved.
- Scope compliance: PASS — only audit/report artifacts are added.

## Next single task

**Runtime V1 Integration**: create the thin demo adapter, route it through the approved V1.1 portability-aware retriever loading, execute real Frozen Runtime E2E, and render the structured answer/citation/status object. This is an integration and validation task, not a KB/retriever-quality redesign or an answer-generation prompt change.
