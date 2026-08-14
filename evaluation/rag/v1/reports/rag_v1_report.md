# RAG V1 Report

## Executive decision

**`RAG_V1_RECOMMENDED_RETRIEVER = Dense Retrieval (BAAI/bge-small-zh-v1.5)`**

Dense retrieval is the best default for this 238-document / 717-chunk CPU-only experiment. It has the best MRR (0.808) and Recall@1 (0.727), reaches Recall@5 0.909, averages 8.55 ms/query, and is stable and simple to operate. RRF hybrid reaches the best Recall@5 (0.939) but lowers MRR to 0.781 and Recall@1 to 0.667 while adding a second index and latency. The reranker is both slower and worse on the provisional evaluation set, so it is not recommended.

These metrics are provisional: 28 of 38 queries are `PROVISIONAL_EVAL`, not Gold Evaluation. Five queries with uncertain expected source are excluded from Recall/MRR/Source Hit denominators.

## 1. Frozen corpus integrity

All 238 documents and all 717 frozen RAG V0 chunks remain intact. The audit passed: 717 unique `chunk_id` values, 238 unique sources, all required source/title/category/URL/original-file/text/chunk-index fields present, all original files traceable, all text hashes valid, contiguous per-source chunk indexes, and exact chunk-ID order matching the V0 index. No chunk was edited or re-created.

The rebuilt TF-IDF baseline reproduces the exact V0 Top-5 chunk order on all 10 frozen smoke queries.

## 2. Dense index

Dense embedding construction succeeded with the required official `BAAI/bge-small-zh-v1.5` model at revision `7999e1d3359715c523056ef9478215996d62a620`.

- Local model weights: 95,827,648 bytes; SHA-256 `354763b9b1357bc9c44f62c6be2276321081ed2567773608c0d0785b61d5a026`.
- Embedding matrix: 717 × 512 float32, L2-normalized; cosine-ready validation passed.
- Document build: 40.871 s; 17.54 chunks/s; peak process RSS 781.86 MiB.
- Batch size / max length: 16 / 512.
- Embedding file: 1,468,544 bytes; SHA-256 `6fedbb90ebf69653a8ffd6f8a1381b6ab389fbb66fa1a5558853ed81770e8059`.
- Every row maps to chunk, source, URL, original file, and chunk index in `indexes/dense/row_mapping.jsonl`.

## 3. Evaluation design

The same 38-query set was used for all four retrievers:

- 10 `EXISTING_SMOKE` questions copied verbatim from RAG V0.
- 28 new questions marked `PROVISIONAL_EVAL`.
- 15 requested service categories covered.
- 33 questions have a reliable expected source; five uncertain-source questions are reported but excluded from Recall/MRR/Source Hit.

No query was modified after seeing the retrieval results. Expected sources were determined from corpus inspection; uncertain cases were not guessed.

## 4. Strict horizontal comparison

| Retriever | R@1 | R@3 | R@5 | R@10 | MRR | Category Hit@5 | Source Hit@5 | Evidence Hit@5 | Avg latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF | 0.606 | 0.727 | 0.788 | 0.879 | 0.694 | 0.763 | 0.788 | 0.939 | 3.07 ms |
| Dense | **0.727** | **0.879** | 0.909 | **0.939** | **0.808** | 0.763 | 0.909 | **0.970** | 8.55 ms |
| Hybrid RRF | 0.667 | **0.879** | **0.939** | **0.939** | 0.781 | 0.737 | **0.939** | **0.970** | 14.16 ms |
| Hybrid + reranker | 0.576 | 0.818 | 0.848 | 0.909 | 0.686 | 0.763 | 0.848 | 0.939 | 7,216.13 ms |

Dense provides the largest balanced gain over TF-IDF: +0.121 Recall@1, +0.121 Recall@5, and +0.113 MRR at only +5.48 ms/query. Hybrid adds another +0.030 Recall@5 but loses -0.061 Recall@1 and -0.027 MRR relative to Dense. Therefore the RRF gain is real but narrow and does not justify making Hybrid the default for this corpus.

## 5. CPU performance

Host: Windows 11, Python 3.12.5, PyTorch 2.13.0+cpu, 12 physical / 16 logical CPU cores, 31.73 GiB RAM.

| Component | Average | p50 | p95 | Peak process RSS |
|---|---:|---:|---:|---:|
| TF-IDF query | 3.07 ms | 3.01 ms | 4.22 ms | 484.74 MiB |
| Dense query | 8.55 ms | 8.64 ms | 9.57 ms | 489.00 MiB |
| Hybrid end-to-end | 14.16 ms | 14.10 ms | 16.28 ms | 489.24 MiB |
| Reranker only, 20 pairs | 7,195.02 ms | 7,230.76 ms | 7,951.81 ms | 1,308.30 MiB |
| Hybrid + reranker end-to-end | 7,216.13 ms | 7,254.61 ms | 7,975.61 ms | 1,308.30 MiB |

The official `BAAI/bge-reranker-base` model loaded and ran successfully at revision `2cfc18c9415c912f9d8155881c133215df768a70`; weight SHA-256 is `ced967c45fd1902eb92716c9ceeca7c95a936770ea9db611f5a841b926e33fbd`. It corrected four expected-source ranks, but degraded nine, including dropping one reliable expected source out of Top-10. Its quality fell below all other systems while adding about 7.2 seconds/query and roughly 819 MiB over Hybrid. It is not worth its CPU cost in this configuration.

## 6. What improved, and what still needs lexical retrieval

Nine reliable-source cases ranked better with Dense than TF-IDF. Representative gains:

- `PROV-016` 馆际互借: TF-IDF missed Top-10; Dense ranked the expected source first.
- `PROV-028` 院系单位号/简称/英文名: TF-IDF rank 8; Dense rank 1.
- `RET-01` 本科生学籍、注册与培养规定: TF-IDF rank 6; Dense rank 1.
- `PROV-008` 教工餐厅资料: TF-IDF rank 8; Dense rank 2.
- `PROV-006` 学生社区邮寄地址/邮编: TF-IDF missed Top-10; Dense rank 5.

Four reliable cases still clearly favor lexical retrieval, fewer than the requested five; no fifth case was fabricated:

- `PROV-003` 校内申诉机构: TF-IDF rank 2 vs Dense rank 8.
- `RET-06` 奖助学金办法: rank 1 vs 3.
- `RET-03` 校园网接入/故障: rank 1 vs 2.
- `PROV-025` IEEE APC优惠: rank 1 vs 2.

Exact policy, system, form, acronym, and proper-name queries remain lexical strengths. RRF preserves this safety net, but only one reliable case strictly outranked both component retrievers: `PROV-006`, where Dense rank 5 improved to Hybrid rank 4. That is too little evidence to make Hybrid the default.

## 7. Frozen V0 smoke review

The evidence-level verdict distribution remains **7 pass / 2 partial / 1 fail**; 10/10 are unchanged, 0 improved, and 0 degraded. This does not mean rankings were identical across methods. It means new retrieval cannot overcome the source-evidence ceiling for the three problematic questions:

- `RET-01` remains partial because it is a composite academic-status/registration/training request; Dense finds the regulation, but a single consolidated answer source is still not present.
- `RET-05` remains partial because borrowing, electronic resources, and opening hours span multiple library documents.
- `RET-09` remains fail because no adequate transport source exists.

This separation prevents source gaps from being mislabeled as retriever failures.

## 8. Transport diagnosis

The transport failure is **C. Source Quality Failure**, with query ambiguity secondary. The only five chunks labelled `交通服务` come from three sources: a university-history link page, a hardship-aid regulation mentioning transport allowance, and an unrelated flexible-vision research article. No current source describes shuttle routes, stops, timetables, campus gates, or access routes. Ranking changes cannot solve this. The deferred gap list is recorded without starting any crawl or expansion.

## 9. Recommendation and next gate

Use Dense as the default `RAG_V1_RECOMMENDED_RETRIEVER`. Keep TF-IDF as a transparent fallback/debug retriever and retain Hybrid as an optional high-recall mode for queries where exact service names matter. Do not enable `bge-reranker-base` on CPU in the present setup.

The system is technically ready to enter a **provisional answer-generation evaluation**: corpus integrity, traceability, local indexing, fixed-query retrieval results, and evidence assembly are all available. It is not ready to claim a formally validated RAG V1 or production merge.

The following must wait for Human Audit:

1. Whether the 238 approved documents are factually valid, complete, correctly categorized, and useful for QA.
2. Removal or correction of mislabelled transport sources and any other sampled false positives.
3. Confirmation of category labels used by Category Hit@5.
4. Formal Gold evaluation and human judgement of answer correctness/completeness.
5. Any KB V1 cleaning or production admission decision.

No Prompt, Gold Label, Human Audit artifact, Public Staging data, Restricted candidate, RAG V0 file, or production asset was modified.
