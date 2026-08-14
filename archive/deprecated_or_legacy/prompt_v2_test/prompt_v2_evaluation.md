# Prompt V2：Public 固定30篇回归测试评估

## A. 测试基本情况

- 测试文章数：30；样本 ID 与 AI_v1 的 external_llm 原始30篇完全一致。
- V1：approve 30，review 0，reject 0。
- V2：approve 14，review 3，reject 13。
- 所有30篇均在 gold_label.xlsx 中存在人工标签。

## B. V1 → V2 变化

- approve → approve：14
- approve → review：3
- approve → reject：13
- 其他变化：0

V2 已打破 V1 的 30/30 approve，并对新闻、成果宣传、合作概况、会议和低复用首页进行实质筛选。

### V1 approve → V2 reject

- **清华大学（THU000001）**：news_event；V1=approve，V2=reject，human=approve。首页不能因权威而自动收录；当前抓取内容以新闻和宣传为主，不能稳定回答具体校园问题。
- **清华大学教育基金会（THU000003）**：promotional_content；V1=approve，V2=reject，human=reject。内容主要宣传基金会项目和活动，无法回答学生如何申请或办理资助。
- **Tsinghua University（THU000004）**：promotional_content；V1=approve，V2=reject，human=approve。英文首页知识密度低且与中文首页重复，不能作为独立校园办事知识条目。
- **清华新闻-清华大学（THU000005）**：news_event；V1=approve，V2=reject，human=reject。综合新闻频道属于事件信息流，不是可复用的校园生活知识。
- **科研合作-清华大学（THU000024）**：organization_intro；V1=approve，V2=reject，human=reject。面向机构合作的概况介绍，不能帮助学生实际发现或参与科研。
- **学术交流-清华大学（THU000030）**：organization_intro；V1=approve，V2=reject，human=reject。泛学术介绍不能回答学生如何参与或办理交流事务。
- **招生就业-清华大学（THU000031）**：organization_intro；V1=approve，V2=reject，human=reject。标题虽含招生就业，正文只是统计与成果概况，不具备学生服务价值。
- **国内合作-清华大学（THU000033）**：organization_intro；V1=approve，V2=reject，human=reject。机构合作概况不能回答学生的实际校园事务或参与问题。
- **教学成果-清华大学（THU000046）**：achievement_report；V1=approve，V2=reject，human=reject。典型教学成果宣传，不能直接解决学生问题。
- **发展概况-清华大学（THU000055）**：achievement_report；V1=approve，V2=reject，human=approve。属于建设成效宣传，不能回答学生如何使用具体教学服务。
- **科研项目概况-清华大学（THU000064）**：research_news；V1=approve，V2=reject，human=reject。科研统计概况不是学生科研资源导航，并与科研项目栏目存在主题重叠。
- **国际会议-清华大学（THU000074）**：achievement_report；V1=approve，V2=reject，human=reject。历史会议与影响力介绍属于成果概况，且内容过时。
- **教工活动-清华大学（THU000091）**：achievement_report；V1=approve，V2=reject，human=reject。教职工活动及教学比赛成效与学生办事无直接关系。

### V1 approve → V2 review

- **统计资料-清华大学（THU000013）**：organization_intro；V1=approve，V2=review，human=approve。具有基础事实查询价值，但偏离校园办事核心且需持续更新，建议人工确认收录范围。
- **清华大学体育部（THU000027）**：mixed；V1=approve，V2=review，human=approve。领域本身高价值，但这次抓取内容不支持直接 approve，需要核验首页是否能稳定导向学生服务。
- **合作交流-清华大学（THU000032）**：mixed；V1=approve，V2=review，human=reject。存在真实学生交流导航价值，但页面混杂宣传新闻，需人工确认或拆分具体服务页。

### V1 approve → V2 approve

- **访客-清华大学（THU000002）**：service_entry；V1=approve，V2=approve，human=approve。属于明确的访客服务导航，可引导真实预约与到校问题。
- **清华大学图书馆（THU000010）**：service_entry；V1=approve，V2=approve，human=approve。包含直接可用的图书馆服务信息和稳定咨询入口。
- **科研项目-清华大学（THU000022）**：resource_directory；V1=approve，V2=approve，human=approve。作为科研项目资源入口能帮助学生继续发现科研方向和机会，符合科研导航例外。
- **科研机构-清华大学（THU000023）**：resource_directory；V1=approve，V2=approve，human=approve。可帮助学生定位科研机构体系和进一步寻找实验室资源，属于科研资源导航。
- **清华大学医院（THU000028）**：service_entry；V1=approve，V2=approve，human=approve。核心医疗服务入口及指南导航价值明确；应采集具体指南并过滤新闻。
- **办事指南-清华大学研究生院（THU000029）**：procedure_guide；V1=approve，V2=approve，human=approve。直接回答高频研究生办事问题，属于高价值指南目录。
- **学生活动-清华大学（THU000036）**：resource_directory；V1=approve，V2=approve，human=reject。不是单次活动回顾，而是稳定的学生讲座资源导航，能帮助学生发现校园活动渠道。
- **特色项目-清华大学（THU000047）**：resource_directory；V1=approve，V2=approve，human=approve。能帮助学生理解和选择培养项目，属于稳定教育资源导航，不是成果宣传。
- **学术学位教育-清华大学（THU000048）**：policy；V1=approve，V2=approve，human=approve。包含正式培养制度与基金政策，可直接回答研究生培养和资助问题。
- **专业学位教育-清华大学（THU000049）**：resource_directory；V1=approve，V2=approve，human=approve。能够帮助专业学位学生了解培养资源和实践渠道，具有稳定导航价值。
- **奖助体系-清华大学（THU000054）**：policy；V1=approve，V2=approve，human=approve。直接回答奖助政策和申请资格，是高价值校园事务知识。
- **校园交通-清华大学（THU000092）**：service_entry；V1=approve，V2=approve，human=approve。直接回答校园出行问题，具有明确可执行信息。
- **周边交通-清华大学（THU000093）**：procedure_guide；V1=approve，V2=approve，human=approve。可直接回答到校路线，是高频校园访问与出行信息。
- **服务信息-清华大学（THU000095）**：service_entry；V1=approve，V2=approve，human=approve。是高频校园服务联系目录，可直接支持办事与应急查询。

## C. 与人工标签比较

- V1-human：一致 18，不一致 12，一致率 60.0%。
- V2-human：一致 23，不一致 7，一致率 76.7%。
- 按 approve/review/reject 三分类原值比较，未做二分类转换。

V2 与人工共有 7 条不一致，但以下差异不应机械改成与人工一致：

- **清华大学（THU000001）**：news_event；V1=approve，V2=reject，human=approve。首页不能因权威而自动收录；当前抓取内容以新闻和宣传为主，不能稳定回答具体校园问题。
- **Tsinghua University（THU000004）**：promotional_content；V1=approve，V2=reject，human=approve。英文首页知识密度低且与中文首页重复，不能作为独立校园办事知识条目。
- **统计资料-清华大学（THU000013）**：organization_intro；V1=approve，V2=review，human=approve。具有基础事实查询价值，但偏离校园办事核心且需持续更新，建议人工确认收录范围。
- **清华大学体育部（THU000027）**：mixed；V1=approve，V2=review，human=approve。领域本身高价值，但这次抓取内容不支持直接 approve，需要核验首页是否能稳定导向学生服务。
- **合作交流-清华大学（THU000032）**：mixed；V1=approve，V2=review，human=reject。存在真实学生交流导航价值，但页面混杂宣传新闻，需人工确认或拆分具体服务页。
- **学生活动-清华大学（THU000036）**：resource_directory；V1=approve，V2=approve，human=reject。不是单次活动回顾，而是稳定的学生讲座资源导航，能帮助学生发现校园活动渠道。
- **发展概况-清华大学（THU000055）**：achievement_report；V1=approve，V2=reject，human=approve。属于建设成效宣传，不能回答学生如何使用具体教学服务。

## D. V2 成功修正的典型案例

- **清华新闻**：综合新闻页包含科研突破、会议、人物和访问报道，V2 reject。
- **清华大学教育基金会**：正文以捐赠动态和活动宣传为主，无学生申请入口，V2 reject。
- **教学成果**：主体是获奖成果与教材荣誉，不是学生可执行知识，V2 reject。
- **科研项目概况**：只有年度立项与经费统计，无项目目录或参与路径，V2 reject。
- **国际会议**：历史会议规模和名单，无当前报名或参与入口，V2 reject。
- **教工活动**：青年教师比赛成效，受众和内容均不面向学生办事，V2 reject。
- **科研项目、科研机构**：作为学生探索科研方向和机构体系的资源导航，V2 保留为 approve，没有把科研内容一刀切。

## E. V2 可能出现的新问题

1. **资源导航的准入边界仍需校准**：科研项目/机构和学生活动被保留，虽然符合已确认的“资源发现”价值，但抓取正文中的具体参与入口有限。扩大规模时应要求 positive_evidence 明确指出目录、链接、联系人或稳定品牌。
2. **聚合首页容易混合高价值服务与新闻**：体育部、校医院等首页包含服务入口，也含新闻和宣传。应优先采集具体服务页，并避免将首页全文直接作为最终知识块。
3. **时效维护仍是独立问题**：交通时间、电话、年度统计和项目规模即使准入正确，也需要 freshness 策略。
4. **review 的触发需保持严格**：本次仅3条 review，分别因低优先级动态统计、体育首页抓取证据不足、合作交流混合学生资源与宣传。

## F. 疑似人工标注问题

- **THU000036 学生活动**：人工 reject（新闻为主），但正文实际是多个长期讲座论坛品牌的结构化介绍，不是单次活动回顾。若知识库包含校园资源发现，V2 approve 更合理。
- **THU000001/THU000004 中英文首页**：人工 approve；抓取内容分别以新闻活动和宣传口号为主，且两者重复。V2 reject 更符合知识条目粒度。
- **THU000013 统计资料**：人工 approve；V2 review。它能回答学校规模事实，但不是校园办事核心且年度变化，是否纳入取决于知识库范围。
- **THU000047/THU000048/THU000049**：人工 approve，V2同意；正文分别提供培养项目导航、正式培养规定和专业学位实践资源，具备学生使用价值。
- **THU000031 招生就业**：人工 reject，V2同意。正文只有规模、行业和就业排名，没有招生/就业办理服务。

## G. 最终结论

### PASS_WITH_MINOR_ISSUES

Prompt V2 已具备扩大 Public 审核规模的基本条件：它把30/30 approve改为13 approve、3 review、14 reject，并将三分类人工一致率从 60.0% 提升到 76.7%。它能稳定过滤综合新闻、宣传、教学成果、历史会议、合作概况和科研统计，同时保留办事指南、医疗、交通、图书馆、奖助政策及科研资源导航。

仍需在扩大前保留小比例人工抽检，重点监控资源导航证据是否充分、聚合首页是否混入新闻，以及时效字段维护。
