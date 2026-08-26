# Fine-tuning Dataset V1 Candidate Assets

## Scope

This work produces candidate pools only. It creates no train/validation/test
split, starts no LoRA/QLoRA training, downloads no external raw data, and changes
no production component.

## Campus assets

The frozen KB V1 contains 488 chunks and 30 approved source documents. Candidate
generation selected 29 unique-title approved chunks outside the held-out
scholarship source family. The resulting pools contain 29 `SUPPORTED`, 20
Gold-Policy-compliant `PARTIAL`, 23 `NOT_SUPPORTED`, 15 paraphrase positives,
11 frozen-Retriever-Top-5 mined negatives, and 29 grounded-answer candidates.
There are also 20 General-vs-Campus boundary-contrast pairs.

All 16 audited false promotes are retained as Gold hard-negative candidates. The
remaining seven policy-realigned cases are separated as `NOT_SUPPORTED` with
`HIGH_CONFIDENCE`, not silently merged into historical Gold.

## Safety and leakage

DEMO002, POS003, and DEMO013 are protected as held-out families. Exact/normalized
deduplication, parent-family checks, and held-out query scanning passed with zero
overlap. Partial candidates are the 20 existing controlled-evidence ablations:
no conflict, two independent points, one locatable support span, and one uncovered
point per case.

## General capability

Six Hugging Face dataset cards were audited. Only OASST1 is a future
metadata-only sample-review recommendation. Four benchmark-lineage datasets are
reserved for future evaluation, and OpenOrca is excluded for this controlled first
pass. Six project-authored schema seeds cover calculus, linear algebra,
probability/statistics, reasoning, science, and code; they are not claimed as
downloaded Hugging Face samples.

## Decision

**CAMPUS_READY_GENERAL_DATA_PENDING**

Campus and safety candidate pools are ready, but licensed, revision-pinned,
sample-level General Capability data has not been acquired or reviewed. The next
task may decide whether to download a small OASST1 sample after a final license and
content filter design. Do not create final splits or start training automatically.
