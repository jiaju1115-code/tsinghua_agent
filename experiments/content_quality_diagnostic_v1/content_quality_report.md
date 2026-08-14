# Public V1 正文抽取质量诊断报告

诊断对象：`public_expansion_v1/run_6` 的 300 条 cleaned Markdown。诊断仅使用本地现有 Markdown、审核结果与代码；未请求网页、未重抓、未调用审核 API、未修改原始数据。

## 结论摘要

最终结论：`CONTENT_EXTRACTION_CRITICAL`

- 可直接用于知识库审核的主体内容：55/300（18.3%）。口径为 `detail_content + thin_content`，不把 `list_page` 视为完整正文。
- 明确抽取失败（`content_missing + navigation_only`）：174/300（58.0%）。
- Prompt V2 的 approve 中，119/153（77.8%）落入缺失、纯导航、模板污染或列表页；现有 approve 不能直接沿用。
- reject 中 71/115（61.7%）属于正文缺失或纯导航，存在因输入残缺被误 reject 的风险。
- 应暂停 Public Expansion V2，先修正文提取，再对受影响数据重抓并重新 Prompt V2 审核。

## A. 七类分布

| 分类 | 数量 | 比例 |
|---|---:|---:|
| `detail_content` | 51 | 17.0% |
| `list_page` | 60 | 20.0% |
| `navigation_only` | 21 | 7.0% |
| `content_missing` | 153 | 51.0% |
| `template_polluted` | 11 | 3.7% |
| `thin_content` | 4 | 1.3% |
| `mixed_or_uncertain` | 0 | 0.0% |

## B. 真正可用正文比例

`detail_content` 51 条加 `thin_content` 4 条，共 55 条（18.3%）。`template_polluted` 虽能辨认正文，但不计入“可直接使用”，应先清理模板；`list_page` 只具索引价值。

## C. 与 Prompt V2 交叉分析

| action | 总数 | detail | list | navigation | missing | polluted | thin | uncertain | 明确抽取失败 | 广义质量受影响 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| approve | 153 | 31 | 35 | 15 | 59 | 10 | 3 | 0 | 74 | 119 |
| review | 32 | 0 | 2 | 1 | 28 | 0 | 1 | 0 | 29 | 31 |
| reject | 115 | 20 | 23 | 5 | 66 | 1 | 0 | 0 | 71 | 95 |

- approve 污染：`navigation_only` 15、`content_missing` 59、`template_polluted` 10、`list_page` 35；其中低价值且不建议下钻的 list approve 为 19 条。
- review：明确抽取失败 29/32（90.6%），review 大量由正文质量问题驱动。
- reject 误伤风险：`content_missing + navigation_only` 共 71 条。

## D. list_page 下钻价值

- 总数：60；`should_follow_links=yes`：19；`no`：41。

| 类型 | 合计 | yes | no |
|---|---:|---:|---:|
| 其他 | 29 | 8 | 21 |
| 办事 | 4 | 4 | 0 |
| 招聘 | 2 | 2 | 0 |
| 政策 | 2 | 2 | 0 |
| 新闻 | 20 | 0 | 20 |
| 法规 | 3 | 3 | 0 |

## E. 来源站点

本批数据实际仅包含 3 个 domain，因此不能虚构 Top 10/15；以下列出全部站点，并按明确抽取失败数排序。

| domain | total | detail | list | missing | navigation | polluted | 明确失败 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lib.tsinghua.edu.cn | 263 | 33 | 51 | 151 | 13 | 11 | 164 |
| www.itc.tsinghua.edu.cn | 23 | 15 | 3 | 2 | 3 | 0 | 5 |
| peace.tsinghua.edu.cn | 14 | 3 | 6 | 0 | 5 | 0 | 5 |

最严重的是 `lib.tsinghua.edu.cn`：样本占比极高，且大量详情页只保存统一导航、咨询页尾与“读取内容中，请等待…”占位。`www.itc.tsinghua.edu.cn` 的已知新闻详情页则只留下学校/中心导航。`peace.tsinghua.edu.cn` 主要问题是栏目页与短标签页被当作候选正文。

## F. 重点人工复核样本

### 10 个最严重正文抽取失败案例

| ID | 标题 | action | 说明 |
|---|---|---|---|
| PUBEXP000013 | 关于公布2026年暑假图书馆开馆时间的通知-清华大学图书馆 | review | 详情页正文缺失；含动态加载占位 |
| PUBEXP000014 | 2026学术图书馆未来论坛（WAL）成功举办-清华大学图书馆 | reject | 详情页正文缺失；含动态加载占位 |
| PUBEXP000015 | 关于美术图书馆暂停开放的通知-清华大学图书馆 | reject | 详情页正文缺失；含动态加载占位 |
| PUBEXP000018 | 总馆、文科图书馆图书可全域预约啦！-清华大学图书馆 | approve | 详情页正文缺失；含动态加载占位 |
| PUBEXP000030 | 2026年图书馆接收毕业生赠书通知-清华大学图书馆 | review | 详情页正文缺失；含动态加载占位 |
| PUBEXP000049 | 服务国家开放创新战略：Frontiers、NSFC科学传播与成果转化中心、CEPIEC 达成战略合作-清华大学图书馆 | reject | 详情页正文缺失；含动态加载占位 |
| PUBEXP000050 | 清华新实践：开放获取期刊《智慧图书馆》iLibrary创刊研讨会顺利召开-清华大学图书馆 | reject | 详情页正文缺失；含动态加载占位 |
| PUBEXP000051 | 文章鉴读 / OASPA：从“百分比”到“参与度”——构建包容性开放获取生态的行动指南 (下)-清华大学图书馆 | approve | 详情页正文缺失；含动态加载占位 |
| PUBEXP000052 | Frontiers发布出版行业首份AI实践指南：为科研出版构建负责任 AI 应用路线图-清华大学图书馆 | reject | 详情页正文缺失；含动态加载占位 |
| PUBEXP000053 | MDPI（多学科数字出版机构）开放获取（OA）政策-清华大学图书馆 | approve | 详情页正文缺失；含动态加载占位 |

### 10 个 list_page 案例

| ID | 标题 | action | 说明 |
|---|---|---|---|
| PUBEXP000045 | 特色资源-清华大学图书馆 | approve | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000046 | 最新资源-清华大学图书馆 | approve | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000047 | 精选资源-清华大学图书馆 | approve | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000084 | 多媒体资源推介-清华大学图书馆 | reject | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000148 | 资源推送 | approve | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000175 | 出版支持-清华大学图书馆 | approve | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000219 | 数据库说明-清华大学图书馆 | approve | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000246 | 入馆须知-清华大学图书馆 | approve | 其他列表；下钻=yes：该资源/服务目录具有稳定知识价值，详情页通常包含范围、使用条件或入口说明。 |
| PUBEXP000012 | 默认排序-清华大学图书馆 | approve | 办事列表；下钻=yes：办事列表的核心规则、条件或办理信息通常在详情页，建议后续下钻。 |
| PUBEXP000044 | 按类型查-清华大学图书馆 | approve | 办事列表；下钻=yes：办事列表的核心规则、条件或办理信息通常在详情页，建议后续下钻。 |

### 10 个 template_polluted 案例

| ID | 标题 | action | 说明 |
|---|---|---|---|
| PUBEXP000029 | 失物招领 | approve | 导航样式行占比 95.8%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000139 | 诺贝尔经济学奖得主著作 | approve | 导航样式行占比 83.6%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000010 | 图书馆报告厅-清华大学图书馆 | approve | 导航样式行占比 76.8%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000245 | M-清华大学图书馆 | approve | 导航样式行占比 74.1%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000153 | 培训资料 | approve | 导航样式行占比 69.8%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000243 | 外文期刊 | approve | 导航样式行占比 68.8%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000134 | 金融学全文电子刊 | approve | 导航样式行占比 67.1%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000019 | 清华大学图书馆美术图书馆 | approve | 导航样式行占比 64.7%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000145 | 本馆风采 | approve | 导航样式行占比 64.3%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |
| PUBEXP000057 | 组织机构-清华大学图书馆 | reject | 导航样式行占比 63.0%；主体存在，但混入页头/栏目/页尾模板，会稀释 Prompt V2 输入。 |

### 10 个正常 detail_content 对照

| ID | 标题 | action | 说明 |
|---|---|---|---|
| PUBEXP000031 | 清华大学保卫部 | approve | 正文段落 33，文本 2922 字；标题与主体匹配。 |
| PUBEXP000141 | 图书借还 | approve | 正文段落 31，文本 3405 字；标题与主体匹配。 |
| PUBEXP000101 | 信息系统开发 | reject | 正文段落 26，文本 2708 字；标题与主体匹配。 |
| PUBEXP000067 | 联系我们-清华大学图书馆 | approve | 正文段落 21，文本 1492 字；标题与主体匹配。 |
| PUBEXP000100 | 规划设计测评 | reject | 正文段落 20，文本 2386 字；标题与主体匹配。 |
| PUBEXP000021 | 常见问题（FAQ） | approve | 正文段落 14，文本 1805 字；标题与主体匹配。 |
| PUBEXP000023 | 服务 | approve | 正文段落 13，文本 1975 字；标题与主体匹配。 |
| PUBEXP000158 | 特别关注 | reject | 正文段落 12，文本 2741 字；标题与主体匹配。 |
| PUBEXP000152 | 读者咨询 | approve | 正文段落 10，文本 1156 字；标题与主体匹配。 |
| PUBEXP000159 | 领导关怀 | reject | 正文段落 10，文本 843 字；标题与主体匹配。 |

## G. 技术根因诊断

1. **动态正文未被抓取（主因）**：大量图书馆详情页在服务器返回的本地 Markdown 中只有“读取内容中，请等待…”，说明正文可能由 JavaScript/异步接口加载；当前 `requests` 抓取静态 HTML，未获得真实详情正文。
2. **Trafilatura 回退条件反向放大模板**：`parser.py` 在 Trafilatura 结果低于清理后全文 35% 时回退到整个 cleaned DOM。对导航很长、正文为空或异步加载的页面，这会把全站菜单/页尾当成正文。
3. **DOM 清理选择器覆盖不全**：只删除通用 `nav/header/footer` 类名；图书馆站的菜单、面包屑、咨询模块和馆链使用站点自定义结构，未被剔除。
4. **详情页 selector fallback 太窄且使用时机不足**：`article, main, .content, .article, .detail, .news_content, #content` 只在 Trafilatura 完全失败时尝试；Trafilatura 返回模板片段或加载占位时不会进入站点 selector 分支。
5. **缺少 title-content 一致性与抽取后质量闸门**：当前仅以 `plain >= 220`、字符种类等判断有效。长导航轻易越过阈值，没有检测正文段落、导航占比、加载占位或详情 URL 的正文缺失。
6. **列表页虽被用于链接发现，但候选本身仍入库**：爬虫会 follow 列表链接，却没有在保存候选时将 `list_page` 与详情页分层；因此目录、栏目和站点地图进入 Prompt V2。
7. **站点结构差异**：ITC、图书馆、保卫部 DOM 差异明显，单一通用抽取链难以稳定覆盖；需要 domain/template 级 selector 与去模板规则。

## H. 修复建议

### P0

1. 暂停 Public Expansion V2；在正文质量闸门通过前不继续扩库。
2. 修正文提取器：对加载占位、详情 URL 无正文、超高导航占比直接判失败，不允许回退到整页 body 后作为有效候选。
3. 对 `lib.tsinghua.edu.cn`、`www.itc.tsinghua.edu.cn` 至少建立站点 selector fallback，并在 Trafilatura 返回低质片段时也执行候选容器比选。
4. 对动态正文明确选择可审计方案：读取已有页面内嵌数据/本地可见接口结构，或在后续获准重抓时使用浏览器渲染；本轮不执行重抓。
5. 修复后重抓所有 `content_missing`/`navigation_only`，并对所有受影响的 Prompt V2 记录重新审核；approve 也必须重审。

### P1

1. 自动识别 `list_page`，保留发现价值但不作为完整知识正文送审；依据 `should_follow_links` 下钻政策、法规、招聘、办事、FAQ 和高价值资源目录。
2. 建立抽取评分：正文段落数、短行率、导航样式占比、链接文本占比、加载占位、标题覆盖度、详情 URL 先验；保留失败原因。
3. 将页头/页尾/咨询区/馆链做站点级剥离，避免 `template_polluted` 稀释 Prompt 输入。

### P2

1. 建立每个 domain 的小型回归样本集（正常详情、动态详情、列表、短页各若干），每次修改后自动比较。
2. 记录提取路径（Trafilatura、selector、rendered、fallback）与正文容器选择证据，便于监控站点模板变更。
3. 对 `thin_content` 与 `mixed_or_uncertain` 设置定期人工抽检，不用单一长度阈值裁决。

## 明确回答

1. 是否暂停 Public Expansion V2：**是**。
2. 是否先修正文提取器：**是**。
3. 是否做不同站点 selector fallback：**是，至少优先覆盖图书馆与 ITC**。
4. 是否自动识别 list_page 并下钻：**是，但按 `should_follow_links` 分流，不应无差别抓取新闻列表**。
5. 修复后是否重抓并重审现有 300 条：**应重抓明确失败条目；对缺失、导航、污染和列表所影响的 Prompt V2 结果重新审核。为保证批次一致性，建议最终对 300 条统一重跑质量闸门与 Prompt V2。**

## 最终结论

`CONTENT_EXTRACTION_CRITICAL`

当前大量数据没有获得真实主体正文，Prompt V2 结果的可信度受到明显影响。应暂停扩库，先修复正文提取与质量闸门，再重抓并重新审核受影响数据。
