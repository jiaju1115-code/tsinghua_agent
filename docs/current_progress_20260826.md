# 项目当前进度（2026-08-26）

## 结论

当前稳定提交主线为 **Submission Candidate V1**，集成结论为 `SUBMISSION_READY`。主线由 Frozen RAG Runtime V1、Evidence Sufficiency V1、Citation Support V1 与 Natural Uncertainty Runtime Adapter V1 组成。Pilot V1 仍是研究候选，没有进入提交运行时。

## 已完成

- 冻结知识库与检索：Knowledge Base V1 / RAG Retrieval V1 已冻结，包含 122 个来源、488 个分段及离线检索索引。
- 冻结完整性：Windows `core.autocrlf=true` 导致的原始字节差异已完成协调；规范化 LF 哈希、Git blob 与原冻结哈希一致，结论为 `FROZEN_INTEGRITY_CONFIRMED`。
- 统一运行时：`src/runtime_v1/` 提供 Submission Candidate V1 的用户侧入口，并通过 Frozen Bundle V1.1 的跨平台加载器验证冻结资产。
- 自然不确定性表达：确定性回归 30/30、运行时适配 smoke 6/6；记录中的不支持校园事实率为 0，引用完整性为 1.0。
- 最终集成门：Runtime / Answer / Prompt 测试 27 项通过；最终集成决策为 `SUBMISSION_READY`。
- 演示验证：15/15 个问题完成全链路，无 `RUNTIME_ERROR`；预期行为符合率 0.8，回答案例引用覆盖率 1.0，结论为 `DEMO_READY_WITH_LIMITATIONS`。
- 训练数据候选：Pilot V1 最终训练包为 1080 条训练、120 条验证、53 条余量；完整性、许可证、来源与泄漏检查均通过。
- Pilot V1 评估：General V0.1 上由 Pilot V0 的 30/100 提升至 32/100，相对 Pilot V0 有 5 个真实改进、3 个真实回退，结论为 `VALIDATED_WITH_MODEST_GAIN`。
- 动态知识与检索：Dynamic Campus、Dynamic Retriever、Core + Dynamic fusion 均已形成候选、shadow 与诊断资产，但没有进入生产/提交主线。
- 平台参赛草稿：本地额外生成了清园通极速知识库导出包与 Coze Agent 配置辅助资产；它们不改变冻结 Submission Candidate V1 的边界。

## 当前运行入口

本地交互：

```powershell
python scripts/chat_submission_candidate_v1.py
```

演示 CLI：

```powershell
python -m src.runtime_v1.demo_cli
```

## 已知限制

- 正式独立 held-out E2E 尚未完成，不能把现有回归、shadow 或 demo 验证描述为正式泛化结论。
- Demo 的 15 个问题中有 3 个安全的 fail-closed 行为与预期不一致；最慢本地模型生成约 16 秒。
- Pilot V1 的收益较小且存在回退，未进入 Submission Candidate V1。
- Base + LoRA 的本地加载 smoke 缺少对应 Qwen Base 快照，未执行；`legacy_data_second` 仍因本地模型运行停滞而未完成。
- Dynamic Retriever 与 Core + Dynamic fusion 仍是实验/shadow 资产，不得描述为生产已启用。

## 下一步

1. 冻结并执行真正独立的 held-out E2E，固定输入、指标、模型、Prompt、重试和缓存口径。
2. 针对 Demo 的 3 个行为不匹配案例做独立诊断，不直接改写冻结阈值或历史资产。
3. 在可用的 Qwen Base 环境中完成 Pilot V1 Base + LoRA 加载与推理 smoke，再决定是否继续训练路线。
4. 继续保持 Frozen V1 只读；任何 corpus、Prompt、Retriever 或索引变更均创建新版本。

## 关键证据

- `reports/final_submission_integration_gate_v1.md`
- `reports/frozen_integrity_reconciliation_v1.md`
- `reports/submission_candidate_v1.json`
- `reports/submission_metrics.json`
- `experiments/demo_runtime_validation_v1/reports/demo_runtime_validation_report_v1.md`
- `evaluation/fine_tuning_pilot_v1_final/final_report.json`
- `evaluation/core_dynamic_e2e_runtime_shadow_v1/reports/actual_runtime_e2e_report_v1.md`
