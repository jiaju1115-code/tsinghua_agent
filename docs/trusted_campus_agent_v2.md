# 清问·可信校园事务智能体 V2（独立候选版）

## 边界

V2 使用独立的公开服务库 `data/05_trusted_campus_kb_v2_public/`，所有新增代码和生成资产均与 V1、发布目录和线上智能体隔离。Public staging 先进入自动复核候选池，只有通过来源、质量、时效、访问级别和事务性标题规则的资料才进入未发布 shadow 检索；历史 review_required 字段仅为兼容旧工件，不再表示需要人工复核。

公开服务库严格只接纳 `access_level=public` 的资料。登录信息门户采集到的页面即使最终跳转到公开域名，也仍标记为 `campus_authenticated`，不得混入公开服务库；Cookie、storage state、个人成绩、名单和财务信息不得写入仓库。

## 链路

```text
Query Planner
  ├─ Fast Path: alias rewrite -> BM25 -> metadata rerank
  └─ Full Path: rewrite/decompose -> Dense + BM25 -> RRF -> metadata/time/authority rerank
       -> Evidence Gate (SUPPORTED/PARTIAL/CONFLICT/NOT_SUPPORTED)
       -> grounded facts + citations + optional action checklist
```

## 关键规则

- metadata 必含 `source / department / publish_date / effective_date / expiry_date / audience / authority_level / topic`；未知日期保持 `null`，不伪造。
- 最新/当前问题过滤已过期来源。排序同时使用相关性、权威性、时效性、场景与受众匹配。
- Evidence Gate 未通过时不补写事实；冲突时保留冲突来源，历史版本单独提示。
- Evidence Gate 对条件、材料、步骤、截止时间和官方入口逐项检查，不能用“相关文档被召回”代替“对应信息已被证据覆盖”。
- 办事问题输出条件、材料、步骤、截止时间和官方入口五类清单；缺项保持为空。
- Fast Path 不加载 Dense 模型；Full Path 才延迟加载冻结 encoder。
- Full Path 批量编码拆解后的子问题；Dense 初始化失败时显式退化为 BM25，并把证据状态上限收紧为 PARTIAL。
- 常驻服务应在 readiness 阶段调用 warmup_full_path()，把本机约 30 秒的首次模型初始化移出用户请求；本次真实 smoke 的热请求约 0.2 秒。

## 知识覆盖

- 八大场景覆盖矩阵：`data/05_trusted_campus_kb_v2_public/coverage_matrix.json`，服务接口为 `GET /api/coverage`。
- 二十类高频事务覆盖矩阵：`data/05_trusted_campus_kb_v2_public/intent_coverage_matrix.json`，服务接口为 `GET /api/intent-coverage`。
- 高频事务定义维护在 `configs/trusted_campus_agent_v2/high_frequency_intents.json`，构建过程会按主题词、办理动作、权威性和有效性统计来源。
- `READY` 只表示存在足够的可执行官方证据，不表示每个当期批次、截止日期或院系细则均已覆盖；涉及“本学期/今年/当前截止时间”的问题仍必须经过时效过滤和 Evidence Gate。

## 当前开发诊断

检索诊断按公开可回答 gold 与 restricted gold 分开统计，避免把默认访问控制造成的不可召回误写成检索退化。该集合不是 held-out，样本也很小，只用于确认改造方向，不能作为正式效果声明。明细见 evaluation/trusted_campus_agent_v2/dev_retrieval_metrics.json。

## 本地使用

```powershell
python scripts/build_trusted_campus_v2_assets.py
python scripts/chat_trusted_campus_v2.py
```

## 文件生成与处理

- TrustedCampusAgentV2.handle() 自动区分普通 RAG 问答和文件任务。
- 支持 DOCX/XLSX/PPTX/PDF 的真实创建、回读和修改后另存；返回值中的 artifact.download_path 可直接下载。
- 内置社会实践报告、活动策划书、奖学金申请材料、会议纪要、课程报告五类校园模板，也可传入用户原模板。
- LLM 只需生成结构化 FilePlan；Python 文件工具负责 OOXML/PDF 字节、样式和导出。
- 可选的 OpenAI-compatible Tool Calling 已正式绑定到 FilePlan。宿主先确定动作、格式和本地路径，再强制模型调用 `create_or_modify_campus_file`；模型返回的路径和来源一律不采信。
- 外部 LLM 默认拿不到用户上传文件内容，也拿不到 campus-authenticated/restricted 证据。只有调用方显式设置 `allow_external_file_content=True` 才能发送已解析的上传内容。
- “根据学校最新要求生成……”默认先经过 RAG 与 Evidence Gate。CONFLICT 或 NOT_SUPPORTED 会拒绝生成权威结论，PARTIAL 只写入已确认部分。

```powershell
python scripts/file_tool_trusted_campus_v2.py "生成一份社会实践报告Word"
python scripts/file_tool_trusted_campus_v2.py "把张三替换为李四" --input .\input.docx --replacements-json .\replace.json
python scripts/file_tool_trusted_campus_v2.py "根据学校最新要求生成实践报告" --format docx --rag --shadow
```

### 使用 LLM Tool Calling

在本地 `.env` 或运行环境配置 OpenAI-compatible 接口；默认读取 `MOMO_API_BASE`、`MOMO_API_KEY`、`MOMO_MODEL`，也可用 `--llm-env-prefix` 选择另一组前缀。密钥不会写入仓库。

```powershell
python scripts/file_tool_trusted_campus_v2.py "生成一份活动策划书Word" --llm-tool-calling
python scripts/file_tool_trusted_campus_v2.py "根据学校最新要求生成社会实践报告" --format docx --rag --shadow --llm-tool-calling
python scripts/chat_trusted_campus_v2.py --shadow --file-llm
```

接入清小搭或其他宿主时，注册 `CampusToolRouter.tool_schemas(openai_wrapper=True)` 返回的工具定义；收到工具调用后，将参数交给 `CampusFileService.execute_with_llm()`。宿主必须自行提供并校验 `input_path`、`template_path`、`output_path`，不要从模型文本中解析路径。稳定契约见 `configs/trusted_campus_agent_v2/file_tool_calling_contract.json`。

本版本是开发候选，不应直接替换或发布现有 Submission Candidate V1。
