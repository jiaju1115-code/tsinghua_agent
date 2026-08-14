# RAG V1

RAG V1 compares four retrievers over the frozen RAG V0 corpus: TF-IDF, BGE dense retrieval, RRF hybrid retrieval, and RRF plus BGE cross-encoder reranking. It does not modify RAG V0, production data, Prompt V3.2, Human Audit, Public Staging, or Restricted candidates.

## Frozen inputs

- Corpus: 238 source documents.
- Chunks: 717 rows from `../rag_v0/chunks/chunks.jsonl`.
- Frozen smoke set: the ten RAG V0 questions, copied without edits.
- Additional questions: 28 rows marked `PROVISIONAL_EVAL`; they are not Gold Evaluation.

## Rebuild

Run from the project environment with Python, PyTorch CPU, Transformers, SciPy, scikit-learn, joblib, PyYAML, psutil, and the bundled artifact-tool Node runtime available:

```powershell
python .\scripts\audit_chunks.py
powershell -ExecutionPolicy Bypass -File .\scripts\download_dense.ps1
python .\scripts\download_reranker_ranges.py
python .\scripts\build_indexes.py
python .\scripts\evaluate.py
python .\scripts\analyze_results.py
```

Then build the two Excel artifacts with the bundled Node runtime and `NODE_PATH` pointing to its `node_modules`:

```powershell
node .\scripts\build_eval_workbook.mjs
node .\scripts\build_smoke_comparison_workbook.mjs
```

Model revisions, RRF parameters, batch sizes, and input paths are frozen in `config/retrieval.yaml`. Both model download scripts use official Hugging Face files, fixed revisions, byte-length validation, and SHA-256 validation. No external embedding, reranking, or LLM API is called.

## Main artifacts

- `audit/chunk_integrity_report.json`: frozen-chunk gate.
- `indexes/tfidf/`: exact sparse cosine baseline and V0 reproducibility check.
- `indexes/dense/`: local normalized embeddings plus row-to-source mapping.
- `indexes/hybrid/`: RRF configuration and metrics.
- `indexes/reranker/`: local model/cache metadata and CPU benchmark.
- `evaluation/rag_v1_eval_set.xlsx`: 38-query evaluation set.
- `evaluation/results_*.jsonl`: per-query Top-1/3/5/10 results.
- `evaluation/metrics.json`: quality and CPU latency metrics.
- `evaluation/v0_vs_v1_smoke_comparison.xlsx`: frozen ten-query comparison.
- `reports/`: dense index, transport gap, case analysis, and final RAG V1 report.

Every returned chunk retains `chunk_id`, `source_id`, title, category, URL, original file, chunk index, and text preview. Dense rows are mapped in `indexes/dense/row_mapping.jsonl`; hybrid results retain both component ranks/scores and the final RRF score.
