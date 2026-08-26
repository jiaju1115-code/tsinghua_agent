# General Capability Data Acquisition V1.1

## Result

`GENERAL_DATA_READY_WITH_LIMITATIONS`

Actual selective acquisition completed through the official Hugging Face Dataset Server. Downloaded/retained source rows: 805 / 680 after filtering and normalized deduplication. Sources used: OASST1 181, MathInstruct 299, GEmO 200. Programmatic math: 200 (29.4%), explicitly labeled `PROGRAMMATIC_MATH`.

License audit: PASS. Benchmark leakage audit: PASS; GSM8K, MMLU and ARC remain EVAL_ONLY. General holdout protection: PASS. Campus cross-leakage: 0. Duplicate removal: 125. Production and Campus assets unchanged.

The pool is below the requested 800 minimum and lacks sufficient dedicated calculus, linear algebra, probability/statistics, science, reasoning and code coverage. Therefore this round stops at `GENERAL_DATA_READY_WITH_LIMITATIONS`; no final split or training is started.
