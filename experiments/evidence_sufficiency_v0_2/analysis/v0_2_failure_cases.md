# V0.2 failure cases

## REAL_INTERNAL_HOLDOUT: PROV-023 — MISSED_SUFFICIENT

- Query: 学生想进行一对一生涯咨询、简历修改或模拟面试，可以找什么服务？
- Expected / predicted: EVIDENCE_SUFFICIENT / EVIDENCE_PARTIAL
- Required points: ["一对一生涯咨询可找什么服务", "简历修改服务", "模拟面试服务"]
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 3, "supported": 2, "partial": 0, "unsupported": 1}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: support-span threshold or required-point decomposition rejected usable evidence.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-WRONG_DOCUMENT-026 — ENTITY_MISMATCH_MISSED

- Query: 学生职业发展指导中心面向学生提供哪些就业服务？
- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 1, "supported": 0, "partial": 1, "unsupported": 0}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: WRONG_DOCUMENT construction was mapped to the wrong coverage severity.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-WRONG_DOCUMENT-011 — ENTITY_MISMATCH_MISSED

- Query: 清华学生社团的建设、成立和日常管理依据什么办法？
- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 3, "supported": 2, "partial": 0, "unsupported": 1}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: WRONG_DOCUMENT construction was mapped to the wrong coverage severity.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-WRONG_DOCUMENT-036 — ENTITY_MISMATCH_MISSED

- Query: 清华学生奖学金、助学金申请和评选办法是什么？
- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 3, "supported": 2, "partial": 1, "unsupported": 0}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: WRONG_DOCUMENT construction was mapped to the wrong coverage severity.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-PARTIAL_COVERAGE-003 — PARTIAL_AS_INSUFFICIENT

- Query: 清华校园网如何接入，账号或网络故障如何处理？
- Expected / predicted: EVIDENCE_PARTIAL / EVIDENCE_INSUFFICIENT
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 2, "supported": 0, "partial": 0, "unsupported": 2}
- Reason codes: EVIDENCE_CONTAMINATION|NO_CORE_ANSWER|TOPIC_RELATED_NOT_ANSWERING
- Root cause: PARTIAL_COVERAGE construction was mapped to the wrong coverage severity.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-PARTIAL_COVERAGE-028 — PARTIAL_AS_INSUFFICIENT

- Query: 清华科研仪器共享平台能否查询开放设备并预约测试？
- Expected / predicted: EVIDENCE_PARTIAL / EVIDENCE_INSUFFICIENT
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 1, "supported": 0, "partial": 0, "unsupported": 1}
- Reason codes: EVIDENCE_CONTAMINATION|NO_CORE_ANSWER|TOPIC_RELATED_NOT_ANSWERING
- Root cause: PARTIAL_COVERAGE construction was mapped to the wrong coverage severity.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-QUERY_CONCEPT_MISMATCH-004 — CONCEPT_MISMATCH_MISSED

- Query: 清华学生奖学金、助学金申请和评选办法是什么？
- Expected / predicted: EVIDENCE_INSUFFICIENT / EVIDENCE_PARTIAL
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 3, "supported": 2, "partial": 1, "unsupported": 0}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: QUERY_CONCEPT_MISMATCH construction was mapped to the wrong coverage severity.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-SUFFICIENT_CONTROL-013 — MISSED_SUFFICIENT

- Query: 给住在清华学生社区的同学寄快递时，邮寄地址和邮编在哪里查？
- Expected / predicted: EVIDENCE_SUFFICIENT / EVIDENCE_PARTIAL
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 3, "supported": 1, "partial": 1, "unsupported": 1}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: support-span threshold or required-point decomposition rejected usable evidence.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-SUFFICIENT_CONTROL-009 — MISSED_SUFFICIENT

- Query: 在校本科生或研究生办理在学证明，可以去哪里申请和打印？
- Expected / predicted: EVIDENCE_SUFFICIENT / EVIDENCE_PARTIAL
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 3, "supported": 2, "partial": 1, "unsupported": 0}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: support-span threshold or required-point decomposition rejected usable evidence.

## SYNTHETIC_STRESS_HOLDOUT: SYN-V02-SUFFICIENT_CONTROL-015 — MISSED_SUFFICIENT

- Query: 教职工想查询校内教工餐厅信息，应查看哪份校园服务资料？
- Expected / predicted: EVIDENCE_SUFFICIENT / EVIDENCE_PARTIAL
- Required points: []
- Support mapping snapshot: not persisted beyond the single formal holdout prediction; coverage={"total": 2, "supported": 1, "partial": 0, "unsupported": 1}
- Reason codes: KEY_INFORMATION_MISSING|PARTIAL_COVERAGE
- Root cause: support-span threshold or required-point decomposition rejected usable evidence.
