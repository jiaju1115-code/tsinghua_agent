# PROVISIONAL_KB_V0 Retrieval Smoke Review

本页是对 `retrieval_smoke_results.jsonl` Top-5 的人工可读技术观察，不是 Gold Label，也不是生成答案质量评估。

| Case | 主题 | Top-5 观察 | 状态 |
|---|---|---|---|
| RET-01 | 教务学籍 | 命中辅修学位教学管理、课程免修、注册相关材料，但未命中一份覆盖“学籍+注册+培养”的总则 | partial |
| RET-02 | 住宿 | Top-1 为住宿注意事项，Top-2 至 Top-5 为学生公寓住宿管理办法分块 | pass |
| RET-03 | 校园网 | Top-1 为校园网络运行，Top-2 为用户服务 | pass |
| RET-04 | 医疗 | 命中校医院及 Restricted 生育医疗报销程序 | pass |
| RET-05 | 图书馆 | 命中电子资源与馆舍资料，但“借阅导引”未进入 Top-5，复合问题覆盖不完整 | partial |
| RET-06 | 奖助 | 命中学生奖学金管理规定和 Restricted 特等奖学金评选办法 | pass |
| RET-07 | 就业 | 命中个体职业咨询、职业发展协会、就业服务协会 | pass |
| RET-08 | 餐饮 | 命中学生食堂、饮食服务中心、教工餐厅 | pass |
| RET-09 | 交通 | Top-5 未找到校园交通/校车资料；现有“交通服务”标签下正文也与交通主题不符 | fail |
| RET-10 | 体育场馆 | 命中体育设施与综合体育馆 | pass |

汇总：pass 7，partial 2，fail 1。脚本启发式指标为 keyword-hit@5 10/10、category-hit@5 9/10；这些指标不能替代上述内容检查，更不能替代后续人工 RAG 评估。
