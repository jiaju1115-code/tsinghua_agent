# Base Model Selection — Hardware Report

检测日期：2026-08-13（Asia/Shanghai）  
检测目录：`D:\python_projects\tsinghua_ai\data_second\model_selection`

## 结论

当前机器没有可用于训练的 CUDA GPU，PyTorch 是 CPU-only 构建。因此本机可以进行 tokenizer、配置兼容性和小模型 CPU smoke test，但不能把任何 1B—9B Base Model 的本地运行等同于“现实可训练”。正式 PEFT 训练必须换到 NVIDIA CUDA 机器；当前阶段不启动长时间训练。

## 硬件

| 项目 | 检测值 |
|---|---|
| OS | Windows 11 10.0.22631 SP0, x86_64 |
| CPU | 13th Gen Intel Core i7-1360P；12 physical / 16 logical cores |
| RAM | 34,070,585,344 bytes（约 31.72 GiB） |
| D: 总空间 | 785,609,912,320 bytes（约 731.65 GiB） |
| D: 可用空间（检测时） | 372,874,141,696 bytes（约 347.27 GiB） |
| NVIDIA GPU | 0（`nvidia-smi` 不存在，PyTorch 也未发现 CUDA device） |
| 单卡 VRAM | N/A |
| GPU 数量 | 0 |

## Python 与训练栈

| 组件 | 版本 / 状态 |
|---|---|
| Python | 3.12.5 |
| PyTorch | 2.13.0+cpu |
| CUDA runtime | 不可用 |
| cuDNN | 不可用 |
| Transformers | 5.13.0 |
| Hugging Face Hub | 1.23.0 |
| PEFT | 0.20.0（本阶段为 LoRA smoke 安装） |
| Accelerate | 1.14.0（本阶段安装） |
| TRL | 未安装；本阶段无需 SFT trainer |
| bitsandbytes | 未安装；Windows CPU 环境不适合验证 QLoRA |
| flash-attn | 未安装；无 CUDA，不能使用 |
| SDPA | PyTorch API 可用，但在当前环境只能走 CPU backend |
| BF16 GPU support | 否 |

## 训练可行性边界

- **本机现实可做**：官方仓库元数据核验、Tokenizer 横测、固定 held-out loss/perplexity、短 completion、CPU 上极小 LoRA forward/backward/save/reload（仅在内存和架构允许时）。
- **本机不现实**：持续 SFT、领域继续预训练、QLoRA CUDA kernel 验证、4B/9B 权重级横测、任何 Full Fine-tuning。
- **建议目标训练机**：Qwen3.5-2B-Base 的 BF16 LoRA 至少 16 GiB NVIDIA VRAM（24 GiB 更稳健）；QLoRA 理论上可压低权重显存，但必须在目标 CUDA/Transformers/PEFT/bitsandbytes 组合上重新 smoke，不能由本机结论担保。
- **Full Fine-tuning**：2B 模型连同梯度、优化器状态和激活通常需要远高于单份权重的显存，建议至少 48 GiB 级别并做显存剖析；本项目当前数据规模和硬件都不支持优先选择 Full FT。

## 环境风险

安装 PEFT/Accelerate 时，`huggingface_hub` 的依赖要求把 `click` 升到 8.4.2，而既有 `anaconda-cli-base 0.6.0` 声明 `click<8.2`。本次模型基准不调用 Anaconda CLI，因此不影响实测，但说明当前 Conda 环境不是隔离、锁定的训练环境。正式训练前应创建独立环境并锁定 Python、PyTorch、CUDA、Transformers、PEFT、Accelerate 与 bitsandbytes 版本。

## 检测方法说明

Windows CIM / `Get-Volume` 在当前沙箱会话因权限或超时不可用，因此 OS/CPU/RAM/磁盘由 Python `platform`、`psutil`、`shutil.disk_usage` 与注册表 CPU 名称交叉获得；GPU 状态由 `nvidia-smi` 不存在和 `torch.cuda.is_available() == false` 双重确认。
