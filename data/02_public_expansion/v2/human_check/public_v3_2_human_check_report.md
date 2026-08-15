# Public Expansion V2 — V3.2 Human Check Evaluation

## 1. Completeness Check

PASS. `Human Check` is the sole worksheet. There are 49 valid rows, exactly `HC0001`–`HC0049`, with unique `check_id` and `original_id`. All human actions, reject types (when required), and notes are populated and legal. Whitespace/newlines were normalized only while reading; no human-source cell was modified.

## 2. Input Freeze

Frozen sole input: `data/02_public_expansion/v2/human_check/public_v3_2_human_check_adjudicated.xlsx`. SHA256 `b6640c3a871f0d42e724452f2569935fd6f9131d817e3cd4d7076fe8719a5c9c`; 84040 bytes; modified UTC `2026-08-14T15:37:56.551741Z`; 49 data rows. Fields: check_id, original_id, title, url, domain, category, content_type, topic_relevance, time_status, v3_2_action, v3_2_reject_type, v3_2_reason, cleaned_content, human_action, human_reject_type, human_note. The adjudicated XLSX, `human_check_rows.json`, and previous V2 frozen materials were not modified.

## 3. Human Label Distribution

`human_action` is the human reference for this sample evaluation, not an absolute gold truth.

| action | V3.2 | human reference |
| --- | ---: | ---: |
| approve | 22 / 49 (44.90%) | 25 / 49 (51.02%) |
| review | 15 / 49 (30.61%) | 8 / 49 (16.33%) |
| reject | 12 / 49 (24.49%) | 16 / 49 (32.65%) |

## 4. Agreement Metrics

Confusion matrix (V3.2 rows × human-reference columns):

| V3.2 \ human | approve | review | reject |
| --- | ---: | ---: | ---: |
| approve | 19 / 49 (38.78%) | 0 / 49 (0.00%) | 3 / 49 (6.12%) |
| review | 6 / 49 (12.24%) | 6 / 49 (12.24%) | 3 / 49 (6.12%) |
| reject | 0 / 49 (0.00%) | 2 / 49 (4.08%) | 10 / 49 (20.41%) |

Exact sample agreement: 35/49 (71.43%). Cohen’s Kappa: 0.554256.

| class (human reference) | precision | recall | F1 |
| --- | ---: | ---: | ---: |
| approve | 19/22 (86.36%) | 19/25 (76.00%) | 80.85% |
| review | 6/15 (40.00%) | 6/8 (75.00%) | 52.17% |
| reject | 10/12 (83.33%) | 10/16 (62.50%) | 71.43% |

Macro F1: 68.15%.

## 5. False Approve

Possible knowledge-base contamination (`V3.2=approve`, human reference=`review` or `reject`): 3/49 (6.12%). All are included in the disagreement JSONL and specifically classified `false_approve`.

## 6. Over-reject

`V3.2=reject`, human reference=`approve` or `review`: 2/49 (4.08%).

## 7. Review Boundary

Exactly one side is `review`: 11/49 (22.45%). Breakdown: `review_to_approve` 6/49 (12.24%); `review_to_reject` 3/49 (6.12%); false-approve-to-review 0/49 (0.00%); over-reject-to-review 2/49 (4.08%).

## 8. Reject-type Agreement

Applicable only where both actions are `reject`: 10/49 (20.41%). Type matches: 10/10 (100.00%). Human non-reject rows are excluded from the reject-type denominator.

## 9. Sampling Limitation

These are **sample agreement** results, not demonstrated **full-pool performance** for the 165-row pool. The supplied 49-row JSON contains no documented randomization, strata, weights, or inclusion probabilities, and the guide describes production quality sampling rather than a blind test. There is no evidence that the 49 rows represent all 165. Human reference does not mean gold label or absolute gold truth.

## 10. Audit

PASS. Scope was limited to input validation, freeze, metrics, and disagreement analysis. No prompt, candidate, raw V3.2 result, production knowledge base, or pre-existing freeze/report was changed. Disagreements: 14/49 (28.57%).

## 11. 主要产物路径

- `data/02_public_expansion/v2/human_check/public_v3_2_human_check_metrics.json`
- `data/02_public_expansion/v2/human_check/public_v3_2_human_check_disagreements.jsonl`
- `data/02_public_expansion/v2/human_check/public_v3_2_human_check_report.md`
- `data/02_public_expansion/v2/audit/public_v3_2_human_check_freeze.json`

HUMAN_CHECK_COMPLETE
