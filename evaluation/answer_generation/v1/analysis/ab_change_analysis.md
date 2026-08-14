# A/B change analysis

> PROVISIONAL_AUTO_EVAL；没有使用人工标签。Composite score = correctness + faithfulness + 0.5×completeness + 2×citation_compliance − 2×generation_hallucination。

## improved (0)

本轮无此类案例。

## degraded (4)

### RET-04 — 清华校医院门诊、报销和就医流程是什么？

- A：清华校医院：门诊-检验医学科、输血科、超声科等；报销需咨询财务部门；就医流程可至官网查询。
- B：清华校医院门诊、报销和就医流程信息不详，需查询官网获取最新信息。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=-1，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### RET-09 — 校园交通、校车和进出校路线怎么查询？

- A：根据当前资料无法确认。
- B：当前资料存在冲突。
- Citation：A=['NONE']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=-1，unsupported claims=1
- Diagnosis：回答提供了关于校园交通、校车和进出校路线的详细信息，证据支持了这些事实，且回答内容完整。

### PROV-016 — 清华师生如何使用馆际互借服务获取外馆文献？

- A：清华师生可通过馆际互借服务获取外馆文献。
- B：根据当前资料无法确认。
- Citation：A=['MISSING_CITATION']；B=['NONE']
- Δ correctness=-2，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-021 — 国际学生选择校外住宿时应查看什么住宿指南？

- A：根据当前资料无法确认。
- B：国际学生选择校外住宿时应查看《2026国际学生住宿指南》。
- Citation：A=['NONE']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=-1，unsupported claims=1
- Diagnosis：

## uncertain (28)

### RET-01 — 如何查询清华大学本科生学籍、注册与培养管理规定？

- A：清华大学本科生学籍管理规定由2016~2017学年度第25次校务会议通过，2019~20学年度第30次校务会议修订。该规定适用于全校本科生的学籍管理。
- B：清华大学本科生学籍管理规定可从学校官网查询。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：证据支持了所有可核验的事实，且证据是完整的。

### RET-02 — 学生公寓住宿规定、入住和退宿怎么办？

- A：学生公寓住宿规定如下：

1. 具有学校学籍的全日制在校学生具有申请入住资格。
2. 提出住宿申请，经批准后方可入住。
3. 与学生社区管理服务中心签订住宿协议。
4. 学生社区管理服务中心统筹安排。
5. 如需调整，提前告知相关学生配合搬家。
6. 办理入住手续后入住指定床位，未经批准不得擅自调换。
7. 遇疾病等特殊情况需调换床位，应向院系和学生社区管理服务中心申请。
8. 毕业、住宿协议到期、退学
- B：学生公寓住宿规定如下：

1. 具有学校学籍的全日制在校学生具有申请入住资格。
2. 学生提出住宿申请，经批准后方可入住。
3. 获批住宿的学生应当与学生社区管理服务中心签订住宿协议。
4. 学生公寓按照分区住宿、院系相对集中的原则进行住宿分配。
5. 住宿学生应当服从学校住宿安排及调整。
6. 学生办理入住手续后应当入住指定床位，不得擅自调换。
7. 学生遇疾病等特殊情况需调换床位时，应向所在院系和
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确、完整地涵盖了学生公寓住宿规定的主要内容，并提供了相应的证据支持。

### RET-03 — 清华校园网如何接入，账号或网络故障如何处理？

- A：清华校园网提供有线网络服务，无线网络服务，GPON光纤入户服务等。账号或网络故障可联系热线服务或在线服务进行处理。
- B：清华校园网提供有线网络服务和无线网络服务，支持IPv4/IPv6双栈认证。遇到问题可拨打热线电话或通过服务邮箱咨询。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### RET-05 — 清华大学图书馆如何借书、使用电子资源和查询开放时间？

- A：- 1
- 6
- 7
- 8
- 9
- 10
- 11
- 12
- B：- 1: 金融图书馆开放时间为周一至周五：8:00—22:00,周末：14:00—22:00。
- 2: 读者需持工作证或学生证借用图书资料。
- 3: 凭本人的校园一卡通学生证、工作证和临时借阅证可以刷卡进入图书馆。
- 4: 可以参观金融馆并借阅资料，需登记有效证件。
- 5: 可以将书还到学校其他图书馆。
- 6: 需开通借书权限才能
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### RET-06 — 清华学生奖学金、助学金申请和评选办法是什么？

- A：清华学生奖学金、助学金评选办法如下：

- 特等奖学金面向全体本科生、研究生分别组织评选，每年表彰不超过二十名学生。
- 评选条件包括基本申请条件、道德品质优秀、学风端正、全面发展等。
- 现场答辩形式进行复评，形成推荐名单，提请校务会议审议。
- 奖学金获得者需在评选当年发放，并颁发荣誉证书。
- B：清华学生奖学金、助学金申请和评选办法如下：

- 特等奖学金面向本科生和研究生，每年评选一次，表彰不超过二十名学生。
- 评选条件包括基本申请条件、道德品质优秀、学风端正、学业成绩优良等。
- 现场答辩形式进行复评，形成推荐名单，提请校务会议审议。
- 特等奖学金获得者有弄虚作假等不当行为的，取消其参评资格并视情节轻重给予相应处理。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确地描述了清华学生奖学金、助学金的申请和评选办法，提供了多个证据支持，且所有事实都被充分支持。

### RET-07 — 清华学生如何获得就业指导、招聘与职业咨询？

- A：清华学生可预约个体咨询，由30余位咨询师提供个性化指导。生涯咨询涵盖自我了解、职业探索、方向选择、简历与面试、求职心理等方面。清华学生职业发展指导中心有近30位咨询师，可为不同学历、不同年级的学生提供系统性的生涯辅导。
- B：清华学生可向学生职业发展指导中心预约个体咨询，提供生涯规划、简历修改、面试技巧等服务。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确、忠实于证据，且完整。证据支持了清华学生获得就业指导、招聘与职业咨询的途径，包括学生职业发展指导中心的个体咨询和专项辅导活动。

### RET-08 — 校内食堂、餐饮服务和就餐信息在哪里查询？

- A：清华大学食堂信息：[C1]丁香园食堂、闻馨园食堂、双清园食堂；餐饮服务：[C2]饮食服务中心；就餐信息：[C5]教工餐厅。
- B：校内食堂、餐饮服务和就餐信息可在以下渠道查询：

1. **学生食堂**：丁香园食堂、闻馨园食堂、双清园食堂
2. **饮食服务中心**：清华膳食处改制为饮食服务中心，提供综合饮食服务网络
3. **商贸与食品安全管理中心**：专项检查和夏季食品安全检查
4. **联系我们-清华大学图书馆**：读者接待处、检索证明、科技查新工作站等
- Citation：A=['CITATION_FORMAT_ERROR']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确且全面，提供了多个渠道查询校内食堂、餐饮服务和就餐信息的途径。证据充分支持每个事实，且没有不支持的证据。

### RET-10 — 体育场馆如何预约、查询开放时间和使用规则？

- A：体育场馆预约：应用导航-场地资源预约。开放时间及使用规则：根据当前资料无法确认。
- B：体育场馆预约：应用导航-场地资源预约。查询开放时间：可从“学生清华”公众号获取。使用规则：详见《注册临时居住证》。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=1，faithfulness=1，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-001 — 本科新生不能按时报到时如何请假或申请保留入学资格？

- A：新生不能按时报到时，可以向录取学院、学系请假，并申请保留入学资格。
- B：新生不能按时报到时，可以向录取学院、学系请假或申请保留入学资格。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确地指出了新生不能按时报到时可以请假或申请保留入学资格的两种方式，即向录取学院或学系请假或申请保留入学资格。提供的证据充分支持了这两个事实。

### PROV-005 — 学生想申请调整宿舍，应查看什么办理流程？

- A：应查看《清华大学学生宿舍申请表》并提交给院系主管学生工作负责人签字、盖章。
- B：学生想申请调整宿舍，应查看《清华大学学生宿舍申请表》并提交给院系主管学生工作负责人签字、盖章。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-006 — 给住在清华学生社区的同学寄快递时，邮寄地址和邮编在哪里查？

- A：请查看清华档案馆官网或学生职业发展指导中心网站，查询邮寄地址和邮编。
- B：紫荆公寓中文地址：100084，北京市海淀区清华大学，紫荆学生公寓×#楼×××房间；寄信人地址、姓名。

紫荆公寓英文地址：寄信人地址、姓名，Name，Zijing Building x# Room xxx(A;B)，Tsinghua University，Beijing 100084，P.R CHINA。

南区公寓中文地址：100084，北京市海淀区清华大学，学生公寓×#楼×××房间；寄信人地址、姓名。

南区公寓英文地址：寄信人地址，姓名
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-007 — 负责清华校内食堂和餐饮保障的是哪个饮食服务部门？

- A：饮食服务中心
- B：负责清华校内食堂和餐饮保障的是饮食服务中心。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-008 — 教职工想查询校内教工餐厅信息，应查看哪份校园服务资料？

- A：教工餐厅信息应查看教工餐厅资料。
- B：教工餐厅信息应查看《清华大学教参服务平台》。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-009 — 清华校车线路、班次和校园出入口交通指引在哪里查？

- A：请查看清华接待服务中心的官方公众号或小程序，其中详细列出了校车线路、班次和校园出入口交通指引。
- B：清华校车线路、班次和校园出入口交通指引请参阅“清华巴士”小程序。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答提供了清华校车线路、班次和校园出入口交通指引的途径，并且证据支持了这些事实。

### PROV-010 — 在清华办理生育医疗费用报销需要查看什么程序？

- A：在清华办理生育医疗费用报销需要查看以下程序：
1. 生育医疗报销程序 - 清华大学信息门户
2. 医保定点医院选择
3. 出示“社会保障卡”
4. 提交相关材料
5. 填写《北京市生育保险医疗费用手工报销申报表》
- B：在清华办理生育医疗费用报销需要查看《北京市生育保险医疗费用手工报销申报表》。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：证据直接支持了回答中的事实，且没有不支持的证据。

### PROV-011 — 清华大学医院能否通过北京114平台预约挂号？

- A：可以，清华大学医院自2024年7月1日起与北京市114预约挂号平台实现直连。
- B：能，关注“北京114预约挂号”公众号，搜索“清华大学医院”可进行预约挂号。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-014 — 清华图书馆图书借还的规则和操作说明在哪里？

- A：图书借还规则和操作说明在清华图书馆主页上。
- B：清华图书馆图书借还的规则和操作说明在《图书借还》一文中。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-015 — 进入清华大学图书馆需要遵守什么入馆管理办法？

- A：进入清华大学图书馆需要遵守以下入馆管理办法：

1. 校内读者凭本人有效图书证入馆。
2. 校外读者按规定办理手续后入馆。
3. 清华校友凭校友卡或毕业证（或复印件），附上有效身份证件，可进入校图书馆。
4. 注意防火安全，严禁在馆内吸烟。
5. 饮料需置于防溢出容器内，不可携带气味食物、外卖盒餐等入馆。
6. 保持安静，手持电话置于静音状态。
7. 衣着整齐，举止文明礼貌。
8.
- B：进入清华大学图书馆需要遵守以下入馆管理办法：

1. 校内读者凭本人有效图书证入馆。
2. 校外读者按规定办理手续后入馆。
3. 清华校友凭校友总会发放的“校友卡”或毕业证(或复印件),并附上本人有效身份证件,可进入校图书馆。
4. 注意防火安全，严禁在馆内任何地方吸烟。
5. 读者可携带非酒精类饮料(置于防溢出容器内)入馆，不可携带有气味食物、外卖盒餐等入馆。按照相关要求，在规定区域内食用或
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-017 — 综合体育馆的建筑面积、观众席位和赛事用途是什么？

- A：综合体育馆总建筑面积12547.85平米，总观众席位4502个，可满足国际比赛和现场电视转播的要求。为2001年第21届世界大学生运动会男子篮球比赛场馆，2008年北京奥运会男子篮球和轮椅篮球训练场馆。
- B：综合体育馆的建筑面积为12547.85平米，总观众席位4502个。它主要用于2001年第21届世界大学生运动会男子篮球比赛和2008年北京奥运会男子篮球和轮椅篮球训练。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-018 — 清华大学特等奖学金采用什么评选办法？

- A：清华大学特等奖学金评选办法如下：

- 评选机构通过现场答辩形式组织复评，形成推荐名单，提请校务会议审议。
- 校务会议讨论决定特等奖学金表彰名单。
- 特等奖学金表彰名单在学校信息门户网站予以公示。
- B：清华大学特等奖学金评选办法如下：

1. 评选机构通过现场答辩形式组织复评，形成推荐名单，提请校务会议审议。
2. 校务会议讨论决定特等奖学金表彰名单。
3. 特等奖学金表彰名单在学校信息门户网站公示。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-019 — 国家助学贷款发放后，学生应遵守哪些贷后管理规定？

- A：根据当前资料，国家助学贷款发放后应遵守以下贷后管理规定：

1. 做好贷款学生信息建档工作。
2. 做好诚信教育工作。
3. 贷款学生在校期间有下列行为的，学校将通知经办银行停止发放助学贷款，并要求一次性偿还贷款本息：
   - 未按合同规定的用途使用贷款；
   - 违法乱纪行为受到学校纪律处分或有关部门刑事处罚；
   - 中途辍学、退学、转学、被学校开除或取消学籍；
   - 学习不刻苦
- B：学生应遵守诚信教育、按时还款、配合催收工作等贷后管理规定。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确地列出了国家助学贷款发放后学生应遵守的贷后管理规定，包括诚信教育、按时还款、配合催收工作等。证据中的信息支持了这些事实，且没有不支持的证据。

### PROV-020 — 国际学生如何区分并查询不同的签证类型？

- A：国际学生可查询不同签证类型如下：X1签证颁发给长期学习，需在入境后30日内申请学习类居留许可；X2签证颁发给短期学习，有效期以签证注明为准。
- B：国际学生可通过以下方式区分并查询不同签证类型：

1. X1签证：颁发给在中国境内长期（超过180日）学习的人员。
2. X2签证：颁发给在中国境内短期（不超过180日）学习的人员。
3. Internships/实习签证：需持就读院校在读及同意外国留学生参与校外实习证明，实习单位出具接收实习证明等相关材料，向高校所在地的公安机关出入境管理部门申请。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-023 — 学生想进行一对一生涯咨询、简历修改或模拟面试，可以找什么服务？

- A：可以找以下服务：

- **生涯咨询**：李锋亮、马昱春、王大亮
- **简历修改**：朱李婧、陈旭东、董亮、赵梦圆
- **模拟面试**：张杨、关麟凤、俞婷君
- B：可以找以下服务：

- 一对一生涯咨询：李锋亮、马昱春、王大亮
- 简历修改：朱李婧、陈旭东、董亮、赵梦圆
- 模拟面试：张杨、关麟凤、俞婷君
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答提供了关于生涯咨询、简历修改和模拟面试的详细信息，证据支持了这些事实。

### PROV-024 — 清华科研仪器共享平台能否查询开放设备并预约测试？

- A：可以查询开放设备并预约测试，详情请访问清华仪器共享服务平台。
- B：能查询开放设备并预约测试。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-025 — 清华通讯作者在IEEE开放获取期刊发表论文有何APC优惠？

- A：通讯作者为我校师生在IEEE金色OA期刊或混合OA期刊发表OA论文时，可获得9折费用折扣。优惠范围包括Full Open Access与Hybrid Open Access期刊。优惠时间截至2026年12月31日。
- B：通讯作者为清华师生在IEEE发表OA论文，可享受9折APC优惠。优惠范围包括金色OA期刊和混合OA期刊。需使用清华大学提供的邮箱地址，并将机构信息正确关联系统中的学校账号：Tsinghua University。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-026 — 学校的信息化教室、录播系统和教学技术支持由什么服务负责？

- A：信息化教学环境服务负责学校信息化教室、录播系统和教学技术支持。
- B：学校信息化教室、录播系统和教学技术支持由《现代教育技术》期刊编辑出版工作负责。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-027 — 清华专业学位人才培养项目采用什么建设定位？

- A：清华专业学位人才培养项目采用“高端定位、清华特色、中国视角”的建设标准。
- B：清华专业学位人才培养项目采用“高端定位、清华特色、中国视角”的建设定位。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-028 — 如何查询清华各院系的单位号、简称和英文名称？

- A：单位号：000 建筑学院 jzxy；003 土木系 tmx；004 水利系 slx；005 环境学院 hjxy；011 机械学院 jxxy；012 机械系 jxx；013 精仪系 jyx；014 能动系 ndx；015 车辆学院 clxy；016 工业工程系 gygcx；021 信息学院 xxxy。简称：建筑学院、土木工程系
- B：如何查询清华各院系的单位号、简称和英文名称？
1. 查看《单位编码》文档，其中列出了清华大学各个院系的单位号、简称和英文名称。
2. 通过清华大学图书馆官网的“联系我们-清华大学图书馆”页面，可以找到总馆联系方式及专业图书馆的联系信息。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

## unchanged (6)

### PROV-002 — 在校本科生或研究生办理在学证明，可以去哪里申请和打印？

- A：在校本科生或研究生办理在学证明，可以到所在院系教学办审批并签字盖章。如需打印，可到自助服务终端（六教A区零层入口处、紫荆C楼102）直接办理，或到注册中心（紫荆C楼201）手工办理。
- B：在校本科生或研究生办理在学证明，可以到所在院系教学办审批并签字盖章。如需打印，可到自助服务终端（六教A区零层入口处、紫荆C楼102）直接办理，或到注册中心（紫荆C楼201）手工办理。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确地提供了在学证明的申请和打印地点，证据充分支持这些事实。

### PROV-003 — 学生不服学校处理或纪律处分时，校内申诉由哪个机构办理？

- A：学生不服学校处理或纪律处分时，校内申诉由学生申诉处理委员会办理。
- B：学生不服学校处理或纪律处分时，校内申诉由学生申诉处理委员会办理。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-004 — 清华学生社团的建设、成立和日常管理依据什么办法？

- A：清华学生社团的建设、成立和日常管理依据《清华大学学生社团建设管理办法》。
- B：清华学生社团的建设、成立和日常管理依据《清华大学学生社团建设管理办法》。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：证据直接支持了回答中的事实，且证据数量与事实数量一致。

### PROV-012 — 校园网络运行和基础网络服务的信息由哪份资料说明？

- A：校园网络运行和基础网络服务的信息由资料[C1]说明。
- B：校园网络运行和基础网络服务的信息由资料[C1]说明。
- Citation：A=['CITATION_FORMAT_ERROR']；B=['CITATION_FORMAT_ERROR']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-013 — 遇到学校信息化账号或网络使用问题时，应到哪里寻找用户服务？

- A：遇到学校信息化账号或网络使用问题时，应到用户服务大厅寻求帮助。
- B：遇到学校信息化账号或网络使用问题时，应到用户服务大厅寻求帮助。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：

### PROV-022 — 学生职业发展指导中心面向学生提供哪些就业服务？

- A：学生职业发展指导中心提供生涯咨询、专项辅导、朋辈辅导、求职技巧实训等就业服务。
- B：学生职业发展指导中心提供生涯咨询、专项辅导、朋辈辅导、求职技巧实训等就业服务。
- Citation：A=['MISSING_CITATION']；B=['MISSING_CITATION']
- Δ correctness=0，faithfulness=0，citation compliance=0，unsupported claims=0
- Diagnosis：回答准确、忠实于证据，且全面覆盖了证据中的关键信息。
