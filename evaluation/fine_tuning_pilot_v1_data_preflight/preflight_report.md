# Pilot V1 Data Rebalancing Preflight

The formal pool is the hash-registered 841-row V1.2 family files; Pilot V0 consumed the derived 757-row train split with 84 validation rows. All source artifacts remain unchanged.

Proposed KEEP: 422; DROP_FROM_V1_SAMPLING: 419; accepted-data gap to 1200: 778; candidate acquisition estimate: 1947-3112 using a 25-40% acceptance band around the historical 28.85% rate.

Programmatic math: keep 120/300 and downsample 180 through template-diverse deterministic selection. Other math: keep 60 and downsample 239.

BOTH_FAIL sanity sample: 24 cases. Case-level counts: {'EVALUATOR_FALSE_NEGATIVE_RISK': 6, 'TRUE_CAPABILITY_FAIL': 14, 'FORMAT_ONLY_FAIL': 4}. Evaluator false-negative risk: `HIGH`; `DO_NOT_INTERPRET_RAW_PASS_RATE_AS_PURE_REASONING_ABILITY`. Evaluator overoptimization risk: `MODERATE`.

Evaluation protection: exact/normalized overlap 0, suspicious near duplicate 0.

Training parameters should remain frozen for the first composition-only Pilot V1 experiment.

Decision: `READY_FOR_HF_DATASET_DISCOVERY`. This authorizes dataset discovery only, not download, dataset construction, or training.
