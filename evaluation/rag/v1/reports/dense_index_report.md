# Dense Index Report

- Status: **PASS**
- Model: `BAAI/bge-small-zh-v1.5`
- Revision: `7999e1d3359715c523056ef9478215996d62a620`
- Local weights SHA-256: `354763b9b1357bc9c44f62c6be2276321081ed2567773608c0d0785b61d5a026`
- Embedding rows × dimension: `717 × 512`
- Batch size / max length: `16 / 512`
- Document encoding time: `40.871 s` (17.54 chunks/s)
- Model load time: `0.616 s`
- Peak process RSS: `781.86 MiB` (incremental `401.36 MiB`)
- Normalization: L2; cosine-ready validation: `True`
- Embedding file SHA-256: `6fedbb90ebf69653a8ffd6f8a1381b6ab389fbb66fa1a5558853ed81770e8059`
- Row traceability: `row_mapping.jsonl` maps every embedding row to chunk, source, URL, original file, and chunk index.
- Encoding: documents use `title + newline + text`; queries use the configured BGE Chinese retrieval instruction.
- Full 38-query CPU benchmark: average `8.550 ms`, p50 `8.637 ms`, p95 `9.565 ms`; peak process RSS with the loaded index/model `489.00 MiB`.
