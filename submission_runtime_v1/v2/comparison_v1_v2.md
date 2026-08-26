# Research/Submission Runtime Comparison

This comparison separates observed platform behavior from intended design. V1
and V2 are draft submission assets; neither changes Frozen Research Runtime.

| Dimension | Submission V1 | Submission V2 | Evidence |
|---|---|---|---|
| Workflow | `Start -> Retrieval -> End` | Router with seven explicit classes and default, then shared retrieval, evidence-gated LLM, End | Saved V2 graph reloaded and seven representative live runs |
| Knowledge base | 7 documents, 11 segments, 6.45 KB | 20 documents, 45 segments, 28.42 KB | Platform KB counters after 13 controlled uploads |
| Source policy | Small public-only subset | Same base plus 13 approved public canonical sources | `kb_expansion_manifest.jsonl` |
| General conversation | Empty or KB-bound behavior | Natural general response after explicit exemption | Cold-joke live test |
| Current information | Weak match could flow to output | Refuses to guess without fresh evidence and gives a verification path | Library-hours live test |
| Evidence state | No three-state gate | Combined prompt demonstrates sufficient, partial, and insufficient behavior | Procedure, aid, and current/scholarship live tests |
| Requested attributes | Related document could be returned without checking the requested field | Prompt checks procedure fields and names missing attributes | Degree-proof and aid live tests |
| Unsafe requests | No generation boundary in retrieval-only V1 | Natural refusal plus legitimate alternative | Credential-theft live test |
| Citation | No reliable citation contract | No fabricated links observed, but only generic fragment fallback is available | Seven live runs; strict citation remains incomplete |
| Deterministic validation | Not deployed | Local fail-closed validator passes five unit tests; not deployed as a Code node | `evidence_validator.py`, `test_evidence_validator.py` |
| Evaluation | 10-case V1 live run: 2 correct, 2 empty fail-closed, 6 relevance/attribute failures | Seven representative live cases pass intended behavior; 50-case set defined but not fully run | `regression/test_results_v2.md` |

## V3 candidate delta

| Dimension | V2 | V3 draft candidate | Live evidence |
|---|---|---|---|
| Evidence step | Combined with final answer | Separate inspectable judge node with three states | In-study-certificate judge returned `SUFFICIENT` before answer ran |
| Conversation | General exemption inside one prompt | Router class passed explicitly to final response; concise, identity-sensitive instructions | Graduate-student query received only its applicable steps |
| Current facts | Prompt rule | Route-aware dated-evidence fail-close | “图书馆今天几点关门” declined to guess and gave official verification path |
| Partial answer | Prompt rule | Independent judge plus fact/advice/missing-detail response | Aid-preparation query gave eligibility and named missing material detail |
| Safety | Prompt rule | Route-aware safe answer | Credential-theft and instruction-injection/fabrication requests refused |
| New KB source | Not separately regression-tested | Graduate degree-proof source retrieved and used | Materials, office, contact and collection time returned |

V3 is materially stronger as a platform runtime than V2 and is the submission
candidate. It is not claimed to have a quantitative win over the local LoRA:
the recorded LoRA training had no valid post-training held-out platform-style
evaluation, so that comparison cannot honestly be asserted without running a
paired evaluation.

## Interpretation

V2 materially improves routing, coverage, uncertainty language, and helpfulness,
but it is not equivalent to Frozen Research Runtime. Platform-owned chunking,
retrieval scores, and reranking remain non-equivalent to the local retriever.
The combined judge/answer node and generic citation fallback are the two main
reasons V2 remains partial rather than ready.
