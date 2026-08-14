# CODEX_BLIND_TEST_V1 — PHASE 2 正式评估

## 1. 实验定义

当前实验为 **Prompt V3.2 + Codex**，50条冻结盲测，以冻结Human标签为正式参考。原API实验 **Prompt V3.2 + gpt-5.4-mini** 仍为 `EVALUATION_BLOCKED`，原因是第三方API生成链路504；两者不混淆。

## 2. 隔离与freeze证明

PHASE 1在读取Human前完成50/50预测并冻结；PHASE 2开始前复算Prediction SHA匹配。Prediction SHA：`07ecca5b83a1f1a0fe63fe416c404589114c8c59aef87ecadd82966bf09f6847`。Human SHA：`ec1e846091532205a04480320a4a4572d99526f58fe8a9037390bed4bc502ca6`。Human=50、Codex=50、matched=50、unmatched=0、duplicate=0。

## 3. Action一致率

匹配 46/50，分歧 4，accuracy **92.0%**。

| Human \ Codex | approve | review | reject |
|---|---:|---:|---:|
| approve | 26 | 1 | 0 |
| review | 1 | 0 | 0 |
| reject | 2 | 0 | 20 |

Approve precision 89.7%；Approve recall 96.3%。Reject precision 100.0%；Reject recall 90.9%。False Accept=2（BLINDV1-010、014）；False Reject=0。

## 4. Topic relevance

匹配 37/50，accuracy **74.0%**。Human high/medium/low=31/11/8；Codex=30/2/18。

| Human \ Codex | high | medium | low |
|---|---:|---:|---:|
| high | 28 | 1 | 2 |
| medium | 2 | 1 | 8 |
| low | 0 | 0 | 8 |

## 5. Medium专项

Human medium=11，Codex medium=2，准确匹配=1；Human medium→Codex high=2，→low=8；Codex medium→Human high=1，→low=0。Codex确实很少使用medium，并明显将边界样本二分为high/low；但多处Human medium本身与Prompt的low事件规则存在口径张力。

## 6. Reject type

Human reject且reject_type有效 n=22；匹配=10；accuracy **45.5%**。

| Human \ Codex | topic_irrelevant | expired_event | other |
|---|---:|---:|---:|
| topic_irrelevant | 8 | 0 | 0 |
| expired_event | 10 | 2 | 0 |
| other | 0 | 0 | 0 |

主要差异是Human把多类普通活动、获奖、领导、签约旧闻标为expired_event，而Codex按Prompt强制顺序使用topic_irrelevant。

## 7. Random vs Targeted

- random：n=25，matches=21，accuracy=84.0%，FA=2，FR=0
- targeted：n=25，matches=25，accuracy=100.0%，FA=0，FR=0

## 8. 专项主题表现

科研成果新闻稳定过滤（001、012、027等均reject）；人物/获奖稳定过滤（028-030均reject）；校领导活动稳定过滤（031-032均reject）；纯签约新闻033、034均reject；普通讲座/活动总体过滤，但014因持续形成音乐讲堂而被Codex approve；长期校园服务无false reject；科研资源无false reject；校园网络、机构、图书馆核心事务稳定保留。

## 9. 全部Action分歧

- BLINDV1-008：Human=approve，Codex=review；Codex flags uncertain currency of an old FAQ; Human accepts it as evergreen.
- BLINDV1-010：Human=reject，Codex=approve；Codex preserves organization history; Human treats the old internal activity chronology as expired.
- BLINDV1-014：Human=reject，Codex=approve；Codex protects the lasting music venue created by the event; Human labels the event page expired.
- BLINDV1-018：Human=review，Codex=approve；Mixed landing page contains an active summer notice; Codex emphasizes evergreen library resources.

## 10. Human label questions

共11条。集中于Human使用expired_event标注Prompt明文要求优先topic_irrelevant的普通活动、获奖、领导与签约页面，以及两个“历史形成持续实体”的边界页。疑问仅单列，不修改Human，主指标仍严格采用冻结标签。

## 11. 系统性错误判断

Codex low+approve=0，满足硬约束。未发现科研成果、人物获奖、领导活动或签约新闻的系统性误收；未发现长期服务、科研资源或校园核心事务的系统性误杀。存在medium使用不足，以及2条event-vs-service/历史价值边界误收，但不构成广泛系统性错误。按Codex content_type观察，错误集中在mixed/news_event边界；多数service_entry、procedure_guide、resource_directory、organization_intro表现稳定。类别未覆盖项应标记NOT_COVERED，不据此声称验证。

### Domain分析

- `lib.tsinghua.edu.cn`：n=41，37/41，90.2%，FA=2，FR=0。
- `www.itc.tsinghua.edu.cn`：n=7，7/7，100%，FA=0，FR=0。
- `peace.tsinghua.edu.cn`：n=2，2/2，100%，FA=0，FR=0；样本较少，仅为观察性结果。

### Content type分析

- service_entry 8/8、procedure_guide 3/3、policy 3/3、resource_directory 4/4、organization_intro 6/6、current_notice 5/5、research_news 2/2、achievement_report 4/4。
- news_event 9/10，错误1条（BLINDV1-014）。
- mixed 1/3，错误集中于历史价值与当前服务的混合页面（BLINDV1-010、018）。
- faq 0/1，仅1条，属于approve/review时效边界。
- promotional_content 1/1，仅1条。

### Category分析

实际覆盖中，非目标范围18/18、科研参与与资源导航6/6、网络与信息化3/3、校园机构与部门3/3；图书馆服务12/15，校园文化与历史1/2。清华基本信息、奖助与资助、教学与培养各仅1条，结果仅供观察。教务与学籍、学生事务、住宿服务、餐饮服务、交通服务、医疗健康、体育与场馆、国际事务与签证、就业与职业发展、校园访问、校园综合服务均为 `NOT_COVERED`，不得声称已验证。

## 12. Prompt冻结建议

Action accuracy=92.0%，Approve precision=89.7%，low+approve=0，无明显系统性错误。建议 **YES_WITH_HUMAN_SAMPLING**：冻结Prompt V3.2用于当前生产，同时对历史形成持续设施、混合落地页和medium边界做人工抽样。

## 13. 最终结论

**CODEX_BLIND_TEST_PASS_WITH_MINOR_ISSUES**
