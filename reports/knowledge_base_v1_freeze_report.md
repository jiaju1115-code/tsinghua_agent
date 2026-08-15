# Knowledge Base V1 Consolidation + RAG Retrieval V1 Freeze Report

> 执行日期：2026-08-15（Asia/Shanghai）  
> Git 审计快照：`4aee0de85b3fd57fd5ffdb66ec9f5ca9e9e655de` / `main`（工作树原本非 clean；本轮以逐文件 hash 而非 clean 假设完成输入不变性审计）  
> 本轮未重抓网页、未调用 LLM 审核 corpus、未启动 E2E、未训练 Evidence Sufficiency，未修改历史 frozen 数据、Prompt、人工标注或历史实验结果。

## 1. Final Corpus Decision

唯一正式 runtime corpus 为 **Canonical Knowledge Base V1**：`data/03_knowledge_base/v1/`。

| 口径 | Public | Restricted | Total |
|---|---:|---:|---:|
| 候选宇宙 | Public Expansion V2：165 | Restricted V1：4 | 169 |
| 纳入 V1 runtime | 119 | 3 | **122** |
| runtime 外排除（含 unresolved exclusion） | 46 | 1 | **47** |
| 其中 UNRESOLVED 且 fail-closed 排除 | 8 | 0 | **8** |

Public 仅在已有 V3.2/quality gate 结论同时满足 `approve`、`candidate_approved`、`quality_gate_pass`、`detail_content`、`evergreen`、正文存在、URL/正文哈希未重复时纳入。Restricted 还必须在候选和 consolidated safety gate 中均为 `safe_general_content`。运行时 corpus 中 review/reject/unresolved 条目数为 **0**。

排除理由来自既有 metadata，不含新的模型复审：`thin_content` 28、`template_polluted` 14、`review` 8、`unknown time status` 9、`historical_but_valuable` 3、`reject` 3、`expired` 1、`active_time_bound` 1（同一 source 可有多个理由）。每个决定均在 `audit/eligibility_decisions.jsonl` 留痕。

与历史口径的关系：

- 历史 RAG V0/V1 的 `PROVISIONAL_KB_V0` 为 238 sources / 717 chunks，其中 public staging 仍含 `pending_human_check`；它保留为 legacy/provenance，不是 V1 runtime 依赖。
- Public Expansion V2 的 165 条 canonical pool 中，V3.2 机器结论为 154 approve；V1 再按已有质量、时效和安全 metadata fail-closed，实际只收纳 119 条 public source。
- Restricted V1 的 4 条既有 approved candidate 中，1 条 `historical_but_valuable` 且无明确有效期，因此不进入 runtime；其余 3 条满足现有安全和质量结论。

现有 49 条 human check 的人工标签只称为 `human_reference`，不是绝对 gold truth。其分歧 URL 已参与冲突检测；未发现与最终 119 条 public runtime source 的直接 normalized-URL 冲突。人工文件仍保持原路径与原始内容。

## 2. Canonical Knowledge Base

正式位置与版本：`data/03_knowledge_base/v1/` / `KNOWLEDGE_BASE_V1`。

```text
data/03_knowledge_base/v1/
├── README.md
├── sources/{public,restricted}/
├── chunks/chunks.jsonl
├── index/{document_embeddings.npy,row_mapping.jsonl,index_manifest.json,model/}
├── manifests/{source_manifest,chunk_manifest,source_to_chunk_mapping}.jsonl
├── provenance/{source_provenance.jsonl,normalized_source_text/}
├── config/{chunking_v1,retriever_v1}.json
└── audit/{eligibility_decisions,knowledge_base_v1_freeze,rag_retrieval_v1_freeze,...}.json
```

每个 source 有稳定 `canonical_source_id`（`KBV1-PUB-*` 或 `KBV1-RES-*`），canonical copy 与原始 source byte hash 一致。新目录与 staging 解耦；未来 runtime 只读取此目录。

## 3. Provenance

`manifests/source_manifest.jsonl` 与 `provenance/source_provenance.jsonl` 为每个 runtime source 记录：canonical/original ID、source type、title、URL/domain、public/restricted、category/content type、review status、time metadata、inclusion reason、原始/新文件相对路径、declared content hash、原始文件 SHA256、canonical source SHA256，以及审核/quality/safety artifact 路径。

因此可回溯：原始正文 → V3.2 审核结果 → 质量/安全结论 → canonical source。该链路不把 `human_reference`、`adjudicated_reference`、proxy 或 automated review 误称为 gold。

Source manifest SHA256：`ad9754265f5ebf9778b1e732acd0146f96e3a0e2fc1f54190dcdd687ed86ee74`。

## 4. Chunk Freeze

- Chunk count：**488**；chunks SHA256：`45b2f9c1eda6fd7e0e2deca1d8e1e2c4ae2075648bc74dfda5ab9f167abc6535`。
- Stable ID：`KBV1-CHUNK-<original-source-id>-<0001...>`；每条都关联 canonical source ID、原始 source ID、顺序、字符边界、正文 SHA256 与 normalized source SHA256。
- 规则：NFKC、换行标准化、水平空白整理、连续空行折叠、移除 restricted 获取元数据行；最大 800 字符、overlap 120、最小 80，优先在段落/句末边界切分。
- Chunk config SHA256：`7dd4c3615679e2ce56fe394bedfb121c0b106e00d61945384f1f04b7487119ec`。
- `source_to_chunk_mapping.jsonl`、`chunk_manifest.jsonl` 与原始 chunks artifact 已验证一一对应。

旧 717 chunks 未被继承；它们仅作为历史比较资产。

## 5. Index Freeze

新 index 为 488 行 Dense flat L2-normalized embeddings：`index/document_embeddings.npy`。

- Index/embedding SHA256：`369edb25725c790f832883dedc82b8eb4d42304e48ed00d8568a2d0fdc852888`。
- 行映射：`index/row_mapping.jsonl`，embedding 行、chunk ID、canonical source ID 的顺序一致。
- 模型：`BAAI/bge-small-zh-v1.5`，revision `7999e1d3359715c523056ef9478215996d62a620`；本地权重副本 SHA256：`354763b9b1357bc9c44f62c6be2276321081ed2567773608c0d0785b61d5a026`。
- pooling：CLS `last_hidden_state[:,0]`；相似度：L2-normalized vector dot product（cosine）；所有 embedding norm 校验通过。

## 6. Retriever Freeze

`RAG_RETRIEVAL_V1` 的唯一配置为 Dense / BGE-small-zh-v1.5 / Top-K=5：

- 中文 query instruction：`为这个句子生成表示以用于检索相关文章：`
- bilingual expansion：`false`
- max length：512；batch size：16
- document input：`title + newline + chunk_text`
- tie-breaking：score 降序，再按 chunk ID 升序

配置文件：`data/03_knowledge_base/v1/config/retriever_v1.json`，SHA256 `2b091a71f3d318023584aaad903db2eeac14b0562dd7e62b3fa91dbd4f3dec6b`。

运行时 adapter：`src/retrieval_v1/adapter.py`。输入 `query, case_id`，输出 `query, case_id, retriever_version, corpus_version, ordered_top5_chunks, source_ids, chunk_ids, scores, latency_ms, error`。它校验两个 freeze manifest sidecar、retriever config 与 chunks/index/model hash；它没有 staging、在线搜索、Evidence Sufficiency 或答案生成依赖。

## 7. Path Cleanup

已修复的 active path：

- 新 runtime adapter 从项目根目录相对定位 `data/03_knowledge_base/v1/`，不含 `D:\python_projects\...` 硬编码。
- 新构建器与 regression/integrity 工具只使用 `pathlib` 和 root-relative path。
- `docs/project_file_map.md` 已声明 V1 是唯一正式 KB/RAG runtime，并将 staging、RAG V0/V1 与旧 answer/citation evaluation 标为 legacy/provenance。

仍保留的 legacy path：历史脚本、报告、manifest 中的 `data_second` 字样未被改写，因为它们是历史证据；V1 runtime 不读取它们。

## 8. Exclusion Registry

已生成 `evaluation/e2e/v1/benchmark/exclusion_registry.jsonl`：

- 记录数：1,425
- 唯一 raw query：182；唯一 normalized query：182
- 来源文件集合：45
- SHA256：`2c116fc91c789193f01764481eab1aa148aadcbe533ee2c2e84a55734827f51e`

范围涵盖 Router frozen/blind/shadow、E2E12、RAG V0/V1、Answer Generation、Citation、Evidence Sufficiency V0.1–V0.4、Prompt calibration、synthetic variants、human check JSON 和历史错误分析中可识别的 query。每条保存 source dataset、query ID、raw/normalized query 及哈希、source/evidence IDs、Query+Evidence canonical hash、可确定的 template family 和排除原因。

这只是未来 held-out benchmark 的排除清单；本轮没有创建任何新的 50 条 benchmark，也没有进行正式 E2E 评估。

## 9. Regression Diagnostic

历史 `evaluation/rag/v1/evaluation/eval_queries.jsonl` 的 38 条 query 仅被用于功能回归：

- processed：38/38
- retrieval errors：0
- output-schema failures：0
- status：PASS

见 `audit/regression_diagnostic.json`。该诊断未计算 R@K、MRR、正确率或任何新模型效果，不能被解释为 held-out 或性能提升。

## 10. Integrity

以下检查均为 PASS：

- 122 个 canonical copy 与原始 source byte hash 一致，且 source manifest/count 与 freeze 一致。
- 488 个 chunk ID 唯一；每个 chunk text SHA256、source→chunk mapping、row mapping 和 embedding row count 一致。
- embedding L2 norm、index SHA256、retriever config hash、KB/RAG freeze sidecar 均一致。
- 历史输入不变性：对 Public Expansion、Restricted Expansion、Human annotation、staging、RAG V0/V1、Answer/Citation、Prompt、Router/E2E/Evidence 等 **2,875** 个历史文件在构建前后和最终再验中均无 hash 变化。

最终完整性报告：`audit/final_integrity_report.json`，SHA256 `0cdbc938c55e7ed5714640a1315010468a85cb622212bd4befb0407d46d7f15c`。

## 11. Remaining E2E Blockers

本轮只解决 Corpus/Chunk/Index/Retriever 基础层。以下问题仍未解决，不能因 Retrieval V1 freeze 而被视为完成：

- Evidence Sufficiency runtime 与真实 semantic entailment。
- Citation mapping 的人工校准与 runtime citation/support gate。
- Unsupported-claim、faithfulness、correct-refusal 的统一 runtime policy。
- 独立 held-out 50 条 E2E benchmark、reference adjudication、泄漏审计的执行。
- 统一的 E2E orchestrator、指标定义与双人/裁决人工评估。

## 12. Final Status

`KNOWLEDGE_BASE_V1_FROZEN`  
`RAG_RETRIEVAL_V1_FROZEN`

KB freeze SHA256：`e54315552f65458570ca9d4108e8e592e8638a331f21012e92e120f87b0edf8b`。  
RAG freeze SHA256：`37364781a7061fd10cdf0fd75d29b22c620999e4afe24aabab6357318766e76d`。

后续 E2E V1 只能读取本 bundle。不得原地修改 Knowledge Base V1 或 RAG Retrieval V1；新增 source、改变 chunking/index/model/config 均必须创建 Knowledge Base V2 与 RAG Retrieval V2。
