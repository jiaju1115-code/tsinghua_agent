# Sufficient-control analysis

Synthetic out-of-fold SUFFICIENT_CONTROL recall is 12/20 (60.0%); 8/20 controls were classified insufficient. All eight misses were direct Sufficient → Insufficient transitions.

The strongest observed pattern is over-conservative separation on controls with multiple extracted points: the current feature model treats point count, evidence shape, lexical support, and requested-attribute overlap as proxies, but it does not perform true semantic entailment. Minimal-point policy therefore did not fully protect controls. This remains a blocking failure.

On seen regression only, V0.2 Synthetic Development improves from 7/12 to 9/12, and the former Synthetic Holdout improves from 5/8 to 8/8. These results are expected to be optimistic because the final model was fitted on all seen calibration rows; readiness is based on out-of-fold results instead.
