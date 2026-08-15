# Required-point calibration

V0.3 uses punctuation-level Minimal Necessary core extraction and does not expand theoretically useful details into extra core points. Optional details are excluded from the core decision, but the current implementation does **not** emit a separate `OPTIONAL_SUPPORT` list; this is an implementation gap.

Across all 28 out-of-fold errors:

- Suspected over-split: 11 cases. These are missed-sufficient cases with more than one extracted core point; the tag is conservative and not proof that every split was wrong.
- Suspected under-split: 2 cases. These are false-sufficient cases represented by one core point.
- Optional-as-core confirmed by independent re-review: 0. No new adjudication was performed.
- Multi-part query missed-split confirmed: 0.
- Requested-attribute-related wrong-document misses: 3.

Conclusion: decomposition is improved conceptually but not yet stable. It is a material contributor, especially among missed sufficient cases, while the largest system-level bottleneck remains the learned three-class boundary plus weak semantic-support representation. Required-point decomposition alone is not an adequate explanation for the failures.
