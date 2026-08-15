# V0 metric reconciliation

Historical final_metrics: correctness 1.2368, faithfulness 1.2895, unsupported 0.0092 (1/109). Historical evaluator summary instead reports unsupported 0.0439 (5/114).

Current Track A reuses correctness/faithfulness: 1.236842105263158 / 1.2894736842105263. New unsupported proxy: 0.10576923076923077; denominator is deterministic atomic factual/procedural claims, so it must not overwrite either historical metric.

Historical completeness is 1.8947/2, whereas the new required-point coverage proxy is 41.41%. They are not comparable: the former is the saved local evaluator judgement; the latter derives up to three query-relevant points from frozen evidence and checks answer coverage deterministically. The difference is preserved and flagged for human review rather than reconciled by tuning.
