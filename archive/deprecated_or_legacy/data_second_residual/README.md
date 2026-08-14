# 清华大学校园知识库第二阶段：AI筛选、分类与审核

本项目只读取 `D:\python_projects\tsinghua_ai\data_first` 的 Raw Evidence，在 `D:\python_projects\tsinghua_ai\data_second` 生成候选索引、审核JSON、分类副本和人工复核报告。程序不会修改、移动或删除第一阶段任何文件；源文件完整性通过逐文件 SHA256 清单在运行前后验证。

本阶段只做审核，不总结或改写官方正文。`reject` 仅表示不建议进入下一阶段，原始证据始终保留在 `data_first`。

## 安装

建议 Python 3.11 或 3.12：

```powershell
cd D:\python_projects\tsinghua_ai\data_second
python -m pip install -r requirements.txt
```

## Public与Portal策略

Public 文档可以发送给本次配置的 MomoAPI，并只要求模型返回审核 JSON。Portal 标记为 `campus_authenticated`，默认仅使用本地规则和人工复核，完整正文不会进入外部客户端。`config.yaml` 中 `allow_external_llm_for_portal: false` 必须保持默认值；代码还在客户端入口执行硬性阻止。

Portal 结果默认复制到 `knowledge/03_needs_review/portal`。本地规则明确判断为人物宣传、科研入口或低价值活动候选时，复制到 `knowledge/05_rejected/portal_candidates`；这仍只是人工审核候选，不删除原文。

## MomoAPI配置

真实凭证只在 `.env`：

```dotenv
MOMO_API_KEY=your_api_key_here
MOMO_API_BASE=https://momoapi.cc/v1
MOMO_MODEL=控制台或models接口确认的模型名
```

`.env` 已加入 `.gitignore`。更换临时 Key 或模型只需编辑 `.env`，不改 Python。日志会脱敏 `Authorization: Bearer ...` 和 `sk-...`。401/403 会立即停止，不连续重试；429和5xx只有限退避。

Base URL 来自 MomoAPI 官方 `/api/status` 返回的服务地址及官方 OpenAI 客户端 `{address}/v1` 配置，不是猜测。模型必须从认证后的 `/v1/models` 实际查询确认。

## 命令

```powershell
python main.py build-index
python main.py api-test
python main.py review-public --limit 30
python main.py review-portal-local
python main.py report
python main.py status
```

直接执行 `python main.py` 只显示帮助，不会审核。Public 首批硬限制最多30篇；Portal本地审核可处理现有全部小规模数据。

推荐顺序：

1. `build-index`：建立Candidate索引、历史去重和原始层哈希基线。
2. 确认 `.env` 的模型后执行 `api-test`，只发送自行生成的无敏感短文本。
3. `review-public --limit 30`：分层抽取校园服务、生活、通知、新生和低价值新闻。
4. `review-portal-local`：完全本地处理Portal并生成 `reports/portal_manual_review.csv`。
5. `report`：生成分类、质量异常、抽样和源完整性报告。
6. `status`：查看SQLite断点状态。

## 断点续审与版本

`data/review_state.db` 使用 `id + content_hash + prompt_version + model + review_type` 唯一确定审核版本。相同组合已完成时不再次付费；进程中断后 `processing` 会恢复为 `pending`。Key失效时更换 `.env` 后重新运行同一命令即可继续。

Prompt版本位于 `config.yaml` 的 `prompt_version`。需要比较新规则时改为 `v2`、`v3`，SQLite会将其视为新审核版本；旧结果仍保留。

## 输出

- `data/candidate_index.csv/jsonl`：统一候选索引。
- `data/review_state.db`：断点状态。
- `reviews/review_results.csv/jsonl`：审核结果。
- `reviews/usage.csv`：API实际返回的Token统计，不自行估算。
- `knowledge/02_ai_reviewed`：逐篇审核JSON，不含完整原文。
- `knowledge/03_needs_review`、`04_approved`、`05_rejected`：从Raw复制的Markdown。
- `reports/portal_manual_review.csv`：Portal人工审核清单。
- `reports/classification_report.md`：分类统计。
- `reports/quality_report.md`：异常判断检测。
- `reports/sampling_report.md`：Public与Portal抽样。
- `reports/source_integrity_report.md`：data_first前后哈希核对。

`reviews/raw_model_outputs` 只保存Public模型响应正文，不保存请求Header或API Key。Portal正文不会写入该目录。
