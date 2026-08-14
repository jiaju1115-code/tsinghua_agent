# Public Expansion V2 最终报告

> 状态：`CANDIDATE_POOL_READY_WITH_PUBLIC_SOURCE_LIMITS`。canonical 主池已修复跨轮次 ID 冲突；以下统计仅使用 canonical 数据。

1. **当前217条 approve category 分布**：{"网络与信息化": 8, "教学与培养": 2, "图书馆服务": 48, "校园机构与部门": 4, "科研参与与资源导航": 17, "校园文化与历史": 2}。
2. **当前最大知识缺口**：教务与学籍、学生事务、住宿服务、餐饮服务、交通服务、医疗健康、体育与场馆、奖助与资助、国际事务与签证、就业与职业发展、校园访问、校园综合服务。
3. **本轮发现 URL 数量**：轮次发现记录 413；唯一 URL 413。
4. **抓取数量**：历史去重后 canonical 抓取 307，成功 307。
5. **Quality Gate 通过数量**：165。未达到约300停止目标，未用新闻、登录页、列表页或薄正文凑数。
6. **Quality Gate 失败类型**：{"extraction_failed": 44, "navigation_only": 22, "list_page": 32, "template_polluted": 4, "detail_content": 3, "private_or_sensitive": 6, "soft_404": 7, "login_required": 23, "thin_content": 1}。
7. **送 V3.2 数量**：165。
8. **approve/review/reject**：154/8/3。
9. **candidate_approved 数量**：154。
10. **各 category 新增数量**：{"住宿服务": 12, "教务与学籍": 63, "体育与场馆": 5, "医疗健康": 13, "学生事务": 4, "国际事务与签证": 12, "就业与职业发展": 7, "交通服务": 3, "网络与信息化": 7, "非目标范围": 2, "教学与培养": 12, "奖助与资助": 4, "校园机构与部门": 6, "科研参与与资源导航": 9, "校园文化与历史": 4, "餐饮服务": 2}。
11. **P0 类别新增**：{"教务与学籍": 63, "学生事务": 4, "住宿服务": 12, "餐饮服务": 2, "交通服务": 3, "医疗健康": 13, "奖助与资助": 4, "就业与职业发展": 7}。
12. **各 domain 分布**：{"www.tsinghua.edu.cn": 84, "www.thsports.tsinghua.edu.cn": 4, "www.med.tsinghua.edu.cn": 9, "www.is.tsinghua.edu.cn": 16, "dag.tsinghua.edu.cn": 2, "student.tsinghua.edu.cn": 1, "career.cic.tsinghua.edu.cn": 1, "career.tsinghua.edu.cn": 5, "learning.tsinghua.edu.cn": 2, "qzc.tsinghua.edu.cn": 22, "www.wyc.tsinghua.edu.cn": 5, "www.itc.tsinghua.edu.cn": 1, "www.jgb.tsinghua.edu.cn": 1, "www.rd.tsinghua.edu.cn": 1, "www.sysc.tsinghua.edu.cn": 1, "www.tyzx.tsinghua.edu.cn": 1, "xsg.tsinghua.edu.cn": 1, "xyy.tsinghua.edu.cn": 1, "zkzx.tsinghua.edu.cn": 1, "tsimf.tsinghua.edu.cn": 1, "ac.tsinghua.edu.cn": 5}。
13. **library 占比**：0/165 = 0.0%，低于10%。
14. **最大 domain 占比**：www.tsinghua.edu.cn 为 84/165 = 50.91%。超过25%，原因是清华主站集中承载信息公开、研究生院、机构目录与校园服务；已完整披露且未据此降低质量门槛。
15. **历史去重数量**：106（URL 105 + title similarity 1）。
16. **Expansion V2 内部去重**：9。
17. **list page 一层 follow 后进入审核数量**：118。
18. **low + approve**：0。
19. **科研成果/人物/领导/普通活动误收检查**：approve 风险关键词命中 0 条；唯一普通论坛新闻已 reject。
20. **长期服务/科研资源误杀检查**：reject 中长期服务或科研资源命中 0 条。抽查纠正了宿舍邮寄地址、114挂号平台和学生表彰制度的初始误判。
21. **PUBLIC_SOURCE_LIMITED**：学生事务、住宿服务、餐饮服务、交通服务、医疗健康、奖助与资助、就业与职业发展、体育与场馆、校园访问、校园综合服务、网络与信息化。公开入口常转向校内认证，且严格排除了普通新闻、附件壳页与低质量正文。
22. **人工抽检包样本数量**：49。
23. **所有新增正文均可独立重新审核**：是；source_file 缺失 0，content hash 不一致 0。
24. **是否修改任何旧数据**：否。所有写入仅位于 `data_second/public_expansion_v2`（及工作区临时脚本）。
25. **是否修改 Prompt V3.2**：否；冻结 Prompt SHA-256 为 `b94623c520fc46d83a49a4d043ad182646e7a881e7e1751e3e98e98724d771cd`。

## 结论

本轮形成 165 条 canonical Quality Gate 有效候选，其中 154 条 candidate_approved、8 条 candidate_review、3 条 candidate_rejected。未达到约300条目标，按规则记录公开源受限，不进入受限/认证来源，不合并生产库。
