# Prompt V3.2 Blind Test V1 正式评估报告

## 执行状态

`EVALUATION_BLOCKED — UPSTREAM_CHAT_COMPLETION_READ_TIMEOUT`

本次没有得到任何有效 Prompt V3.2 输出，因此不能计算或发布正式盲测性能指标，也不能从四个规定结论中选择 PASS/NEEDS_REVISION/FAIL。该状态是基础设施故障，不是模型性能结论。

## A. 样本与泄漏检查

- 冻结样本：50 条；random 25、targeted 25。
- 历史调参样本泄漏：0。
- URL 与 normalized URL 重复：0。
- 冻结人工文件 SHA-256：`EC1E846091532205A04480320A4A4572D99526F58FE8A9037390BED4BC502CA6`。
- Prompt V3.2 SHA-256：`B94623C520FC46D83A49A4D043AD182646E7A881E7E1751E3E98E98724D771CD`。
- 模型输入不含人工标签、人工备注或历史 AI 判断。

## B. 冻结人工标签

- human_action：50/50 有效；approve 27、review 1、reject 22。
- human_topic_relevance：50/50 有效；high 31、medium 11、low 8。
- 数字 `29`、`30` 等模板残留仅在辅助字段中按 missing 处理；原始人工文件未被修改。

## C. API 执行记录

- 冻结配置：gpt-5.4-mini、temperature 0.1、concurrency 3、max_completion_tokens 900。
- 首轮沙箱内调用：0 成功、50 失败；150 次网络尝试，含 100 次重试，均为套接字权限拒绝。
- 获准联网后进行两次完整批次尝试：分别运行约 15 分钟和 30 分钟，均无单条原始结果落盘，随后终止残留进程以避免重复调用。
- TCP 443、HTTP 服务、鉴权和 `/models` 均正常；模型列表包含 `gpt-5.4-mini`。
- 不含样本数据的最小 chat completion 探针在 60 秒后 ReadTimeout，故障定位为上游生成接口。

## D. 正式指标

以下指标均为 `NOT_AVAILABLE — 0 EVALUABLE AI RESULTS`：

- action 一致率与 3×3 混淆矩阵
- approve precision / recall
- reject precision / recall
- topic_relevance 一致率
- reject_type 一致率
- low + approve
- random vs targeted
- medium 专项
- domain/content_type/category 与各定向覆盖专项
- action 分歧与 Human label 疑问

## E. 系统性错误与冻结建议

- 是否存在 Prompt 系统性错误：`NOT_EVALUABLE`。
- 是否建议冻结 Prompt V3.2：`NO — 等待同一冻结配置成功完成 50/50 API 结果后再判断`。
- 正式盲测结论：`EVALUATION_BLOCKED`，不是 `BLIND_TEST_FAIL`。

## F. 重跑要求

上游 chat completion 恢复后，应直接重跑现有冻结运行器。不得更换样本、模型、Prompt、temperature、并发或 token 参数；只有 50 条原始结果全部保存后，才能读取冻结人工标签并计算正式指标。
