# Base Model Selection Report

日期：2026-08-13  
项目目标：为清华校园中文智能体选择可训练、可复现、易与 RAG 解耦集成的 pretrained/base 底座。  
阶段约束：只允许模型加载、benchmark 与极小 LoRA smoke；未启动长时间训练。

## 决策摘要

**推荐 Base Model：`Qwen/Qwen3.5-2B-Base`，但属于“完成官方核验与 tokenizer 实测、等待目标 CUDA 机器完成权重级 smoke 后落地”的条件性推荐。**

**第二候选：`Qwen/Qwen3.5-4B-Base`。** 只有在获得至少 24 GiB、建议 32 GiB NVIDIA VRAM，并完成同口径 loss / throughput / LoRA smoke 后才值得升级。

当前机器不能真正训练推荐模型：PyTorch 为 CPU-only，没有 CUDA GPU。正式训练方法推荐 **LoRA（BF16）**，不推荐 Full Fine-tuning；QLoRA 可作为显存紧张时的备选，但由于本机无法验证 bitsandbytes/CUDA 与 Qwen3.5 新架构组合，不能在本阶段把 QLoRA 宣布为已验证方案。

## 证据边界

已完成：

- 5 个官方候选仓库的 model card、base/pretrained 身份、许可、门控、revision、权重大小与上下文核验。
- Qwen 2B / 4B / 9B 固定 revision 的 tokenizer 实测。
- 固定 10 条 Public source 的校园 held-out 隔离，记录 source_id 与 hash；这些 source 永久排除后续训练实验。
- 对 Gemma 两个官方对照发起实测，真实记录 401 gated。
- 对 Qwen3.5-2B-Base 发起两次权重下载：Xet 通道无字节进展；官方非 Xet HTTP 通道到 10 MiB 后停止变化。进程在有界无进展窗口后终止。

未完成且未伪造：

- Qwen3.5-2B 的 held-out perplexity/loss、completion tokens/s、内存峰值。
- LoRA forward/backward/save/reload。
- Qwen 4B/9B 权重级横测。
- Gemma tokenizer/权重级横测。

因此本报告给出的是架构与工程选型结论，不声称已完成公平的全模型性能横测。原始运行记录见 `base_model_benchmark.jsonl`。

## 硬件约束

当前环境：Windows 11、i7-1360P、31.72 GiB RAM、无 NVIDIA GPU、PyTorch 2.13.0+cpu。详细组件与环境冲突见 `hardware_report.md`。

现实显存估计（需在目标机实测校准）：

| 模型 / 方法 | 估计要求 | 判断 |
|---|---:|---|
| Qwen3.5-2B BF16 inference | 约 5–7 GiB | 单卡可行 |
| Qwen3.5-2B BF16 LoRA | 最低约 16 GiB；24 GiB 更稳健 | 推荐路径 |
| Qwen3.5-2B QLoRA | 约 8–12 GiB | 理论可行，尚未验证 |
| Qwen3.5-2B Full FT | 建议 48 GiB 以上并做分布式/优化器剖析 | 不推荐 |
| Qwen3.5-4B BF16 LoRA | 最低约 24 GiB；32 GiB 更稳健 | 算力升级后评估 |
| Qwen3.5-9B PEFT | 需更高显存与部署预算 | 当前排除 |

估计包含模型、激活、梯度/adapter 与运行时开销，不能替代目标 sequence length / batch size 下的 `max_memory_allocated` 实测。

## 候选比较

### Qwen/Qwen3.5-2B-Base — 推荐

- 官方 model card 明确这是 pre-trained only 权重，Apache-2.0，非 gated；原生 262,144 context，并把控制 token 设计为便于 LoRA-style PEFT。
- 中文/多语言覆盖与本项目最匹配；校园 held-out tokenizer 为 6,135 tokens / 5,522 中文字符，约 **1.111 tokens/中文字符**。
- 官方 BF16 权重约 4.55 GB，是 Qwen3.5 第一组中唯一值得在当前 32GB RAM 主机尝试完整 CPU smoke 的候选。
- 风险：Qwen3.5 是带视觉编码器的混合架构；模型卡称 2B，但实际权重和大词表会增加内存/LoRA target-module 风险。完整权重 smoke 因下载停滞未完成。

官方资料：[Qwen3.5-2B-Base model card](https://huggingface.co/Qwen/Qwen3.5-2B-Base)。

### Qwen/Qwen3.5-4B-Base — 第二候选

- 同为官方 pre-trained only、Apache-2.0、262,144 context，中文与 RAG 场景匹配。
- 与 2B 使用同 tokenizer，因此本轮 token 效率相同。
- 两个 BF16 shard 合计约 9.32 GB；HF 页面同时显示 nominal 4B 与约 5B 参数信息，报告保留这一差异，正式训练应以实际 config/parameter count 为准。
- 当前无 GPU，无法公平验证其训练和推理成本；不能仅凭更大参数量替代 2B。

官方资料：[Qwen3.5-4B-Base model card](https://huggingface.co/Qwen/Qwen3.5-4B-Base)。

### Qwen/Qwen3.5-9B-Base — 当前排除实测

- 官方、Apache-2.0、pre-trained only、长上下文，理论能力上限高。
- BF16 shard 合计约 19.31 GB；当前 CPU-only 环境不具备现实训练或公平吞吐测试条件。
- 如果未来有 48–80 GiB 级 GPU 或多卡，并且 4B 相对 2B 已显示清晰领域收益，才值得重新进入候选。

官方资料：[Qwen3.5-9B-Base model card](https://huggingface.co/Qwen/Qwen3.5-9B-Base)。

### google/gemma-3-1b-pt — 对照受阻

- Google DeepMind 官方 pretrained model，约 1B，32K context，140+ 语言，Transformers 官方支持。
- Hugging Face 需要先接受 Gemma 使用条款并认证；本机实测得到 401 gated，故无 tokenizer/loss/LoRA 结果。
- Gemma license 与门控增加公开复现摩擦，中文校园适配证据也弱于 Qwen，故不推荐为主底座。

官方资料：[Gemma 3 1B PT model card](https://huggingface.co/google/gemma-3-1b-pt)。

### google/gemma-3-270m — 管线对照受阻

- 官方、资源最低，适合验证训练管线本身。
- 容量过小，不适合作为最终校园中文智能体底座；同样因 Gemma gated/未认证而无法下载。

官方资料：[Gemma 3 270M model card](https://huggingface.co/google/gemma-3-270m)。

## 为什么不是其他模型

- **不是 Qwen 4B/9B**：当前硬件无 CUDA，无法证明 PEFT 可行性和吞吐；更大不自动更适合。
- **不是 Gemma 1B/270M**：受 gated/许可认证阻塞，中文与校园语料适配证据较弱；270M 容量不足。
- **不是 Instruct/Chat/Reasoning 版本**：本阶段目标是可继续训练的 pretrained/base 权重，不能把 post-trained 对话表现混入 Base Model 选型。
- **不是社区 merge/量化衍生模型**：来源、训练历史、可复现性与许可链条不满足本阶段要求。

## 训练方法建议

1. 在独立、锁定的 Linux + CUDA 环境重跑 `Qwen/Qwen3.5-2B-Base` 固定 revision。
2. 先完成 BF16 load、中文/校园 held-out loss、短 completion tokens/s、显存峰值。
3. 用 sequence length 512、micro-batch 1、gradient checkpointing 的 LoRA smoke；验证 forward、backward、save、reload。
4. 只有 smoke 全通过才进入短 SFT pilot；先 LoRA，不做 Full FT。
5. 若 16 GiB 显存不足，再验证 QLoRA；不得只根据理论显存宣布兼容。

## 后续训练数据应该是什么

适合构建：

- 权利与许可明确、版本可追溯、人工确认质量的中文校园任务数据。
- 结构化 SFT 样本：问题、必要上下文、可核验答案、来源元数据、时效标记。
- 若做领域继续预训练，应使用单独许可审查过的校园正文 corpus，并与 SFT、RAG KB、评估集分别建 manifest。
- 训练数据需做去重、PII/凭据清理、时间有效性和部门归属检查。

严禁进入训练：

- Evaluation / Gold Set 及任何人工 Gold Label。
- 本轮 10 个 Base Model benchmark held-out source_id：`STGPUB-0012, STGPUB-0070, STGPUB-0104, STGPUB-0094, STGPUB-0139, STGPUB-0163, STGPUB-0180, STGPUB-0078, STGPUB-0080, STGPUB-0162`。
- 尚未完成 Human Audit 的样本不能因已进入 RAG 而自动成为训练数据。
- Cookie、Token、storage state、密码、个人身份数据。
- Prompt V3.2 的评估输入/历史 AI 判断，不得混入训练以污染后续评估。

## RAG 兼容性

Embedding 模型与生成模型必须保持解耦。Qwen3.5-2B 只作为未来 generator 候选；PROVISIONAL_KB_V0 的检索器与向量索引可独立替换和评估。任何 chunk 都应以 evidence 形式注入，并保留 URL/source_id，模型不承担事实数据库职责。

## 算力增加时是否升级

有 24–32 GiB VRAM 时，值得把 4B 纳入与 2B 的同口径 A/B，但升级前提是 4B 在校园 held-out loss、SFT 任务和部署延迟上提供实质收益。有 48–80 GiB 或多卡时可以研究 9B；在数据只有数百条且 RAG 承担事实检索的阶段，盲目升级 9B 的收益很可能不抵训练/部署成本。

## 产物

- `hardware_report.md`
- `official_model_metadata.json`
- `base_model_scorecard.xlsx`
- `base_model_benchmark.jsonl`
- `heldout/heldout_index.json`
- `scripts/prepare_heldout.py`
- `scripts/benchmark_model.py`

