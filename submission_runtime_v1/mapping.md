# Local V1 to Coze mapping

| Local behavior | Coze implementation | Current state | Difference / risk |
|---|---|---|---|
| Frozen KB V1 (122 sources, 488 chunks) | Coze knowledge base | Partial prototype | Only a small public-only sample was uploaded; platform chunking/indexing differs. |
| DenseRetrieverV1 Top-5 | Knowledge Retrieval, hybrid, Top-K 5, threshold 0.5 | Working | Encoder, scores, chunk boundaries, query rewrite, and reranker are platform-owned and are not equivalent to Frozen Retriever V1. |
| Required-point decomposition and requested attributes | Code node or tightly constrained Evidence Judge | Not deployed | Must preserve TIME/DEADLINE/LOCATION/PRICE/ELIGIBILITY/PROCEDURE/ENTRY/MATERIALS/CONTACT/OBJECT/CURRENT_STATUS checks. |
| `SUFFICIENT/PARTIAL/INSUFFICIENT` | Evidence Judge + Selector | Not deployed | Current retrieval node has no three-state gate. |
| `READY/PARTIAL/BLOCKED` one-way support gate | Selector branches | Not deployed | Current weak matches can reach output directly. |
| Claim-to-support-unit provenance | Citation formatter using returned document metadata only | Not deployed | Current workflow output does not expose reliable title/URL citations. |
| Evidence-bound claim extraction | Platform LLM node after gate | Not deployed | A test LLM node was explored but removed when the editor could not safely replace the existing direct edge; no model-call claim is made. |
| Deterministic refusal with no model call | INSUFFICIENT branch static output | Not deployed | Empty retrieval currently yields an empty string, not natural uncertainty text. |
| Natural partial answer | PARTIAL branch + deterministic limitation text | Not deployed | Current output may dump a related document without naming the missing attribute. |
| Restricted-source redaction | Pre-output policy | Not applicable to prototype | No restricted source was uploaded. This must remain fail-closed before any broader migration. |
| Prompt-injection boundary | System prompt treating query/evidence as untrusted data | Specified locally | Injection tests returned empty results in the retrieval-only prototype, but the LLM boundary is untested. |

## Non-equivalence statement

`SUBMISSION_RETRIEVER_ADAPTATION` means only that the platform was configured to Top-K 5. It does not assert identical embeddings, retrieval order, thresholds, chunk IDs, or evaluation behavior.
