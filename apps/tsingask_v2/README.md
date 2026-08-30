# 清问 · TsingAsk V2（独立版）

这是与现有线上智能体隔离的“可信校园事务智能体”。它不依赖清小搭，不读取认证门户资料，不会发布或覆盖线上项目。

## 一键安装与运行

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File apps\tsingask_v2\setup.ps1
powershell -ExecutionPolicy Bypass -File apps\tsingask_v2\start.ps1
```

浏览器打开 `http://127.0.0.1:8765`。首次安装默认下载官方 Qwen3-4B Q4_K_M（约 2.5 GB），校验大小和 SHA256；如只想先复用本机已校验的 Qwen2.5-1.5B，可给安装脚本加 `-SkipModel`。

## 已接通的五层能力

1. 本地模型：Qwen3-4B 优先、已校验 Qwen2.5-1.5B 回退；所有文件内容与规划留在本机。
2. Agent：Fast Path / Full Path、查询改写与拆分、Dense + BM25、metadata 重排、Evidence Gate、行动清单。
3. 公开知识库：严格限定清华官方公开来源，去重、排除新闻和过期资料、同制度保留较新版本，输出逐条审计记录与 8 场景 Coverage Matrix。
4. 文件工具：读取、生成、修改并下载 DOCX / XLSX / PPTX / PDF；模型只产出结构化计划，Python 写真实文件。
5. 独立产品：FastAPI + React/Vite，提供上传、问答、来源、证据状态、覆盖矩阵与文件下载接口。

## 知识库维护

```powershell
python scripts\build_trusted_campus_public_kb_v2.py
```

服务库在 `data/05_trusted_campus_kb_v2_public/`。原始抓取资料不会被物理删除；被判为重复、新闻、过期、非办事资料的项目只会从服务库剔除，并记录在 `audit/admission_decisions.jsonl`。

微信公众号资料采用白名单：账号必须能从清华官网核验，文章还必须是制度、流程或办事指南。一般新闻、活动回顾、人物故事不会入库；正式部门制度的权威级别始终高于公众号文章。

## API

- `GET /api/health`
- `GET /api/coverage`
- `GET /api/templates`
- `POST /api/uploads`
- `POST /api/chat`
- `GET /api/files/{file_id}`
- OpenAPI：`/api/docs`

运行时上传与生成文件只保存在 `apps/tsingask_v2/.artifact_runtime/`，该目录被 Git 忽略。
