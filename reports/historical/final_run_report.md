# 第二阶段首轮运行总报告

时间：2026-08-09（Asia/Shanghai）

## 原始证据保护

- `data_first` 运行前后逐文件 SHA256 完全一致：是。
- 校验文件：192。
- 没有删除、移动、重命名、修改或覆盖第一阶段文件。
- 临时API Key仅在 `.env`；对 `data_second` 其他文件扫描，真实Key泄漏文件数为0。

## Candidate Index

- Candidate总数：139
- V1.1 Public：86
- Legacy Public独立候选：26
- Portal：27
- 因三键重复排除：0（第一阶段已在落盘前处理精确重复）
- Public合计：112

## MomoAPI

- 官方服务地址：`https://momoapi.cc`
- OpenAI-compatible Base URL：`https://momoapi.cc/v1`
- 接口：`/v1/models`、`/v1/chat/completions`
- 实际模型：`gpt-5.4-mini`
- `/v1/models`实际返回模型数：6
- 无敏感JSON Smoke Test：成功
- Public真实审核：30，达到硬上限后停止
- Portal外部调用：0
- 401/403/429：均未出现
- API usage：prompt 54,600；completion 12,628；total 67,228 tokens

## Public AI结果

- approve：30
- review：0
- reject：0

该分布明显异常。模型把低相关新闻、基金会、科研和合作介绍也全部approve，表现出严重的权威性偏置和过度批准。模型原始结果已保留，没有人工篡改或付费重跑；应先升级Prompt，再扩大审核。

Public freshness：current 21、possibly_outdated 8、outdated 0、unknown 1。

Public time_sensitivity：low 20、medium 9、high 1。

Public personal_data_risk：none 22、low 8、medium/high 0。低风险主要是公开服务联系方式等信号，已由质量报告要求人工检查。

Public possible_conflict：30条均为false。

## Portal本地审核

- 全部本地审核：27
- 进入人工review：24
- 进入本地reject候选：3
- 外部API正文发送：0
- 人工审核表：27条

Portal本地审核仍偏保守：带有“后勤服务”等字样的人物标兵稿可能被送入Review而不是Reject，下一版本应让明确人物宣传规则优先于“服务”关键词。

## 全部57条审核结果分布

分类：校园办事7、校园生活29、新生入校1、规章制度1、校园通知3、其他16。

Freshness：current35、possibly_outdated16、outdated5、unknown1。

Time sensitivity：low20、medium25、high12。

## 20个Public样本

1. `THU000029` 研究生院办事指南：96/88，办事指南，approve。
2. `THU000095` 服务信息：89/72，服务指南，approve。
3. `THU000027` 体育部：92/68，部门介绍，approve。
4. `THU000010` 图书馆：95/84，部门介绍，approve。
5. `THU000028` 校医院：95/88，部门介绍，approve。
6. `THU000092` 校园交通：93/88，服务指南，approve；高时效异常。
7. `THU000093` 周边交通：94/82，服务指南，approve。
8. `THU000036` 学生活动：88/74，部门介绍，approve。
9. `THU000074` 国际会议：72/58，科研信息，approve。
10. `THU000091` 教工活动：68/42，部门介绍，approve。
11. `THU000047` 特色项目：82/79，其他，approve。
12. `THU000003` 教育基金会：28/22，新闻，approve；明显异常。
13. `THU000049` 专业学位教育：42/58，部门介绍，approve。
14. `THU000013` 统计资料：42/38，其他，approve。
15. `THU000030` 学术交流：62/55，部门介绍，approve。
16. `THU000005` 清华新闻：28/34，新闻，approve；明显异常。
17. `THU000046` 教学成果：58/62，新闻，approve。
18. `THU000022` 科研项目：58/32，科研信息，approve；明显异常。
19. `THU000048` 学术学位教育：92/90，规章制度，approve。
20. `THU000023` 科研机构：42/38，科研信息，approve；明显异常。

分数格式为“relevance_score / knowledge_value”。完整理由见 `sampling_report.md`。

## 10个Portal本地样本

1. `PORTAL000001` 后勤服务指南：review。
2. `PORTAL000002` 党政办信息办公网：review。
3. `PORTAL000003` 科研办公信息网：review。
4. `PORTAL000004` 国际合作与交流处信息资讯：review。
5. `PORTAL000005` 马耳他申根信息：review。
6. `PORTAL000006` 境内延期F字访问签证指南：review。
7. `PORTAL000007` 办事程序：review。
8. `PORTAL000008` 清华大学医院：review。
9. `PORTAL000009` 后勤技能标兵人物稿：review，疑似应reject。
10. `PORTAL000010` 后勤服务标兵人物稿：review，疑似应reject。

## 下一轮建议

1. Prompt v2加入硬决策门槛：低相关或低价值不得approve；新闻、人物宣传、科研信息默认reject，除非含明确长期校园服务流程。
2. 明确“官方权威不等于知识价值”，要求模型先判内容类型和时效，再给动作。
3. `relevance_score < 60` 或 `knowledge_value < 60` 时禁止approve；高时效内容最多review。
4. 将30篇v1结果视为Prompt评测集，不继续扩大；升级为v2后只复审这30篇并对比动作变化。
5. Portal本地规则中人物宣传优先级应高于“后勤服务”等正向词；一次性活动与过期疫苗通知默认reject/review。
6. 人工检查Public中8条 `personal_data_risk=low`，确认只是公共联系方式后再进入第三阶段。
7. 第三阶段前不要直接使用当前 `04_approved/public`；先处理质量报告中的异常项。
