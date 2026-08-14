# Citation Pipeline V1

Post-generation citation mapping over the frozen 38-question A baseline. The pipeline does not regenerate or rewrite answers, expand retrieval, or train any model.

Flow: frozen answer → deterministic atomic claims → frozen BGE claim embeddings → Top-5-only evidence rules → citation assignment → marker-only rendering → provisional evaluation.

## Rebuild

Run from the project root in this order:

```powershell
python data_second/citation_pipeline_v1/scripts/freeze_inputs.py
python data_second/citation_pipeline_v1/scripts/run_pipeline.py
python data_second/citation_pipeline_v1/scripts/build_reports.py
node data_second/citation_pipeline_v1/scripts/build_workbook.mjs
python data_second/citation_pipeline_v1/scripts/final_audit.py
```

The workbook builder uses the bundled `@oai/artifact-tool` runtime through the local `node_modules` junction. No external API is called.

## Interpretation

All metrics are `PROVISIONAL_AUTO_EVAL`. Citation Precision Proxy means only that an assigned citation passed the current deterministic rules; it is not human-validated precision. Human fields in the workbook are intentionally blank.
