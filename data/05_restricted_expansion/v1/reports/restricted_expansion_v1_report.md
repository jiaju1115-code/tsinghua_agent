# Restricted / Authenticated Expansion V1 Report

**最终状态：`SOURCE_EXHAUSTED_WITH_HIGH_QUALITY_CANDIDATES`**  
**停止条件：B（主要受限入口已穷尽；不为数量收集导航页、旧通知或公开外链）**

1. Public Staging最终approve数量：234。
2. Public Staging category分布：{"教务与学籍": 61, "学生事务": 4, "住宿服务": 12, "餐饮服务": 2, "交通服务": 3, "医疗健康": 13, "网络与信息化": 15, "图书馆服务": 48, "体育与场馆": 4, "奖助与资助": 4, "国际事务与签证": 12, "就业与职业发展": 6, "科研参与与资源导航": 25, "教学与培养": 10, "校园机构与部门": 10, "校园文化与历史": 5}。
3. Restricted重点缺口：学生事务, 餐饮服务, 交通服务, 体育与场馆, 奖助与资助, 就业与职业发展, 校园访问, 校园综合服务。
4. login_required旧seed数量：23；推荐/条件抓取13，验证发现职业站可公开直达且大量旧路径404，不作为Restricted新增。
5. Restricted发现URL数量：门户首页142 + 通用入口108 + 搜索结果224（分层计数，非唯一并集）。
6. 抓取数量：核心17 + 精选8 + 职业原始种子探测3。
7. private_sensitive_gate：{"safe_general_content": 17, "unclear": 18, "sensitive_internal": 1}。
8. Quality Gate通过数量：5。
9. list page数量：4。
10. dedup数量：0；另有Restricted内部同名择优1。
11. 送V3.2数量：4。
12. approve/review/reject：4/0/0。
13. 各category新增数量：{"教务与学籍": 1, "校园综合服务": 1, "医疗健康": 1, "奖助与资助": 1}。
14. 各P0类别新增：{"学生事务": 0, "住宿服务": 0, "餐饮服务": 0, "交通服务": 0, "医疗健康": 1, "奖助与资助": 1, "就业与职业发展": 0}。
15. system/domain分布：{"info.tsinghua.edu.cn": 4}。
16. expired数量：0。
17. low + approve：0。
18. 科研成果/活动类误收：否。
19. 长期服务误杀：未发现；列表/薄页保留在QG记录，未错误送审。
20. 个人数据进入candidate：否。
21. 凭据/Token/Cookie落盘：否；storage state沿用项目既有安全位置，未复制到报告或候选。
22. 每条正文可独立重新审核：是，4/4存在，哈希不匹配0。
23. 仍明显不足category：学生事务, 餐饮服务, 交通服务, 体育与场馆, 奖助与资助, 就业与职业发展, 校园访问, 校园综合服务。
24. 下一步是否需要Restricted Expansion V2：暂不建议立即开启；先人工抽检本轮和Public staging，再决定是否换新入口。

Prompt：冻结Prompt V3.2，基准日2026-08-12；未调用第三方模型API。
