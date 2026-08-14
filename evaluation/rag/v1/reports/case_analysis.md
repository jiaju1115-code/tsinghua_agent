# Query Case Analysis

Cases are selected only from queries with a reliable expected source. Rank 999 denotes not retrieved in Top-10.

## Sparse clearly wins (4 observed)

- **PROV-003 — 学生不服学校处理或纪律处分时，校内申诉由哪个机构办理？**: expected source `STGPUB-0030`; TF-IDF rank=2, Dense rank=8.
- **RET-06 — 清华学生奖学金、助学金申请和评选办法是什么？**: expected source `STGPUB-0029`; TF-IDF rank=1, Dense rank=3.
- **RET-03 — 清华校园网如何接入，账号或网络故障如何处理？**: expected source `STGPUB-0104`; TF-IDF rank=1, Dense rank=2.
- **PROV-025 — 清华通讯作者在IEEE开放获取期刊发表论文有何APC优惠？**: expected source `STGPUB-0203`; TF-IDF rank=1, Dense rank=2.

Lexical retrieval wins when exact policy names, system names, form names, or uncommon service terms occur verbatim in the source.

## Dense clearly wins (9 observed)

- **PROV-016 — 清华师生如何使用馆际互借服务获取外馆文献？**: expected source `STGPUB-0158`; TF-IDF rank=None, Dense rank=1.
- **PROV-006 — 给住在清华学生社区的同学寄快递时，邮寄地址和邮编在哪里查？**: expected source `STGPUB-0067`; TF-IDF rank=None, Dense rank=5.
- **PROV-028 — 如何查询清华各院系的单位号、简称和英文名称？**: expected source `RESV1-0010`; TF-IDF rank=8, Dense rank=1.
- **PROV-008 — 教职工想查询校内教工餐厅信息，应查看哪份校园服务资料？**: expected source `STGPUB-0074`; TF-IDF rank=8, Dense rank=2.
- **RET-01 — 如何查询清华大学本科生学籍、注册与培养管理规定？**: expected source `STGPUB-0047`; TF-IDF rank=6, Dense rank=1.

Dense retrieval wins when the query paraphrases the service need and the source uses different wording.

## Hybrid creates a strict rank gain (1 observed)

- **PROV-006 — 给住在清华学生社区的同学寄快递时，邮寄地址和邮编在哪里查？**: expected source `STGPUB-0067`; TF-IDF=None, Dense=5, Hybrid=4. RRF promoted complementary candidates.

A strict gain here means the expected source ranks above both single retrievers; merely tying the better retriever is not counted.

## Reranker corrections (4 observed)

- **PROV-003 — 学生不服学校处理或纪律处分时，校内申诉由哪个机构办理？**: Hybrid rank=5, reranked rank=2; cross-encoder corrected candidate order.
- **PROV-006 — 给住在清华学生社区的同学寄快递时，邮寄地址和邮编在哪里查？**: Hybrid rank=4, reranked rank=3; cross-encoder corrected candidate order.
- **PROV-008 — 教职工想查询校内教工餐厅信息，应查看哪份校园服务资料？**: Hybrid rank=2, reranked rank=1; cross-encoder corrected candidate order.
- **PROV-025 — 清华通讯作者在IEEE开放获取期刊发表论文有何APC优惠？**: Hybrid rank=2, reranked rank=1; cross-encoder corrected candidate order.
