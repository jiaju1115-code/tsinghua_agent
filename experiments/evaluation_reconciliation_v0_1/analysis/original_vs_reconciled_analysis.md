# Original vs reconciled

| Metric | Original V0 | Reconciled V0.1 | Delta |
|---|---:|---:|---:|
| evidence_sufficient_count | 43 | 34 | -9 |
| clean_subset_size | 43 | 34 | -9 |
| clean_correctness_mean_0_to_2 | 1.186046511627907 | 1.2058823529411764 | 0.01983584131326932 |
| completeness | 0.3798449612403101 | NOT_DIRECTLY_COMPARABLE | NOT_DIRECTLY_COMPARABLE |
| unsupported_claim_rate | 0.2366412213740458 | NOT_DIRECTLY_COMPARABLE | NOT_DIRECTLY_COMPARABLE |
| citation_coverage | 0.0916030534351145 | NOT_DIRECTLY_COMPARABLE | NOT_DIRECTLY_COMPARABLE |
| evidence_non_sufficient_count | 7 | 16 | 9 |
| generation_primary_failure_count | 49 | 44 | NOT_DIRECTLY_COMPARABLE |
| correct_refusal_count | PROXY_NOT_STRICTLY_COMPARABLE | 2 | NOT_DIRECTLY_COMPARABLE |
| wrong_refusal_count | 1 | 1 | NOT_DIRECTLY_COMPARABLE |

The reconciled set is HYBRID_RECONCILED: 17 secondary-AI rows plus 33 unreviewed original proxies. Completeness, unsupported-claim rate and citation coverage use incompatible denominators and are not forced into numeric deltas.
