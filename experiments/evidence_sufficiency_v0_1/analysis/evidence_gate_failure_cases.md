# Failure cases

## development: A08

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "SVD分解在最小二乘中的作用如何解释？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-9c5b42a6", "web-7a545601", "web-e91046d1", "web-1f21ab59", "web-7d79b7d5", "web-6bd6af84"]}]

## development: A26

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "Dijkstra算法为什么要求边权非负？", "status": "SUPPORTED", "evidence_ids": ["web-1f85cf96", "web-b635683d", "web-ad2f3495", "web-aedcc010", "web-6dbea31e", "web-846e3bc5", "web-1c430bc7", "web-fa6c8ce0", "web-68f80ff2"]}]

## development: G01

- Expected / predicted: EVIDENCE_SUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: MISSED_SUFFICIENT
- Required points: [{"point": "2026年量子计算领域有哪些最新新闻？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-898d0070", "web-72dd67c9", "web-a3d230de", "web-b497c3de", "web-e8039f50", "web-014cc809", "web-abf0f2e0", "web-3d5f7479", "web-a6afdbd2"]}]

## synthetic: SYN-PARTIAL-01

- Expected / predicted: EVIDENCE_PARTIAL / EVIDENCE_INSUFFICIENT
- Reason codes: EVIDENCE_CONTAMINATION, NO_CORE_ANSWER, QUERY_CONCEPT_MISMATCH, WRONG_DOCUMENT
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "清华校医院门诊", "status": "NOT_SUPPORTED", "evidence_ids": ["C1"]}, {"point": "报销", "status": "NOT_SUPPORTED", "evidence_ids": []}, {"point": "就医流程是什么", "status": "NOT_SUPPORTED", "evidence_ids": []}]

## synthetic: SYN-WRONG_DOCUMENT-02

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "清华大学图书馆如何借书", "status": "SUPPORTED", "evidence_ids": ["C1", "C2", "C3", "C4"]}, {"point": "使用电子资源", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["C3"]}, {"point": "查询开放时间", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["C3"]}]

## synthetic: SYN-TOPIC_RELATED_NOT_ANSWERING-02

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "清华大学图书馆如何借书", "status": "SUPPORTED", "evidence_ids": ["C1", "C2", "C3", "C4"]}, {"point": "使用电子资源", "status": "NOT_SUPPORTED", "evidence_ids": []}, {"point": "查询开放时间", "status": "NOT_SUPPORTED", "evidence_ids": []}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-02

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "清华大学图书馆如何借书", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["C2", "C3", "C5"]}, {"point": "使用电子资源", "status": "NOT_SUPPORTED", "evidence_ids": []}, {"point": "查询开放时间", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["C3", "C5"]}]

## synthetic: SYN-WRONG_DOCUMENT-03

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "清华大学医院能否通过北京114平台预约挂号？", "status": "SUPPORTED", "evidence_ids": ["C1", "C2", "C3", "C4", "C5"]}]

## synthetic: SYN-TOPIC_RELATED_NOT_ANSWERING-03

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "清华大学医院能否通过北京114平台预约挂号？", "status": "SUPPORTED", "evidence_ids": ["C1", "C2", "C3", "C4", "C5"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-03

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "清华大学医院能否通过北京114平台预约挂号？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["C1", "C2", "C4"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-04

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "进入清华大学图书馆需要遵守什么入馆管理办法？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["C1", "C2", "C3", "C4", "C5"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-05

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "电磁感应定律的物理含义是什么？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-3323851c", "web-638c138b", "web-7a3bac32", "web-92f7b351", "web-89a3afdd", "web-5facb77c"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-06

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "p值", "status": "NOT_SUPPORTED", "evidence_ids": []}, {"point": "显著性水平应该如何解释", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-3cc236ae", "web-d9ed61f9", "web-f09cfaa0"]}]

## synthetic: SYN-PARTIAL-06

- Expected / predicted: EVIDENCE_PARTIAL / EVIDENCE_INSUFFICIENT
- Reason codes: NO_CORE_ANSWER, TOPIC_RELATED_NOT_ANSWERING
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "p值", "status": "NOT_SUPPORTED", "evidence_ids": []}, {"point": "显著性水平应该如何解释", "status": "NOT_SUPPORTED", "evidence_ids": []}]

## synthetic: SYN-WRONG_DOCUMENT-07

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "SVD分解在最小二乘中的作用如何解释？", "status": "SUPPORTED", "evidence_ids": ["web-984f18bb"]}]

## synthetic: SYN-TOPIC_RELATED_NOT_ANSWERING-07

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "SVD分解在最小二乘中的作用如何解释？", "status": "SUPPORTED", "evidence_ids": ["web-984f18bb"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-07

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "SVD分解在最小二乘中的作用如何解释？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-9c5b42a6", "web-7a545601", "web-e91046d1", "web-1f21ab59", "web-7d79b7d5", "web-6bd6af84"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-08

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "单位根检验", "status": "NOT_SUPPORTED", "evidence_ids": []}, {"point": "协整关系有什么区别", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-1afbe31a", "web-fbb3b58d", "web-984f18bb"]}]

## synthetic: SYN-WRONG_DOCUMENT-09

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "Dijkstra算法为什么要求边权非负？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-898d0070", "web-a3d230de", "web-b497c3de", "web-abf0f2e0", "web-3d5f7479", "web-a6afdbd2"]}]

## synthetic: SYN-TOPIC_RELATED_NOT_ANSWERING-09

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "Dijkstra算法为什么要求边权非负？", "status": "SUPPORTED", "evidence_ids": ["web-898d0070", "web-a3d230de", "web-b497c3de", "web-abf0f2e0", "web-3d5f7479", "web-a6afdbd2"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-09

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "Dijkstra算法为什么要求边权非负？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-1f85cf96", "web-b635683d", "web-ad2f3495", "web-aedcc010", "web-6dbea31e", "web-846e3bc5", "web-1c430bc7", "web-fa6c8ce0", "web-68f80ff2"]}]

## synthetic: SYN-WRONG_DOCUMENT-10

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "2026年量子计算领域有哪些最新新闻？", "status": "SUPPORTED", "evidence_ids": ["web-8b0dad46", "web-d856ef8c", "web-3e58a91b", "web-f9f5f6ec"]}]

## synthetic: SYN-TOPIC_RELATED_NOT_ANSWERING-10

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_SUFFICIENT
- Reason codes: FULL_COVERAGE
- Failure class: FALSE_SUFFICIENT
- Required points: [{"point": "2026年量子计算领域有哪些最新新闻？", "status": "SUPPORTED", "evidence_ids": ["web-8b0dad46", "web-d856ef8c", "web-3e58a91b", "web-f9f5f6ec"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-10

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "2026年量子计算领域有哪些最新新闻？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-898d0070", "web-72dd67c9", "web-a3d230de", "web-b497c3de", "web-e8039f50", "web-014cc809", "web-abf0f2e0", "web-3d5f7479", "web-a6afdbd2"]}]

## synthetic: SYN-CONTAMINATED_EVIDENCE-11

- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Reason codes: EVIDENCE_CONTAMINATION, KEY_INFORMATION_MISSING, PARTIAL_COVERAGE
- Failure class: PARTIAL_AS_INSUFFICIENT
- Required points: [{"point": "哪个国家的人口最多？", "status": "PARTIALLY_SUPPORTED", "evidence_ids": ["web-3bceb1d8", "web-2795eafa", "web-ef19adad", "web-8b0dad46", "web-d856ef8c", "web-3e58a91b", "web-f9f5f6ec", "web-96915a1a", "web-ad40f2c1"]}]
