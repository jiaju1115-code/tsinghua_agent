# Readiness for new blind

`NOT_READY_FOR_NEW_BLIND`

Blocking evidence:

- Real CV Sufficient Precision 86.2%, Recall 73.5%, False Sufficient 4/15 (26.7%). All miss the suggested calibration targets.
- Real Partial recall is 37.5%; the three-class boundary is not stable on real samples.
- Synthetic CV Sufficient Control recall is 12/20 (60.0%), with eight controls misclassified insufficient.
- Wrong Document and Partial Coverage improve substantially, but they do not offset the control and Real-boundary failures.
- The implementation uses an overlap/shape proxy rather than true semantic entailment and does not explicitly emit optional support points.

Single next issue: stabilize the **Real Partial/Insufficient/Sufficient boundary with a faithful semantic-support representation**, while preserving sufficient recall. Do not acquire a new blind set or start another version until this is resolved in calibration.
