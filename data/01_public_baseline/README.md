# 清华大学校园知识库第一轮公开网页采集工具

本工具从可公开访问的 `tsinghua.edu.cn` 及其子域名中，低频发现网页、提取原始正文并逐页保存为 Markdown，同时保留来源、元数据、附件链接和审计日志。它不登录、不绕过认证、不采集个人数据，也不调用任何 LLM。当前版本用于构造待后续 AI 筛选和人工审核的 Raw Knowledge Dataset。

## 环境与安装

建议使用 Python 3.11 或 3.12。在 Windows PowerShell 中执行：

```powershell
cd D:\python_projects\tsinghua_ai\data_first
python -m pip install -r requirements.txt
python main.py public
```

公开链路使用轻量 HTTP；认证门户链路使用可视化 Microsoft Edge + Playwright。安装依赖后无需下载 Chromium，因为默认调用本机 Edge。

## 文件结构

- `main.py`：入口。
- `config.yaml`：全部运行参数；默认安全测试模式。
- `seeds.txt`：可人工维护的官方入口，一行一个。
- `crawler/`：抓取、解析、发现、写入和 SQLite 状态。
- `utils/`：固定路径、URL、元数据与日志工具。
- `data/crawl_state.db`：待爬/已爬状态、深度、父页、ID 和内容哈希。
- `knowledge/01_raw/`：V1 第一轮已有公开数据，保持不动。
- `knowledge/01_raw_public/`：V1.1 起新增的公开数据。
- `knowledge/01_raw_portal/`：认证门户数据，只保存在本机。
- `knowledge/index.csv`、`index.jsonl`：知识索引。
- `knowledge/attachments.csv`：附件登记（不下载、不解析）。
- `logs/`：成功、失败、跳过、认证和重复明细以及 `crawl.log`。

## 测试模式与抓取规模

`config.yaml` 默认是：

```yaml
test_mode: true
test_max_pages: 100
max_pages: 3000
```

V1.1 第二轮测试的公开上限为 100 个新处理页面，不会自动继续正式抓取。验收后，明确将 `test_mode` 改为 `false` 才会采用 `max_pages`。可直接修改最大页数；深度、并发、单域延迟、超时和重试也均在配置中。正式扩大前建议继续保持 `concurrency: 3` 和每域至少 1 秒间隔。

## 停止、续爬与重试

按一次 `Ctrl+C` 停止。已完成结果会逐项提交到 SQLite 和索引，正在处理的 URL 在下次启动时自动恢复为待处理，因此再次执行 `python main.py public` 即为断点续爬。不要删除数据库。

失败页见 `logs/failed.csv`。若需统一重试，将 `retry_failed_on_start` 临时改为 `true` 后运行；已成功 URL 不会重抓。处理完建议改回 `false`，避免每次启动反复重试永久错误。

## 数据和日志

第一轮正文位于 `knowledge/01_raw`，V1.1 新公开正文位于 `knowledge/01_raw_public`。CSV 使用 UTF-8 BOM，便于 Excel 直接打开；JSONL 和 Markdown 使用 UTF-8。`source_url` 是发现地址，`final_url` 是重定向后地址。发布日期、更新时间和部门仅在页面存在可靠信号时写入，否则为空。

常见跳过原因：`robots_disallowed`、`soft_404`、`login_required`、`private_or_sensitive`、`no_meaningful_content`、`unsupported_content_type`。认证页另记入 `logs/auth_required.csv`，不会尝试绕过。429 和服务端临时错误会有限退避，超过配置次数后停止重试。

## 常见问题

- **没有生成 Markdown**：查看 `logs/skipped.csv`、`failed.csv` 和网络连通性；入口也可能受 robots 约束。
- **中文乱码**：文件均为 UTF-8；CSV 带 BOM。编辑器应选择 UTF-8。
- **结果偏少**：先检查种子和最大深度，不要直接提高并发。
- **动态页面为空**：当前不会默认启动浏览器，这是已知边界；应先人工确认公开性，再开发 Playwright fallback。
- **想完全重跑**：为保留审计链，不建议手工删除状态；请先备份整个 `data_first`，再显式规划新批次数据库。

## 清华信息门户采集

认证门户与公开网页是两套独立链路：

```powershell
python main.py public  # 只运行公开网页
python main.py portal  # 只运行认证门户
python main.py all     # 先公开、后门户；必须显式指定
python main.py         # 只显示帮助，不采集
```

运行 `python main.py portal` 后，程序先探测当前 Edge 是否通过官方 CDP 调试端口开放。若可以，会新建一个标签页附着，不读取浏览器数据库、Cookie 或 Token；若无法规范附着，则启动独立的可视 Edge。看到登录页后，请本人手动完成用户名、密码和验证码输入。进入信息门户即表示登录成功，程序随后保存 Playwright 自己的会话状态并开始受控采集。

会话过期时，Portal 采集会停止并写入 `logs/portal_auth_expired.csv`。重新运行命令，在可视浏览器中再次手动认证即可断点续爬。程序绝不自动填写或反复提交登录表单。

Portal 默认 `portal_test_max_pages: 5`；完成安全抽检后才可人工改为最多 50。最大深度为 3，只扩展包含办事、服务、通知、新生、信息化、后勤、图书馆、校医院、体育或安全等白名单主题的链接，不做全站递归。

所有 Portal Markdown 位于 `knowledge/01_raw_portal`，标记为 `access_level: campus_authenticated` 和 `source_mode: authenticated_portal`；索引为 `portal_index.csv/jsonl`，附件只登记到 `portal_attachments.csv`。这些数据不得上传公开 GitHub、发布到公网、转为公开 API 或发送第三方。

以下内容严格禁止：成绩、GPA、课表、选课/考试结果、借阅/消费/财务/工资记录、校园卡余额、住宿房间、医疗/体检结果、个人邮件/网盘、个人申请审批、学籍详情、身份或银行卡信息、个人账户及任何认证凭证。URL、锚文本或标题命中高风险词时会在访问正文前阻止，并登记到 `portal_private_skipped.csv`。

按 `Ctrl+C` 会停止新增导航、保存 SQLite/CSV、保存专用浏览器状态并安全关闭专用 Edge。下次运行自动恢复 `portal_state.db` 中断点。

如需清除本项目的本地认证状态，请先停止 Portal 程序，然后手工删除 `data/auth/storage_state.json`。该目录已加入 `.gitignore`。删除它只会要求下次重新手动登录，不会删除 Portal Markdown、索引或状态数据库。

## 第二阶段建议

保持 `knowledge/01_raw` 不变，将 AI 筛选作为独立程序读取索引和 Markdown，输出到新的目录；做相关性评分、主题分类、时效性、冲突与近似重复检测，并保留人工审核状态。不要让筛选程序覆写第一轮原始材料。
