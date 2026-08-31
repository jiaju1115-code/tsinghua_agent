# Qwen3 Grounded Natural LoRA V1

## 决策

当前生产候选**不应立即微调**：知识正确性主要由 RAG、metadata 和 Evidence Gate 决定，微调不能替代知识库；仓库里的旧 Pilot LoRA 面向 Qwen2.5-1.5B，不能挂到当前 Qwen3-4B。旧评测也显示收益主要集中在格式遵循，尚不足以证明当前校园问答质量提升。

这套资产用于下一阶段的受控实验：让 Qwen3 学习“只根据输入 facts 自然改写并标注 [F#]”，而不是记忆会过期的校规。数据由当前公开服务库确定性生成，train/validation 按 source_id 隔离，任何门户内容、上传文件和评测题均不会进入训练集。

## 使用

先重建并检查数据：

```powershell
python scripts\build_qwen3_grounded_sft_v1.py
cd training\qwen3_grounded_lora_v1
python validate_dataset.py
```

在 Linux NVIDIA GPU 服务器上安装 `requirements.txt` 后运行：

```bash
bash run_train.sh
```

默认使用 `Qwen/Qwen3-4B` 4-bit QLoRA。GGUF 文件不能直接用于 Transformers LoRA 训练；训练机需下载相同 Qwen3-4B 的 Hugging Face 基座。训练产物只保存 adapter，不会自动连接到 TsingAsk runtime。

训练前后分别运行同一验证集，输出 citation、数字越界和 PARTIAL 说明指标：

```bash
python evaluate_adapter.py --output outputs/base_evaluation.json
python evaluate_adapter.py --adapter outputs/adapter --output outputs/adapter_evaluation.json
```

## 接入门槛

只有在独立留出集上同时达到以下条件才考虑合并/量化：引用格式通过率不低于 98%，新增数字/日期为 0，PARTIAL 限制说明通过率不低于 95%，校园 RAG 正确性与拒答/追问指标不低于基座，且自然度盲评显著更好。未达到门槛时继续使用当前基座和 prompt，不部署 adapter。
