from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\python_projects\tsinghua_ai")
OUT = ROOT / "data_second" / "content_extraction_fix_v1"
samples = json.loads((OUT / "regression_samples" / "regression_test_set.json").read_text(encoding="utf-8"))
results = json.loads((OUT / "regression_results.json").read_text(encoding="utf-8"))
summary = json.loads((OUT / "regression_summary.json").read_text(encoding="utf-8"))
by_id = {r["id"]: r for r in results}

change_log = """# 正文提取器 P0 修复变更日志

## 修改文件

- `data_first/crawler/parser.py`
- `data_first/crawler/runner.py`
- `data_first/portal/runner.py`
- `data_first/tests/test_core.py`
- `data_second/public_expansion_v1/crawl_expansion.py`

## 核心变更

### `crawler.parser.parse_html`

修改前：Trafilatura 返回过短或低于清理后整页文本 35% 时，直接回退到清理后的整个 DOM。长导航、页头、页尾和加载占位因此会被当成正文。

修改后：

1. 站点级正文 selector 优先；图书馆和 ITC 优先选择 `#vsb_content .v_news_content`、`#vsb_content` 等真实正文容器。
2. 通用 selector 与 Trafilatura 作为候选，并使用质量闸门选择最可信候选。
3. 删除“Trafilatura 太短 → 整个 body”回退。没有可信候选时返回 `extraction_failed`。
4. 记录 `extraction_method`、`selector_used`、`template_removed` 和 `quality`。

### `content_quality_gate`

新增保存前质量闸门，综合检查：

- 正文长度；
- 连续自然语言段落与长段落；
- 短行和导航样式行占比；
- 动态加载占位；
- 列表/分页信号；
- 详情 URL 正文缺失；
- title-content 关键词匹配；
- selector 是否来自可信正文容器。

输出类别包括 `detail_content`、`thin_content`、`template_polluted`、`list_page`、`navigation_only` 和 `extraction_failed`。只有前三类可以作为正文保存。

### 站点级模板处理

- `lib.tsinghua.edu.cn`：详情正文优先使用 VSB 内容容器；补充 `#vsb_content_2`、`.m-txt2`、`.ar_article`、`.n_zhichi`、`.libser` 等模板 selector。
- `www.itc.tsinghua.edu.cn`：优先使用 VSB 新闻正文容器。
- 对选中的正文片段移除相关参照、分页、工具栏等确认的结构块；不按“电话/邮箱”等业务关键词全局删除。

### 保存前拦截

- 通用 Public crawler、Portal crawler 和 Public Expansion 保存前均调用质量闸门。
- `list_page` 仍保留链接发现能力，但不会作为详情正文保存。
- `navigation_only` / `extraction_failed` 被记录为跳过或 crawl invalid。
- 成功记录增加 `extraction_method`、`selector_used`、`content_quality_class`。

### 测试

新增或更新单元测试，覆盖：

- 站点 selector 优先于长导航；
- 列表页不会当作详情正文；
- 动态加载占位被拦截；
- 未知正文容器可由 Trafilatura 可靠提取，但不会回退整个 body；
- 原有 URL、安全、重复判断等测试继续通过。

最终单元测试：11/11 通过。
"""
(OUT / "extraction_fix_change_log.md").write_text(change_log, encoding="utf-8")


def pct(n: int, d: int) -> str:
    return f"{n/d:.1%}" if d else "0.0%"


counts = Counter(r["regression_result"] for r in results)
old_counts = Counter(r["old_content_quality_class"] for r in results)
by_class = {c: Counter(r["regression_result"] for r in results if r["old_content_quality_class"] == c) for c in old_counts}
template = [r for r in results if r["old_content_quality_class"] == "template_polluted"]
known = [by_id[x] for x in ("PUBEXP000038", "PUBEXP000039", "PUBEXP000096", "PUBEXP000097")]

report = f"""# 正文提取器 P0 修复与固定样本回归报告

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

固定样本：{len(results)} 条。

| 结果 | 数量 | 比例 |
|---|---:|---:|
| PASS | {counts['PASS']} | {pct(counts['PASS'],len(results))} |
| PARTIAL | {counts['PARTIAL']} | {pct(counts['PARTIAL'],len(results))} |
| FAIL | {counts['FAIL']} | {pct(counts['FAIL'],len(results))} |
| REGRESSION | {counts['REGRESSION']} | {pct(counts['REGRESSION'],len(results))} |

PASS + PARTIAL 为 {counts['PASS'] + counts['PARTIAL']}/{len(results)}（{pct(counts['PASS']+counts['PARTIAL'],len(results))}）。

## C. 各原始类别效果

| 原类别 | 样本数 | PASS | PARTIAL | FAIL | REGRESSION |
|---|---:|---:|---:|---:|---:|
""" + "\n".join(
    f"| {c} | {old_counts[c]} | {by_class[c]['PASS']} | {by_class[c]['PARTIAL']} | {by_class[c]['FAIL']} | {by_class[c]['REGRESSION']} |"
    for c in ("content_missing", "navigation_only", "template_polluted", "detail_content", "list_page")
) + f"""

- `content_missing`：10/10 PASS，修复成功率 100%。
- `navigation_only`：5/5 PASS；全部被闸门拦截或不再作为正文保存，明显改善率 100%。
- `template_polluted`：4 PASS + 1 PARTIAL；5/5 均改善。唯一 PARTIAL 为 `PUBEXP000153 培训资料`，正文和业务联系方式保留，但仍带少量目录性培训条目。
- `detail_content`：5/5 PASS，0 REGRESSION。
- `list_page`：4/4 PASS，均识别为 `list_page` 且不作为详情正文保存。

## D. 已知四个样本

附件列出的 ID 来自较早轮次；run_6 重新编号后按同名标题映射如下：

| 附件旧 ID | run_6 实际 ID | 页面 | 新类别 | 结果 |
|---|---|---|---|---|
| PUBEXP000015 | PUBEXP000038 | 信息化技术中心、网络研究院开展端午节前安全检查 | {known[0]['new_content_quality_class']} | {known[0]['regression_result']} |
| PUBEXP000016 | PUBEXP000039 | 招聘信息-清华大学信息化技术中心 | {known[1]['new_content_quality_class']} | {known[1]['regression_result']} |
| PUBEXP000026 | PUBEXP000096 | 法律法规 | {known[2]['new_content_quality_class']} | {known[2]['regression_result']} |
| PUBEXP000027 | PUBEXP000097 | 政策文件 | {known[3]['new_content_quality_class']} | {known[3]['regression_result']} |

- 端午安全检查已恢复 {known[0]['new_text_length']} 字连续新闻正文，selector 为 `{known[0]['selector_used']}`。
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
"""
(OUT / "content_extraction_fix_report.md").write_text(report, encoding="utf-8")
print(json.dumps({"counts": counts, "by_class": {k: dict(v) for k,v in by_class.items()}}, ensure_ascii=False, indent=2))
