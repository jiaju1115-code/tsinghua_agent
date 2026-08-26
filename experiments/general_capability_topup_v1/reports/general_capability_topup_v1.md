# Targeted General Top-up V1

## Result

`GENERAL_TOPUP_INSUFFICIENT`

The top-up reused only already audited sources and cached rows. V1.1 contained 680 candidates; 558 raw top-up rows were inspected and 161 new candidates were accepted after cross-deduplication, producing 841 total candidates.

Final distribution: General instruction 181, calculus 12, linear algebra 78, probability/statistics 10, mathematical reasoning 499, basic science 1, general reasoning 51, basic code 9.

The result remains below the 850 stopping threshold and the weak-family coverage is still insufficient, especially basic science, calculus, probability/statistics, and code. Programmatic math is 300/841 = 35.67%, slightly above the 35% monitoring target; no further GEmO expansion was performed. License, benchmark leakage, holdout, and Campus cross-leakage audits passed. Campus and production were unchanged. Final split and training remain NO.
