# 正文提取器 P0 修复变更日志

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
