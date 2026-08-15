# Wrong-document analysis

- V0.2 former Synthetic Holdout: 0/3.
- V0.3 Synthetic out-of-fold: 16/19 (84.2%).
- V0.3 exact former Synthetic Holdout, `SEEN_REGRESSION`: 3/3 (100.0%).

Requested-attribute and document-shape features materially improve wrong-document rejection, but three out-of-fold misses remain: two False Sufficient and one Insufficient → Partial. The requested-attribute check is therefore useful but not yet reliable enough on its own.
