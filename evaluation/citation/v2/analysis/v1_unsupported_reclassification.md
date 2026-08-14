# V1 Unsupported Reclassification

> PROVISIONAL_AUTO_EVAL；自动重归因不是人工 Gold。全库检索只用于诊断，不影响 V2 官方引用和指标。

总计：92。

- V1_MAPPING_FAILURE: 32
- TOP5_EVIDENCE_PARTIAL: 14
- RETRIEVAL_FAILURE: 0
- SOURCE_QUALITY_FAILURE: 1
- GENERATION_HALLUCINATION: 2
- AMBIGUOUS: 43

## 逐条结果

### RET-01-C002 · V1_MAPPING_FAILURE

- Question: 如何查询清华大学本科生学籍、注册与培养管理规定？
- Claim: 该规定适用于全校本科生的学籍管理。
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-02-C002 · V1_MAPPING_FAILURE

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 具有学校学籍的全日制在校学生具有申请入住资格。
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-02-C003 · TOP5_EVIDENCE_PARTIAL

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 提出住宿申请，经批准后方可入住。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-02-C004 · V1_MAPPING_FAILURE

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 与学生社区管理服务中心签订住宿协议。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-02-C005 · AMBIGUOUS

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 学生社区管理服务中心统筹安排。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-02-C006 · TOP5_EVIDENCE_PARTIAL

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 如需调整，提前告知相关学生配合搬家。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-02-C007 · V1_MAPPING_FAILURE

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 办理入住手续后入住指定床位，未经批准不得擅自调换。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-02-C008 · TOP5_EVIDENCE_PARTIAL

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 遇疾病等特殊情况需调换床位，
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-02-C009 · AMBIGUOUS

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 应向院系和学生社区管理服务中心申请。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-02-C010 · TOP5_EVIDENCE_PARTIAL

- Question: 学生公寓住宿规定、入住和退宿怎么办？
- Claim: 毕业、住宿协议到期、退学
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-03-C001 · V1_MAPPING_FAILURE

- Question: 清华校园网如何接入，账号或网络故障如何处理？
- Claim: 清华校园网提供有线网络服务，无线网络服务，GPON光纤入户服务等。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-03-C002 · AMBIGUOUS

- Question: 清华校园网如何接入，账号或网络故障如何处理？
- Claim: 账号或网络故障可联系热线服务或在线服务进行处理。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-04-C001 · AMBIGUOUS

- Question: 清华校医院门诊、报销和就医流程是什么？
- Claim: 清华校医院：门诊-检验医学科、输血科、超声科等；
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-04-C002 · AMBIGUOUS

- Question: 清华校医院门诊、报销和就医流程是什么？
- Claim: 报销需咨询财务部门；
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-04-C003 · AMBIGUOUS

- Question: 清华校医院门诊、报销和就医流程是什么？
- Claim: 就医流程可至官网查询。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-06-C002 · V1_MAPPING_FAILURE

- Question: 清华学生奖学金、助学金申请和评选办法是什么？
- Claim: 特等奖学金面向全体本科生、研究生分别组织评选，每年表彰不超过二十名学生。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-06-C003 · AMBIGUOUS

- Question: 清华学生奖学金、助学金申请和评选办法是什么？
- Claim: 评选条件包括基本申请条件、道德品质优秀、学风端正、全面发展等。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-06-C004 · V1_MAPPING_FAILURE

- Question: 清华学生奖学金、助学金申请和评选办法是什么？
- Claim: 现场答辩形式进行复评，形成推荐名单，提请校务会议审议。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-06-C005 · V1_MAPPING_FAILURE

- Question: 清华学生奖学金、助学金申请和评选办法是什么？
- Claim: 奖学金获得者需在评选当年发放，并颁发荣誉证书。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-07-C001 · AMBIGUOUS

- Question: 清华学生如何获得就业指导、招聘与职业咨询？
- Claim: 清华学生可预约个体咨询，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-07-C002 · V1_MAPPING_FAILURE

- Question: 清华学生如何获得就业指导、招聘与职业咨询？
- Claim: 由30余位咨询师提供个性化指导。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-07-C004 · AMBIGUOUS

- Question: 清华学生如何获得就业指导、招聘与职业咨询？
- Claim: 清华学生职业发展指导中心有近30位咨询师，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-07-C005 · TOP5_EVIDENCE_PARTIAL

- Question: 清华学生如何获得就业指导、招聘与职业咨询？
- Claim: 可为不同学历、不同年级的学生提供系统性的生涯辅导。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-08-C001 · AMBIGUOUS

- Question: 校内食堂、餐饮服务和就餐信息在哪里查询？
- Claim: 清华大学食堂信息：[C1]丁香园食堂、闻馨园食堂、双清园食堂；
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### RET-08-C002 · AMBIGUOUS

- Question: 校内食堂、餐饮服务和就餐信息在哪里查询？
- Claim: 餐饮服务：[C2]饮食服务中心；
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-08-C003 · AMBIGUOUS

- Question: 校内食堂、餐饮服务和就餐信息在哪里查询？
- Claim: 就餐信息：[C5]教工餐厅。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-10-C001 · AMBIGUOUS

- Question: 体育场馆如何预约、查询开放时间和使用规则？
- Claim: 体育场馆预约：应用导航-场地资源预约。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### RET-10-C002 · AMBIGUOUS

- Question: 体育场馆如何预约、查询开放时间和使用规则？
- Claim: 开放时间及使用规则：根据当前资料无法确认。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-001-C001 · AMBIGUOUS

- Question: 本科新生不能按时报到时如何请假或申请保留入学资格？
- Claim: 新生不能按时报到时，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-001-C002 · AMBIGUOUS

- Question: 本科新生不能按时报到时如何请假或申请保留入学资格？
- Claim: 可以向录取学院、学系请假，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-001-C003 · TOP5_EVIDENCE_PARTIAL

- Question: 本科新生不能按时报到时如何请假或申请保留入学资格？
- Claim: 并申请保留入学资格。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-002-C001 · TOP5_EVIDENCE_PARTIAL

- Question: 在校本科生或研究生办理在学证明，可以去哪里申请和打印？
- Claim: 在校本科生或研究生办理在学证明，
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-002-C002 · AMBIGUOUS

- Question: 在校本科生或研究生办理在学证明，可以去哪里申请和打印？
- Claim: 可以到所在院系教学办审批并签字盖章。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-002-C003 · AMBIGUOUS

- Question: 在校本科生或研究生办理在学证明，可以去哪里申请和打印？
- Claim: 如需打印，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-002-C004 · V1_MAPPING_FAILURE

- Question: 在校本科生或研究生办理在学证明，可以去哪里申请和打印？
- Claim: 可到自助服务终端（六教A区零层入口处、紫荆C楼102）直接办理，或到注册中心（紫荆C楼201）手工办理。
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-003-C001 · AMBIGUOUS

- Question: 学生不服学校处理或纪律处分时，校内申诉由哪个机构办理？
- Claim: 学生不服学校处理或纪律处分时，校内申诉由学生申诉处理委员会办理。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-005-C001 · V1_MAPPING_FAILURE

- Question: 学生想申请调整宿舍，应查看什么办理流程？
- Claim: 应查看《清华大学学生宿舍申请表》并提交给院系主管学生工作负责人签字、盖章。
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-006-C001 · AMBIGUOUS

- Question: 给住在清华学生社区的同学寄快递时，邮寄地址和邮编在哪里查？
- Claim: 请查看清华档案馆官网或学生职业发展指导中心网站，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-006-C002 · AMBIGUOUS

- Question: 给住在清华学生社区的同学寄快递时，邮寄地址和邮编在哪里查？
- Claim: 查询邮寄地址和邮编。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-007-C001 · AMBIGUOUS

- Question: 负责清华校内食堂和餐饮保障的是哪个饮食服务部门？
- Claim: 饮食服务中心
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-008-C001 · AMBIGUOUS

- Question: 教职工想查询校内教工餐厅信息，应查看哪份校园服务资料？
- Claim: 教工餐厅信息应查看教工餐厅资料。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-009-C001 · SOURCE_QUALITY_FAILURE

- Question: 清华校车线路、班次和校园出入口交通指引在哪里查？
- Claim: 请查看清华接待服务中心的官方公众号或小程序，其中详细列出了校车线路、班次和校园出入口交通指引。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-010-C001 · GENERATION_HALLUCINATION

- Question: 在清华办理生育医疗费用报销需要查看什么程序？
- Claim: 在清华办理生育医疗费用报销需要查看以下程序：
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-010-C003 · AMBIGUOUS

- Question: 在清华办理生育医疗费用报销需要查看什么程序？
- Claim: 医保定点医院选择
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-010-C004 · AMBIGUOUS

- Question: 在清华办理生育医疗费用报销需要查看什么程序？
- Claim: 出示“社会保障卡”
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-010-C005 · AMBIGUOUS

- Question: 在清华办理生育医疗费用报销需要查看什么程序？
- Claim: 提交相关材料
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-010-C006 · V1_MAPPING_FAILURE

- Question: 在清华办理生育医疗费用报销需要查看什么程序？
- Claim: 填写《北京市生育保险医疗费用手工报销申报表》
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-013-C001 · AMBIGUOUS

- Question: 遇到学校信息化账号或网络使用问题时，应到哪里寻找用户服务？
- Claim: 遇到学校信息化账号或网络使用问题时，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-013-C002 · AMBIGUOUS

- Question: 遇到学校信息化账号或网络使用问题时，应到哪里寻找用户服务？
- Claim: 应到用户服务大厅寻求帮助。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-014-C001 · AMBIGUOUS

- Question: 清华图书馆图书借还的规则和操作说明在哪里？
- Claim: 图书借还规则和操作说明在清华图书馆主页上。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-015-C001 · AMBIGUOUS

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 进入清华大学图书馆需要遵守以下入馆管理办法：
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-015-C002 · V1_MAPPING_FAILURE

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 校内读者凭本人有效图书证入馆。
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-015-C003 · V1_MAPPING_FAILURE

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 校外读者按规定办理手续后入馆。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-015-C004 · V1_MAPPING_FAILURE

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 清华校友凭校友卡或毕业证（或复印件），附上有效身份证件，
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-015-C005 · AMBIGUOUS

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 可进入校图书馆。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-015-C006 · TOP5_EVIDENCE_PARTIAL

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 注意防火安全，严禁在馆内吸烟。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-015-C007 · V1_MAPPING_FAILURE

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 饮料需置于防溢出容器内，不可携带气味食物、外卖盒餐等入馆。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-015-C008 · TOP5_EVIDENCE_PARTIAL

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 保持安静，手持电话置于静音状态。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-015-C009 · TOP5_EVIDENCE_PARTIAL

- Question: 进入清华大学图书馆需要遵守什么入馆管理办法？
- Claim: 衣着整齐，举止文明礼貌。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-016-C001 · AMBIGUOUS

- Question: 清华师生如何使用馆际互借服务获取外馆文献？
- Claim: 清华师生可通过馆际互借服务获取外馆文献。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-017-C002 · AMBIGUOUS

- Question: 综合体育馆的建筑面积、观众席位和赛事用途是什么？
- Claim: 可满足国际比赛和现场电视转播的要求。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-018-C002 · V1_MAPPING_FAILURE

- Question: 清华大学特等奖学金采用什么评选办法？
- Claim: 评选机构通过现场答辩形式组织复评，形成推荐名单，提请校务会议审议。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-018-C003 · V1_MAPPING_FAILURE

- Question: 清华大学特等奖学金采用什么评选办法？
- Claim: 校务会议讨论决定特等奖学金表彰名单。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-018-C004 · V1_MAPPING_FAILURE

- Question: 清华大学特等奖学金采用什么评选办法？
- Claim: 特等奖学金表彰名单在学校信息门户网站予以公示。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-019-C002 · V1_MAPPING_FAILURE

- Question: 国家助学贷款发放后，学生应遵守哪些贷后管理规定？
- Claim: 做好贷款学生信息建档工作。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-019-C003 · AMBIGUOUS

- Question: 国家助学贷款发放后，学生应遵守哪些贷后管理规定？
- Claim: 做好诚信教育工作。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-019-C005 · AMBIGUOUS

- Question: 国家助学贷款发放后，学生应遵守哪些贷后管理规定？
- Claim: 未按合同规定的用途使用贷款；
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-019-C006 · TOP5_EVIDENCE_PARTIAL

- Question: 国家助学贷款发放后，学生应遵守哪些贷后管理规定？
- Claim: 违法乱纪行为受到学校纪律处分或有关部门刑事处罚；
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-019-C007 · V1_MAPPING_FAILURE

- Question: 国家助学贷款发放后，学生应遵守哪些贷后管理规定？
- Claim: 中途辍学、退学、转学、被学校开除或取消学籍；
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-019-C008 · AMBIGUOUS

- Question: 国家助学贷款发放后，学生应遵守哪些贷后管理规定？
- Claim: 学习不刻苦
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-020-C001 · AMBIGUOUS

- Question: 国际学生如何区分并查询不同的签证类型？
- Claim: 国际学生可查询不同签证类型如下：X1签证颁发给长期学习，
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-020-C003 · V1_MAPPING_FAILURE

- Question: 国际学生如何区分并查询不同的签证类型？
- Claim: X2签证颁发给短期学习，有效期以签证注明为准。
- V2 label: SUPPORTED
- Full-corpus diagnostic: AMBIGUOUS

### PROV-023-C002 · AMBIGUOUS

- Question: 学生想进行一对一生涯咨询、简历修改或模拟面试，可以找什么服务？
- Claim: **生涯咨询**：李锋亮、马昱春、王大亮
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-023-C003 · AMBIGUOUS

- Question: 学生想进行一对一生涯咨询、简历修改或模拟面试，可以找什么服务？
- Claim: **简历修改**：朱李婧、陈旭东、董亮、赵梦圆
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-023-C004 · AMBIGUOUS

- Question: 学生想进行一对一生涯咨询、简历修改或模拟面试，可以找什么服务？
- Claim: **模拟面试**：张杨、关麟凤、俞婷君
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-024-C001 · GENERATION_HALLUCINATION

- Question: 清华科研仪器共享平台能否查询开放设备并预约测试？
- Claim: 可以查询开放设备并预约测试，详情请访问清华仪器共享服务平台。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-025-C001 · V1_MAPPING_FAILURE

- Question: 清华通讯作者在IEEE开放获取期刊发表论文有何APC优惠？
- Claim: 通讯作者为我校师生在IEEE金色OA期刊或混合OA期刊发表OA论文时，
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-025-C002 · AMBIGUOUS

- Question: 清华通讯作者在IEEE开放获取期刊发表论文有何APC优惠？
- Claim: 可获得9折费用折扣。
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-025-C003 · TOP5_EVIDENCE_PARTIAL

- Question: 清华通讯作者在IEEE开放获取期刊发表论文有何APC优惠？
- Claim: 优惠范围包括Full Open Access与Hybrid Open Access期刊。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-025-C004 · TOP5_EVIDENCE_PARTIAL

- Question: 清华通讯作者在IEEE开放获取期刊发表论文有何APC优惠？
- Claim: 优惠时间截至2026年12月31日。
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C001 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 单位号：000 建筑学院 jzxy；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C002 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 003 土木系 tmx；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C003 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 004 水利系 slx；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C004 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 005 环境学院 hjxy；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C005 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 011 机械学院 jxxy；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C006 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 012 机械系 jxx；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C007 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 013 精仪系 jyx；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C008 · TOP5_EVIDENCE_PARTIAL

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 014 能动系 ndx；
- V2 label: PARTIALLY_SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C009 · AMBIGUOUS

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 015 车辆学院 clxy；
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C010 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 016 工业工程系 gygcx；
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C011 · V1_MAPPING_FAILURE

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 021 信息学院 xxxy。
- V2 label: SUPPORTED
- Full-corpus diagnostic: NOT_FOUND_IN_CORPUS

### PROV-028-C012 · AMBIGUOUS

- Question: 如何查询清华各院系的单位号、简称和英文名称？
- Claim: 简称：建筑学院、土木工程系
- V2 label: UNSUPPORTED
- Full-corpus diagnostic: AMBIGUOUS
