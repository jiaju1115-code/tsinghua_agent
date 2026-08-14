# 正文提取器 P0 修复与固定样本回归报告

## 最终结论

`EXTRACTION_FIX_PASS`

P0 修复有效，可以进入下一阶段“重抓历史失败页面”，但本轮没有自动重抓 174 条、没有重跑全部 300 条、没有调用 Prompt V2，也没有扩库。

## A. 修改内容

### 动态正文

对图书馆和 ITC 失败样本检查公开页面 HTML 后确认：正文不需要额外 API、XHR、登录或浏览器渲染，真实正文已经嵌入静态 HTML 的 VSB 内容容器，主要为：

- `#vsb_content .v_news_content`
- `#vsb_content`
- `.v_news_content`
- 部分模板的 `#vsb_content_2`

旧 Markdown 中的“读取内容中，请等待...”来自正文下方“相关参照”异步模块，并非正文自身。旧提取器选错块和整页回退导致真实正文丢失。

- 内容来源：公开详情页自身 HTML。
- 公开可访问：是。
- 身份认证：不需要。
- 是否依赖 content ID/API：不需要额外接口；URL 中页面 ID 仅用于正常公开页面路由。
- 批量适用性：适合，selector 稳定且成本低。
- 频率风险：与普通公开网页抓取相同，应继续限速并尊重 robots/站点负载。
- `dynamic_fetch_used`：本回归均为 `false`，因为不需要额外动态请求。

### fallback

彻底删除“Trafilatura 太短 → cleaned body”逻辑。现在只有可信 selector、通过闸门的 Trafilatura 或通用正文容器可以成为正文；否则返回 `extraction_failed`。

### selector

为 `lib.tsinghua.edu.cn` 与 `www.itc.tsinghua.edu.cn` 增加分模板 selector 列表，并让 selector 在 Trafilatura 为空、过短、导航过高、缺少段落或出现占位时都参与候选比较。

### 模板清洗

按 DOM 结构剥离 header/footer/nav、相关参照、工具栏、分页等确认的模板块。没有全局删除电话、邮箱、地址、办理时间等词，因此业务联系方式得到保留。

### quality gate

新增 `content_quality_gate`，并接入 Public、Public Expansion 与 Portal 的保存前流程。列表页保留链接发现，但不再被当作详情正文保存。

## B. 回归结果

固定样本：29 条。

| 结果 | 数量 | 比例 |
|---|---:|---:|
| PASS | 28 | 96.6% |
| PARTIAL | 1 | 3.4% |
| FAIL | 0 | 0.0% |
| REGRESSION | 0 | 0.0% |

PASS + PARTIAL 为 29/29（100.0%）。

## C. 各原始类别效果

| 原类别 | 样本数 | PASS | PARTIAL | FAIL | REGRESSION |
|---|---:|---:|---:|---:|---:|
| content_missing | 10 | 10 | 0 | 0 | 0 |
| navigation_only | 5 | 5 | 0 | 0 | 0 |
| template_polluted | 5 | 4 | 1 | 0 | 0 |
| detail_content | 5 | 5 | 0 | 0 | 0 |
| list_page | 4 | 4 | 0 | 0 | 0 |

- `content_missing`：10/10 PASS，修复成功率 100%。
- `navigation_only`：5/5 PASS；全部被闸门拦截或不再作为正文保存，明显改善率 100%。
- `template_polluted`：4 PASS + 1 PARTIAL；5/5 均改善。唯一 PARTIAL 为 `PUBEXP000153 培训资料`，正文和业务联系方式保留，但仍带少量目录性培训条目。
- `detail_content`：5/5 PASS，0 REGRESSION。
- `list_page`：4/4 PASS，均识别为 `list_page` 且不作为详情正文保存。

## D. 已知四个样本

附件列出的 ID 来自较早轮次；run_6 重新编号后按同名标题映射如下：

| 附件旧 ID | run_6 实际 ID | 页面 | 新类别 | 结果 |
|---|---|---|---|---|
| PUBEXP000015 | PUBEXP000038 | 信息化技术中心、网络研究院开展端午节前安全检查 | detail_content | PASS |
| PUBEXP000016 | PUBEXP000039 | 招聘信息-清华大学信息化技术中心 | list_page | PASS |
| PUBEXP000026 | PUBEXP000096 | 法律法规 | list_page | PASS |
| PUBEXP000027 | PUBEXP000097 | 政策文件 | list_page | PASS |

- 端午安全检查已恢复 388 字连续新闻正文，selector 为 `#vsb_content .v_news_content`。
- 招聘、法律法规、政策文件均稳定识别为 `list_page`，没有伪装成完整详情正文。

## E. 图书馆动态正文结论

已可靠解决本次回归覆盖的图书馆详情正文问题。10 个原 `content_missing` 样本全部恢复可读主体。修复方式不是调用未知接口或浏览器执行脚本，而是直接选择公开静态 HTML 中已经存在的正文容器；“读取内容中”仅属于相关参照模块。

## F. 正常页面是否受损

没有。5 个 `detail_content` 对照样本全部 PASS，REGRESSION 为 0。电话号码、邮箱、地址、办理时间等业务信息在相应样本中仍保留。

## G. quality gate 效果

- 9 个非详情候选被成功拦截：5 个 `navigation_only` + 4 个 `list_page`。
- 仍有导航内容无正文却通过：0。
- 正常详情误拦截：0/5。
- 正常短页面误拦截：本固定集中未观察到；短但有实质正文的图书馆通知被识别为 `thin_content` 并通过。

## H. 测试范围与限制

- 只重新请求了固定 29 个公开 URL。
- 结果证明 P0 机制和两大重点站点模板有效，但不能替代后续对全部历史失败页面的重抓验证。
- 图书馆与 ITC 若未来更换 VSB 模板，需要依靠 `extraction_method`、`selector_used` 和质量闸门监控失效。
- 本轮没有修改 run_6 原 Markdown 或正文质量诊断文件。

## 下一步建议（本轮不执行）

1. 使用修复后的提取器重抓历史 `content_missing/navigation_only`。
2. 对新结果重新运行正文质量诊断。
3. 仅对通过质量闸门的记录重新执行 Prompt V2。
4. 在重抓前先保留当前 run_6 作为只读基线。
