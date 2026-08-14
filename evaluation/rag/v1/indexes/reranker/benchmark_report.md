# Reranker CPU Benchmark

- Status: **PASS**
- Model: `BAAI/bge-reranker-base`
- Revision: `2cfc18c9415c912f9d8155881c133215df768a70`
- Weight SHA-256: `ced967c45fd1902eb92716c9ceeca7c95a936770ea9db611f5a841b926e33fbd`
- Input: Hybrid Top-20 query/document pairs; final Top-10.
- Evaluation queries: 38, identical to the other retrievers.
- Pure reranking: average 7,195.02 ms; p50 7,230.76 ms; p95 7,951.81 ms.
- End-to-end Hybrid + reranker: average 7,216.13 ms; p50 7,254.61 ms; p95 7,975.61 ms.
- Peak process RSS: 1,308.30 MiB.
- Quality: Recall@5 0.848, MRR 0.686. This is below Hybrid (0.939 / 0.781) and Dense (0.909 / 0.808).

Although the cross-encoder corrected four expected-source ranks, it degraded nine and dropped one reliable expected source out of Top-10. On this CPU-only machine and this provisional evaluation set, the quality/cost trade-off is negative. The model is retained for reproducibility and analysis but is not recommended for the default architecture.
