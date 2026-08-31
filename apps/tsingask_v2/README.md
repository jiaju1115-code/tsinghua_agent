# 清问 · TsingAsk V2（独立版）

这是与现有线上智能体隔离的“可信校园事务智能体”。它不依赖清小搭，不读取认证门户资料，不会发布或覆盖线上项目。

## 一键安装与运行

在仓库根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File apps\tsingask_v2\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File apps\tsingask_v2\start.ps1
```

浏览器打开 `http://127.0.0.1:8765`。首次安装默认下载官方 Qwen3-4B Q4_K_M（约 2.5 GB），校验大小和 SHA256；如只想先复用本机已校验的 Qwen2.5-1.5B，可给安装脚本加 `-SkipModel`。

输入框上方可直接选择检索方式：`Fast / 快速回答` 只做轻量检索，适合术语解释和简单事实；`Full / 深度检索` 会拆解问题并启用 Dense + BM25 与完整证据核验，适合条件、材料、流程、截止时间和多条件比较。选择会保存在本机浏览器中。调用 `POST /api/chat` 时也可传 `retrieval_mode: "fast" | "full" | "auto"`。

安装脚本默认使用 `-GpuBackend auto`：检测到 NVIDIA 显卡时安装 CUDA 版 PyTorch 与 llama.cpp，并把 Qwen3 的全部层卸载到 GPU；Apple Silicon 使用 Metal，其余机器安全回退到 CPU。AMD/Intel 独显部署可显式选择 `-GpuBackend vulkan`（需要本机 CMake/C++ 与 Vulkan SDK），AMD ROCm 可选择 `hipblas`。运行时可用 `TSINGASK_FORCE_CPU=1` 强制 CPU，或用 `TSINGASK_GPU_LAYERS=20` 限制显存占用；默认 `auto` 等价于 GPU 后端可用时 `-1`（全部层）。多卡可用 `TSINGASK_TENSOR_SPLIT=0.6,0.4` 指定显存比例。`GET /api/health` 会返回实际加速模式。

示例：

```powershell
# 自动检测（推荐）
powershell -ExecutionPolicy Bypass -File apps\tsingask_v2\setup.ps1 -GpuBackend auto

# CUDA 12.4 预编译轮子
powershell -ExecutionPolicy Bypass -File apps\tsingask_v2\setup.ps1 -GpuBackend cu124
```

## 已接通的核心能力

1. 本地模型：Qwen3-4B 优先、已校验 Qwen2.5-1.5B 回退；自动使用可用 GPU，所有文件内容与规划留在本机。
2. Agent：Fast Path / Full Path、查询改写与拆分、Dense + BM25、metadata 重排、Evidence Gate、行动清单；Full Path 由本地模型将已确认事实组织成自然中文，生成内容会逐句检查事实引用、中文短语支持度和数字越界，未通过的句子会被剔除，无法安全保留时才回退到确定性答案。
3. 公开知识库：当前为 402 个服务来源、2,004 个 chunks、Dense 索引 ready；严格限定清华官方公开来源，去重、排除新闻和过期资料、同制度保留较新版本，输出逐条审计记录、8 场景 Coverage Matrix 和 20 类高频事务矩阵。
4. 文件工具：读取、生成、修改并下载 DOCX / XLSX / PPTX / PDF；模型只产出结构化计划，Python 写真实文件。
5. 引导式 Evidence Gate：证据不足时不再只拒答，而是最多追问 3 个关键槽位，同时给出官方查找入口；PARTIAL 只回答已确认部分，CONFLICT 展示版本冲突与采用依据。
6. 多轮事务：会话记住身份、学期、当前/目标院系、项目类型；流程结论自动沉淀为可勾选任务，并可导出 ICS 日历。
7. 材料检查：上传材料后可检查表面完整性、空白字段、签字盖章提示；它不会替代主管部门的资格审查。
8. 安全与治理：检索内容及上传文件做提示注入隔离；全链路耗时与案例可回放；反馈进入隔离队列，不会自动污染知识库。
9. 独立产品：FastAPI + React/Vite，支持真实下载、异步文件任务、预热、文件自动过期与本机容器部署。

## 知识库维护

一次性原子重建：

```powershell
python scripts\build_trusted_campus_public_kb_v2.py
```

公开站点增量抓取、附件下载、清洗、Dense 索引与原子切换：

```powershell
python scripts\refresh_trusted_campus_public_kb_v2.py
```

安装每周日 03:30 的本机更新任务：

```powershell
powershell -ExecutionPolicy Bypass -File apps\tsingask_v2\install_refresh_task.ps1
```

更新过程只抓公开页面，遵守现有域名白名单、并发和间隔限制。新库只有完整构建成功后才会替换服务库；旧库保留为 `.previous`，失败则自动回滚。服务会检测知识库 manifest 变化，并在下一次请求时载入新版本，无需重启。微信公众号信息只从清华官网核验的账号和可公开验证的原文/附件进入候选集，不登录信息门户，也不绕过访问控制。

服务库在 `data/05_trusted_campus_kb_v2_public/`。原始抓取资料不会被物理删除；被判为重复、新闻、过期、非办事资料的项目只会从服务库剔除，并记录在 `audit/admission_decisions.jsonl`。

当前快照排除了 138 条新闻/宣传资料和 18 条认证/受限来源。`intent_coverage_matrix.json` 中的 `READY` 只表示该事务已有最低数量的可执行官方证据，不表示当期批次、院系细则或截止日期一定完整。涉及“今年/本学期/当前截止时间”的问题仍会执行时效过滤与 Evidence Gate。

微信公众号资料采用白名单：账号必须能从清华官网核验，文章还必须是制度、流程或办事指南。一般新闻、活动回顾、人物故事不会入库；正式部门制度的权威级别始终高于公众号文章。

## API

- `GET /api/health`
- `GET /api/coverage`
- `GET /api/intent-coverage`
- `GET /api/templates`
- `POST /api/uploads`
- `POST /api/chat`
- `POST /api/jobs`、`GET /api/jobs/{job_id}`（较慢的文件任务）
- `GET /api/files/{file_id}`
- `POST /api/sessions`、`GET/PATCH /api/sessions/{id}/tasks...`
- `GET /api/sessions/{id}/calendar.ics`
- `GET /api/traces`、`POST /api/traces/{case_id}/replay`
- `POST /api/feedback`
- `POST /api/warmup`
- OpenAPI：`/api/docs`

## 容器运行

模型与知识库以只读卷挂载，服务仅监听本机回环地址：

```powershell
docker compose -f apps\tsingask_v2\docker-compose.yml up --build
```

运行时上传与生成文件只保存在 `apps/tsingask_v2/.artifact_runtime/`，该目录被 Git 忽略。上传默认 7 天过期，生成文件默认 1 天过期；异步任务状态当前保存在进程内，重启后失效。生产化前应接入持久队列、身份认证、配额和定时清理。

## 当前边界

- 公开服务库不读取登录信息门户内容，不保存 Cookie、token、浏览器 profile、成绩、名单或财务信息。
- 微信公众号只有在账号可从清华官网核验、原文/附件能公开访问且内容属于制度或流程时才允许准入；当前服务快照没有公众号来源，不使用搜索摘要补数。
- 当前轻量回归为 22 项通过，但尚未完成新一轮正式 held-out E2E 和真实用户评测，README 不声明生产准确率。
