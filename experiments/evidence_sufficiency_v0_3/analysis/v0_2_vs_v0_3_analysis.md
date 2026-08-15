# V0.2 vs V0.3 analysis

All V0.3 historical-set numbers are `SEEN_REGRESSION`; only the V0.3 cross-validation rows are out-of-fold.

## Seen regression

- v0_2_real_development: accuracy 23/24 (95.8%); sufficient recall 100.0%; false sufficient 1/3 (33.3%).
- v0_2_real_internal_holdout: accuracy 8/8 (100.0%); sufficient recall 100.0%; false sufficient 0/2 (0.0%).
- v0_2_synthetic_development: accuracy 32/36 (88.9%); sufficient recall 75.0%; false sufficient 1/24 (4.2%).
- v0_2_synthetic_holdout: accuracy 24/24 (100.0%); sufficient recall 100.0%; false sufficient 0/16 (0.0%).
- legacy_synthetic_v0_1: accuracy 40/40 (100.0%); sufficient recall N/A; false sufficient 0/40 (0.0%).
- historical_17: accuracy 15/17 (88.2%); sufficient recall 71.4%; false sufficient 0/10 (0.0%).

## Same-set safety comparison

Legacy Synthetic 40 False Sufficient: V0.1 7/40 (17.5%); V0.2 6/40 (15.0%); V0.3 0/40 (0.0%).

## Interpretation

V0.3 Real CV sufficient recall is 73.5%, versus V0.2 Real Development 66.7%; this is a modest recovery but below the 85% calibration target. Synthetic CV Sufficient Control recall is 60.0%, essentially not recovered. The exact old sets improve sharply after fitting all seen rows, but those regression gains are not evidence of generalization.
