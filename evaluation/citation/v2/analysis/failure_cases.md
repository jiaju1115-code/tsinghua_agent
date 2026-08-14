# Citation Pipeline V2 Failure Cases

> 只展示真实案例；没有实际案例的类别明确记为未检测到。

## V1 unsupported → V2 successfully supported

- Claim: `RET-01-C002` — 该规定适用于全校本科生的学籍管理。
- Diagnosis: V1_MAPPING_FAILURE / AMBIGUOUS

## whole-chunk failure → span-level success

- Claim: `RET-01-C002` — 该规定适用于全校本科生的学籍管理。
- Diagnosis: V1_MAPPING_FAILURE / AMBIGUOUS

## entity alias success

未检测到满足条件的实际案例。

## numeric normalization success

- Claim: `PROV-025-C004` — 优惠时间截至2026年12月31日。
- V1/V2: UNSUPPORTED → PARTIALLY_SUPPORTED
- Chosen spans: ['PROV-025-PROV0-STGPUB-0203-0000-S0021']

## semantic similarity high but support false

- Claim: `RET-01-C001`
- Span: `RET-01-PROV0-STGPUB-0048-0000-S0005`
- Scores: embedding=0.7838, verifier=0.9944
- Veto flags: ['NUMERIC_MISMATCH']

## verifier false positive

- Anchor: `NUM-001` (NUMERIC_SWAP)
- Verifier score: 0.999967 at threshold 0.95
- Premise: (经2016~2017学年度第25次校务会议通过,2019~20学年度第30次校务会议修订)
- Hypothesis: (经2017~2017学年度第25次校务会议通过,2019~20学年度第30次校务会议修订)

## verifier false negative

未检测到满足条件的实际案例。

## hard safety rule veto

- Claim: `RET-01-C001`
- Span: `RET-01-PROV0-STGPUB-0048-0000-S0005`
- Scores: embedding=0.7838, verifier=0.9944
- Veto flags: ['NUMERIC_MISMATCH']

## evidence only outside Top-5

未检测到满足条件的实际案例。

## evidence not present anywhere in corpus

- Claim: `RET-02-C003` — 提出住宿申请，经批准后方可入住。
- Diagnosis: TOP5_EVIDENCE_PARTIAL / NOT_FOUND_IN_CORPUS

## generation hallucination

- Claim: `PROV-010-C001` — 在清华办理生育医疗费用报销需要查看以下程序：
- Diagnosis: GENERATION_HALLUCINATION / NOT_FOUND_IN_CORPUS

## source quality failure

- Claim: `PROV-009-C001` — 请查看清华接待服务中心的官方公众号或小程序，其中详细列出了校车线路、班次和校园出入口交通指引。
- Diagnosis: SOURCE_QUALITY_FAILURE / NOT_FOUND_IN_CORPUS

## partial support

- Claim: `RET-02-C003` — 提出住宿申请，经批准后方可入住。
- V1/V2: UNSUPPORTED → PARTIALLY_SUPPORTED
- Chosen spans: ['RET-02-PROV0-STGPUB-0001-0001-S0007']

## multiple spans required

- Claim: `PROV-002-C001` — 在校本科生或研究生办理在学证明，
- V1/V2: UNSUPPORTED → PARTIALLY_SUPPORTED
- Chosen spans: ['PROV-002-PROV0-STGPUB-0009-0000-S0008', 'PROV-002-PROV0-STGPUB-0009-0000-S0017']
