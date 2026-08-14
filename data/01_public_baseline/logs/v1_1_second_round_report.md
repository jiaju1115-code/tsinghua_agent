# V1.1 与第二轮采集报告

> 本文件记录最初因用户离线而未完成认证的阶段性结果。Portal 后续已完成累计50页测试；最终结果请以 `logs/portal_privacy_and_qa_report.md` 为准。

时间：2026-08-09（Asia/Shanghai）

## 数据保护

- 第一轮 `knowledge/01_raw` 的 26 份 Markdown 未移动、未删除、未改写。
- 原 `data/crawl_state.db`、索引与日志均增量保留。
- V1.1 新公开数据写入 `knowledge/01_raw_public`。
- Portal 数据目录、独立状态库、索引和日志已建立。
- 两次 Portal 手动登录均超时，未采集认证正文；失败会话产生的无效 `storage_state.json` 已删除，避免保留不必要认证材料。

## Public V1.1 实现

- URL 队列新增 priority，按 URL、链接锚文本和高价值服务域名联合评分。
- 已验证并加入信息化、图书馆、饮食、校医院、体育、保卫、后勤和研究生办事指南入口。
- 解析 `robots.txt` 的 Sitemap 声明及 `/sitemap.xml`，设置单种子数量和 sitemap-index 层数限制；初始化标记避免每次启动重复请求。
- 新结果 Front Matter 增加 `source_mode: public_web`。
- 清洗增加页眉页脚、二维码、打印、分享、图标私有字符和明显重复数字处理。
- 保留 SHA256 精确去重，新增 64 位 SimHash；近似重复只登记，不删除正文。
- 修复畸形 URL 端口导致的异常，并确保后续内部异常会回写 SQLite 与 `failed.csv`。

## Public 第二轮测试

- 实际处理：100（达到硬上限后停止）
- 成功：86
- 失败：1（畸形 URL；已修复，URL 已恢复为待处理）
- 跳过：5
- 认证：2
- 精确重复：6
- 近似重复：1
- 新发现 URL：552
- 生成 Markdown：86
- 输出目录：`knowledge/01_raw_public`

分类分布：

- 校园办事：8
- 校园生活：9
- 新生入校：8
- 规章制度：5
- 校园通知：0（本批旧分类函数未单列通知；代码现已补充该类别）
- 其他：56

近似重复示例：`THU000038` 与 `THU000099`，SimHash 相似度 0.9531；两份均保留。

## Portal 实现

- 独立 Playwright/Edge 链路，不复制 Requests Cookie。
- 先探测本机 `9222/9223` 官方 CDP 端口；仅开放时才附着，并新建标签页。
- 未开放 CDP 时启动独立、可视 Microsoft Edge，由用户本人手动认证。
- `data/auth` 已加入 `.gitignore`，任何状态均不写日志、不打印 Cookie/Token/Header。
- URL、锚文本、标题进入正文前均执行个人页面 deny；正文保存前再次扫描敏感值模式。
- 只对白名单校园公共主题扩展，最大深度 3，不做全站递归，不查隐藏 sitemap。
- 独立 `portal_state.db`、`PORTAL000001` ID、Raw 目录、CSV/JSONL、附件表和五类日志。
- Portal Markdown 固定标记 `campus_authenticated` 和 `authenticated_portal`。
- Ctrl+C 逐项保存状态并关闭专用浏览器。

## Portal 测试结果

- 当前 Edge 官方 CDP 复用：失败；没有发现开放的官方调试端口，未强行接管。
- 采用方式：独立可视 Edge + 用户手动统一身份认证。
- 启动次数：2
- 两次均在 600 秒内未检测到登录完成，安全超时退出。
- 成功：0
- 失败页面：0
- 跳过页面：0
- 主动阻止个人页面：0（尚未进入链接发现）
- 登录过期：0
- 手动登录超时：2
- 生成 Markdown：0
- Portal 附件：0
- 个人数据误抓：没有；Portal Raw 目录为空，索引和日志只有表头。

由于 Portal 成功数为 0，以下统计当前不可计算：分类分布、高价值公共信息比例、10 份随机抽检、最有价值栏目、JS 页面比例和附件规模。未达到“先成功采集 5 页并确认安全”的前置条件，因此没有擅自扩大到 50 页。

## 自动测试

- AST 语法检查：通过。
- 单元测试：7/7 通过。
- 覆盖 URL 标准化、HTML/附件解析、认证页识别、SQLite 恢复、公开优先级、SimHash、Portal 私人 deny。
- 86 份 V1.1 Public Markdown 的 YAML Front Matter 均可解析，`access_level`/`source_mode` 正确。
- Conda 退出时仍显示本机 `conda-libmamba-solver` 插件警告，与采集结果无关。

## 下一步

1. 用户准备好后运行 `python main.py portal`，在专用 Edge 中完成登录；保持 `portal_test_max_pages: 5`。
2. 立刻扫描全部 5 份内容与索引，确认无成绩、课表、财务、借阅、申请、账户或身份信息。
3. 只有 5 页安全检查通过后，才把 `portal_test_max_pages` 人工调到 50 并运行第二次。
4. 对 50 页结果随机抽检至少 10 份，再计算 Portal 高价值比例、JS/iframe 与附件规模。
5. Public 下一批开始后，新发现链接将使用中文锚文本优先级；本批运行前的旧待爬链接缺少历史锚文本，无法事后完整恢复其评分。
