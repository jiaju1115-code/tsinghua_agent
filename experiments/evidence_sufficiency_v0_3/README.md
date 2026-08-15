# Evidence Sufficiency V0.3 Calibration

This directory contains an offline calibration/model-selection experiment. It is not a blind evaluation. Every labeled row and every historical regression set is treated as seen data.

## Outcome

`NOT_READY_FOR_NEW_BLIND`

- Unified data: 49 Real ({'EVIDENCE_INSUFFICIENT': 7, 'EVIDENCE_SUFFICIENT': 34, 'EVIDENCE_PARTIAL': 8}) and 98 unique Synthetic rows; 149 raw rows became 147 unique Query+Evidence rows after removing two within-kind duplicates.
- Real 5-fold nested CV: 34/49 accuracy (69.4%), sufficient recall 73.5%, false sufficient 4/15.
- Synthetic 5-fold nested CV: 85/98 accuracy (86.7%), sufficient-control recall 12/20, false sufficient 2/78.
- Final candidate: `v0.3-c`, frozen before historical regression.
- Audit: `PASS`.

## Reproduction order

1. `python scripts/build_unified_calibration_dataset.py`
2. `python scripts/run_v0_3_cross_validation.py`
3. `python scripts/freeze_candidate.py`
4. `python scripts/run_v0_3_regression.py`
5. `python scripts/finalize_v0_3_reports.py`

Do not rerun steps 1–3 and then interpret historical regression as blind performance. No network, retrieval, evidence supplementation, answer generation, or citation generation is part of this experiment.
