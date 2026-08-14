# training_v0

这是下一阶段 SFT / domain adaptation 的**空管线骨架**，不是已启动的训练实验。

当前 Base Model 决策：条件性推荐 `Qwen/Qwen3.5-2B-Base`，固定 revision `b1485b2fa6dfa1287294f269f5fb618e03d52d7c`。正式训练前必须在目标 CUDA 机器完成权重级 benchmark 与 LoRA save/reload smoke。

## 数据隔离

- `data/train/` 只接收许可清晰、人工确认、专门构造的训练样本。
- 禁止复制 Evaluation / Gold Set。
- 禁止直接复制 `rag_v0` chunks 作为训练集。
- 禁止使用 `human_audit` 的未完成人工字段推断标签。
- `model_selection/heldout/heldout_index.json` 中的 10 个 source_id 永久排除。
- 禁止凭据、Cookie、Token、storage state 和个人敏感信息。

本目录暂不包含训练数据、adapter 或 checkpoint，也没有启动长时间训练。

