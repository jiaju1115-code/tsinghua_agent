# Evidence Gate V0.1 analysis

1. V0 confused topical relevance with answer sufficiency; V0.1 requires point-level evidence coverage.
2. Required-point decomposition is present, but lexical overlap is not sufficient semantic understanding.
3. Multi-part queries are split and scored per point.
4. Wrong-document/concept mismatch checks are explicit and conservative.
5. Navigation-dense evidence is flagged as contamination.
6. False Sufficient: development {'count': 1, 'rate': 0.16666666666666666}; holdout {'count': 0, 'rate': 0.0}; synthetic {'count': 7, 'rate': 0.175}.
7. Over-conservatism: development missed sufficient {'count': 1, 'rate': 0.16666666666666666}; holdout {'count': 0, 'rate': 0.0}.
8. The 33 unreviewed reconciliation rows lack frozen evidence, so they are reported as UNKNOWN rather than fabricated shadow labels.
9. Decision: DO NOT PROMOTE because synthetic false-sufficient rate is material.
