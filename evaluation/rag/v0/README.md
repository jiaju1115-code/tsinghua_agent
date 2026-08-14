# PROVISIONAL_KB_V0

`PROVISIONAL_KB_V0` 是完全独立于 production 的实验知识库。它只读取：

- `staging_public_baseline_v1/public_staging_manifest.xlsx` 中 234 条 approve；
- `restricted_expansion_v1/candidates/restricted_approved_candidates.xlsx` 中 4 条 approve。

它不写入或覆盖旧数据、production、Prompt V3.2，也不绑定任何生成模型。

## 流水线

`source document → validation → normalization → chunking → metadata → embedding → vector index → retrieval → evidence assembly`

- Validation：检查正文文件存在、UTF-8、正文非空，并按既有口径 `sha256(trim + collapse_all_whitespace)` 校验清单哈希；同时记录原始文件字节 SHA-256。
- Normalization：Unicode NFKC、统一换行、压缩行内空白与多余空行；Restricted 捕获中的 `Auth`/`Discovery` 采集说明不进入知识正文。
- Chunking：按段落/句末边界切分，目标最大 800 字符、重叠 120 字符；极短尾块允许与前块合并。
- Embedding：`title + newline + chunk_text` 的中文字符 2–4 gram TF-IDF，L2 归一化，最多 60,000 维。
- Index：SciPy CSR 稀疏矩阵上的精确余弦（归一化向量点积），适合当前 717 个 chunk 的小规模 V0。
- Retrieval：返回 Top-K 的 chunk、source、category、URL、原文件、相似度与正文。
- Evidence assembly：只拼装带来源编号的证据，不调用或绑定生成模型。

## 复建

在 `D:\python_projects\tsinghua_ai` 执行：

```powershell
python -m pip install -r .\data_second\rag_v0\requirements.txt
python .\data_second\rag_v0\scripts\run_all.py
```

单独检索：

```powershell
python .\data_second\rag_v0\scripts\retrieve.py "学生公寓退宿怎么办？" --top-k 5
```

`run_all.py` 会重新生成已知产物，并在最后运行索引完整性检查。它不会修改两个输入目录。

## 目录

- `config/rag_v0.json`：唯一运行配置。
- `scripts/`：构建、检索、smoke test、完整性验证和总入口。
- `knowledge_base_manifest/knowledge_base_manifest.jsonl`：238 条逐条验证与来源追溯。
- `normalized_documents/`：238 个规范化文本副本，文件名等于 source_id。
- `chunks/chunks.jsonl`：717 个 chunk 及完整元数据。
- `vector_index/`：稀疏向量、vectorizer、chunk 顺序与索引元数据。
- `retrieval_test_cases/`：10 个固定测试问题。
- `retrieval_results/`：逐题 Top-5、证据组装、脚本指标与内容观察。

## 设计边界

V0 使用成熟、无网络运行依赖的稀疏向量基线，而非语义 dense embedding。执行中曾验证 `BAAI/bge-small-zh-v1.5` 仓库 commit `7999e1d3359715c523056ef9478215996d62a620`，但 96 MB 权重下载两次停滞，故没有声称 dense index 成功，也没有以随机向量替代。后续网络/环境稳定时，可新增独立 dense embedding backend 做 A/B 检索评估；生成模型仍应保持解耦。

本库是临时实验资产。Human Audit 未完成不阻塞 V0，但正式 KB V1 必须按人工结果清理；RAG 收录不代表对应文本自动具备训练许可。
