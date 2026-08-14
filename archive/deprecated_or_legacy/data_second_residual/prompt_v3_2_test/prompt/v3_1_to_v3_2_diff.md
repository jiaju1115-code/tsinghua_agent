# Prompt V3.1 → V3.2 定向修订说明

## 修改内容

1. 新增独立的主题相关性轴：先识别页面核心主题，再按 `high / medium / low` 判断是否属于面向学生和校园用户的目标知识。
2. 将 `out_of_scope` 正式替换为 `topic_irrelevant`。新语义既包括外校/泛行业内容，也包括“100% 与清华有关，但只是成果、获奖、人物、领导、签约或普通活动”的低复用页面。
3. 明确先主题、后时效：low 页面直接 `topic_irrelevant`；只有主题相关但已失效时才使用 `expired_event`。
4. 细化科研与教学边界：科研机构、实验室、平台、数据库和学生机会可保留；科研成果、教师获奖和教学成果宣传通常拒绝。
5. 用 `candidate_user_question` 检查主题价值，禁止为单篇新闻强行制造低频事件问题。
6. 调整 `active_time_bound`：剩余有效期不足或等于 60 天原则上 review；超过 60 天且 high、信息完整、使用价值明确时允许 approve。
7. 新增输出字段 `topic_relevance`、`valid_from`、`valid_until`；日期只能来自正文明确证据。

## 保持不变

- Quality Gate 和 Prompt 的职责边界；
- “清华校园知识库”不限于办事指南的总体方向；
- 长期校园服务、机构、数据库、科研平台与学生可利用资源的保护原则；
- `historical_but_valuable` 仅用于当前仍存在的持续事实；
- category、content_type、audience、证据、possible_duplicate 等原有字段语义；
- 固定 30 条正文、人工标签、模型、temperature、并发和其他 API 参数。
