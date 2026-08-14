# Citation Pipeline V2

Frozen post-generation citation mapping over the 38-question A baseline. V2 reuses V1 claims and the original Dense Top-5, replaces whole-chunk matching with claim-aware evidence spans, adds conservative normalization, and optionally gates candidates with the already-local pretrained `BAAI/bge-reranker-base`.

No answer generation, training, corpus modification, retrieval expansion for official metrics, or external API is used.

## Rebuild order

```powershell
python data_second/citation_pipeline_v2/scripts/freeze_inputs_v2.py
python data_second/citation_pipeline_v2/scripts/run_v2.py
python data_second/citation_pipeline_v2/scripts/diagnose_and_report.py
python data_second/citation_pipeline_v2/scripts/finalize_metadata.py
node data_second/citation_pipeline_v2/scripts/build_workbooks.mjs
python data_second/citation_pipeline_v2/scripts/final_audit.py
```

The official V2 metrics only use the original per-question Dense Top-5. Full-corpus retrieval is diagnostic and cannot add citations or change official coverage/compliance.

