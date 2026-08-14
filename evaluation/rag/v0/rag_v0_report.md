# PROVISIONAL_KB_V0 Report

## 结论

Track B 已完成一个可重建、与 production 隔离、生成模型解耦的 Retrieval V0。238/238 条 approve 数据通过入库前文件存在、既有哈希口径、UTF-8 与正文非空检查；共生成 717 个 chunk。索引后完整性检查为 `PASS`。

## 入库与追溯

- Public Staging：234/234 入库。
- Restricted approve：4/4 入库。
- 校验拒绝：0。
- Chunk：717；Public 670，Restricted 47。
- Chunk 字符数：最小 97，平均 658.2，最大 868（短尾合并所致）。
- 每个 chunk 均含 `chunk_id, source_id, title, url, category, source_type, original_file, text, chunk_index`；717/717 保留 URL 和原文件路径。
- 规范化正文按 source_id 独立保存，可由 chunk → source_id/original_file → 原始网页正文回溯。

逐条证据见 `knowledge_base_manifest/knowledge_base_manifest.jsonl`，构建后校验见 `knowledge_base_manifest/post_build_validation.json`。

## Embedding 与索引

- Backend：scikit-learn character n-gram TF-IDF（2–4 gram，L2，60,000 维）。
- Index：SciPy CSR flat cosine；717 × 60,000，556,509 个非零值。
- Embedding matrix SHA-256：`be34ad63d1a14c42468565ded910beef56524cb3932635b75ab314836c5f708b`。
- 构建环境：CPU；本次 embedding/index 构建约 1.4 秒。
- 选择理由：238 文档/717 chunk 属于小规模语料，精确稀疏余弦简单、成熟、稳定、无原生 ANN 依赖，适合作为 V0 retrieval 基线。

曾尝试加载锁定 commit 的 `BAAI/bge-small-zh-v1.5`。模型元数据/tokenizer 可访问，但 96 MB safetensors 权重两次下载均停滞，未得到可用 dense 权重。因此本轮明确降级为真实 TF-IDF 向量基线；没有随机向量、伪造 embedding 或虚构 dense benchmark。

## Retrieval smoke test

- 固定问题：10；每题 Top-5。
- 脚本启发式：keyword-hit@5 = 10/10；category-hit@5 = 9/10；平均检索调用约 0.001 秒（不含进程启动）。
- 内容观察：pass 7，partial 2，fail 1。
- 明确失败：交通问题没有找到校园交通/校车资料；现有“交通服务”类别的 3 条正文内容也暴露出标签/语料质量问题。
- 部分覆盖：教务学籍复合问题、图书馆复合问题能找到相关材料，但 Top-5 未覆盖全部意图。

逐题完整 chunk、source、category、similarity score 和 evidence assembly 位于 `retrieval_results/retrieval_smoke_results.jsonl`；内容观察位于 `retrieval_results/retrieval_smoke_review.md`。

## 数据隔离与限制

- 未读取或使用 Evaluation/Gold Set；未把 Human Audit Sample 当训练或检索标签。
- 未修改 Prompt V3.2、历史结果、两个输入目录或 production。
- 未调用第三方大模型 API。
- 未把 Cookie、Token、storage state、密码或浏览器凭据复制到 `rag_v0`。
- Knowledge Base 身份不等于 Training Data 身份；本轮没有构建训练集。
- V0 结果只证明本地检索链路可运行。进入 RAG V1 前应补充人工 relevance 判定、改写/多意图查询测试，并在 Human Audit 结果回来后清理正式 KB。
