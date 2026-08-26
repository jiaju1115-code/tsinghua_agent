# Fine-tuning Pilot V0 Failure Analysis V1

## Executive conclusion

Pilot V0 changed General accuracy from 22.0% to 30.0% (delta +8.0%). There were 11 wins and 3 regressions. Forgetting assessment: `NO_CLEAR_FORGETTING`. The gain is concentrated in strict format and constraint compliance, not broad reasoning: General Reasoning, Linear Algebra, Mathematical Reasoning, and Probability remain 0% for both models.

## Paired results

| Metric | Base | Pilot V0 | Delta |
|---|---:|---:|---:|
| Correct | 22/100 | 30/100 | +8 |
| Accuracy | 22.0% | 30.0% | +8.0% |

WIN 11; REGRESSION 3; BOTH_PASS 19; BOTH_FAIL 67.

## Main regression profile

Two instruction-value fidelity regressions and one basic-science factual regression were observed. No third regression category exists in this run. Detailed evidence is preserved in `regressions.jsonl`.

## Data diagnosis

The 680-row figure is acquisition V1.1, not the final Pilot input. V1.2 has 841 rows, including 300 programmatic-math rows (35.67%); Pilot used a 757/84 split. Mathematical reasoning is 59.3% of train rows and all math families are 71.2%. Code (8 rows), science (1), and non-math reasoning (46) are sparse. This imbalance is a `POSSIBLE_CAUSE`, not proof of causality.

## Training diagnosis

Verdict: `LIKELY_DATA_ISSUE`. Two epochs, LR 1e-4, effective batch 16, LoRA r=16/alpha=32, assistant-completion-only loss, and q/k/v/o targeting provide no direct evidence of excessive intensity. Keep them fixed for a composition-only V1 attribution run. If regression persists, test a modest LR reduction separately.

## Pilot V1 recommendation

Use targeted rebalancing to 1100-1350 General replay cases. Prioritize instruction value fidelity, deterministic general reasoning, and QA/science/reading. Maintain code with a smaller diverse slice, add non-programmatic math diversity, and cap programmatic math near 10-12%. Predefined gate: `CONDITIONAL_GO`: no overall General regression, fewer regressions than V0, no severe family collapse, and target/Campus behavior maintained.

## Acquisition decision

`READY_FOR_TARGETED_DATA_ACQUISITION`
