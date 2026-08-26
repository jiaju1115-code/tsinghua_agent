# Fine-tuning Pilot V1 — Hugging Face Dataset Discovery

## Scope and frozen baseline

This is **General Capability Data Acquisition V2, Stage 1**. It reviewed dataset cards, licenses, revisions, schemas, official upstream descriptions, and small Hugging Face Dataset Viewer previews. It did **not** download formal training data, construct Pilot V1, modify the V1.2 pool, alter `proposed_keep` / `proposed_drop`, or run training.

The formal preflight artifacts were re-read. The frozen accepted gaps are:

| Family | Existing KEEP | Target | Accepted gap |
|---|---:|---:|---:|
| Instruction / Value Fidelity | 37 | 300 | 263 |
| General QA / Science / Reading | 55 | 264 | 209 |
| General Reasoning | 51 | 240 | 189 |
| Writing / Multilingual | 90 | 120 | 30 |
| Coding | 9 | 96 | 87 |
| Programmatic Math | 120 | 120 | 0 — DO_NOT_ADD |
| Other Math | 60 | 60 | 0 — DO_NOT_ADD |

Total accepted gap: **778**. The historical 28.85% yield was not applied mechanically. Source-specific preview quality and filtering burden produce a recommended **1,190 candidate reads → about 891 accepted**, leaving a 113-row quality/dedup buffer. Acquisition envelope: minimum 1,040; recommended 1,190; hard upper bound 1,420.

## Tier 1 primary sources

| Family | Dataset / allowed component | License | Grade | Candidates | Expected accepted |
|---|---|---|---:|---:|---:|
| Instruction / Value Fidelity | [NVIDIA Nemotron IF Chat v1](https://huggingface.co/datasets/nvidia/Nemotron-Instruction-Following-Chat-v1), `structured_outputs` only | CC-BY-4.0 | B | 220 | 187 |
| Instruction / Value Fidelity | [AI2 Tulu 3 personas IF](https://huggingface.co/datasets/allenai/tulu-3-sft-personas-instruction-following), verifiable constraints | ODC-BY-1.0 | B | 120 | 78 |
| Instruction / Value Fidelity | [Databricks Dolly 15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k), extraction/classification | CC-BY-SA-3.0 | B | 60 | 42 |
| QA / Science / Reading | Dolly, closed/context-grounded QA only | CC-BY-SA-3.0 | B | 180 | 126 |
| QA / Science / Reading | [SQuAD 1.1](https://huggingface.co/datasets/rajpurkar/squad), train only | CC-BY-SA-4.0 | A | 140 | 112 |
| General Reasoning | [RuleTaker](https://huggingface.co/datasets/tasksource/ruletaker), train only, depth/config-stratified | Apache-2.0 | B | 200 | 144 |
| General Reasoning | [bAbI QA](https://huggingface.co/datasets/facebook/babi_qa), English train only, task-balanced | CC-BY-3.0 | B | 100 | 68 |
| Writing / Multilingual | Dolly, constrained summarization | CC-BY-SA-3.0 | B | 30 | 24 |
| Writing / Multilingual | Tulu 3, objective rewrite/controlled generation | ODC-BY-1.0 | B | 20 | 14 |
| Coding | [NVIDIA OpenCodeInstruct](https://huggingface.co/datasets/nvidia/OpenCodeInstruct), all-tests-pass safe pure functions | CC-BY-4.0 | B | 90 | 72 |
| Coding | [Google MBPP](https://huggingface.co/datasets/google-research-datasets/mbpp), full/train task IDs 601–974 only | CC-BY-4.0 | A | 30 | 24 |
| **Total** | 8 unique Tier 1 repositories | — | — | **1,190** | **891** |

Why these sources:

- Nemotron `structured_outputs` directly exercises schema adherence and exact value preservation; the card names its generators and verifier/LLM-judge filtering. Only the CC-BY-4.0 structured component is allowed.
- Tulu 3 supplies explicit 1–3 item constraint labels. Its exact generator model is not named on the card, so it remains grade B and must pass local structural checks.
- Dolly is human-authored and category-addressable. Viewer samples also show typos and occasional questionable open-domain answers, so only deterministic categories are allowed.
- SQuAD supplies high-quality context/question/answer spans. It is benchmark-derived, so train-only use comes with permanent lineage exclusion from evaluation.
- RuleTaker and bAbI provide deterministic rule, set, relation, and finite-state tasks without requiring chain-of-thought completions. Their template risk is controlled by depth/task stratification and per-template caps.
- OpenCodeInstruct exposes unit tests and execution status. The preview also contains failed and filesystem-dependent rows, which are explicitly ineligible.
- MBPP is the smallest coding source and is limited to the official `full/train` IDs 601–974. The evaluation/test/sanitized evaluation components remain prohibited.

## Quality gates for controlled acquisition

Every candidate must pass all applicable gates before it can become accepted data:

1. Revision and component must exactly match the selection manifest.
2. License/component metadata and attribution record must be retained per row.
3. Exact, normalized, high-lexical, and semantic-near-duplicate checks must run against General V0.1, V1.2, proposed KEEP/DROP, and all newly accepted rows.
4. General V0.1 simple JSON echo/list-copy patterns and paraphrases are excluded; instruction candidates must add multi-condition or nontrivial value-fidelity behavior rather than evaluator imitation.
5. Benchmark-derived sources are train-only. All sibling validation/test splits and the entire selected dataset lineage are permanently disqualified from current and future evaluation.
6. Rationale/proof/`reasoning_content` is not the completion target. Reasoning targets are concise gold labels/answers only.
7. Coding rows must be pure, deterministic, locally unit-testable, and free of shell, network, filesystem, package-install, security/exploit, or computer-control behavior.
8. Template caps and source caps apply before acceptance. No source may dominate the 778-row top-up.

## Backup sources

- [OpenAssistant/oasst1](https://huggingface.co/datasets/OpenAssistant/oasst1) — PASS/B, but it already contributes 242 of 422 proposed KEEP rows. Do not acquire more unless Tier 1 filtering leaves a documented shortfall.
- [HuggingFaceH4/no_robots](https://huggingface.co/datasets/HuggingFaceH4/no_robots) — A-quality human SFT, but CC-BY-NC-4.0 makes it REVIEW-only.
- [AllenAI SciQ](https://huggingface.co/datasets/allenai/sciq) — useful supported basic-science QA, but CC-BY-NC-3.0 and benchmark lineage make it REVIEW-only.
- [Google Natural Questions](https://huggingface.co/datasets/google-research-datasets/natural_questions) — clear CC-BY-SA-3.0, but huge HTML records, web/time-sensitive content, no-answer cases, and low acquisition efficiency reduce it to C-grade fallback. Dataset Server only if ever activated.
- [Yale FOLIO](https://huggingface.co/datasets/yale-nlp/FOLIO) — less templated expert logic, but gated access conditions were not accepted or audited in this stage.

## Rejected sources

- `sahil2801/CodeAlpaca-20k`: HF says CC-BY-4.0 while the [upstream DATA_LICENSE](https://github.com/sahil280114/codealpaca/blob/master/DATA_LICENSE) is CC-BY-NC-4.0; viewer samples are untested and include unsafe categories. FAIL.
- `Muennighoff/natural-instructions`: no dataset-wide license and its component files visibly include DROP, BigBench, SQuAD, PIQA and other benchmark tasks. FAIL.
- `tasksource/stepgame`: extreme template concentration and apparent statement/label inconsistencies in the viewer preview. Grade D.
- `allenai/openbookqa`: HF card license is unknown. FAIL.
- `Open-Orca/OpenOrca`: very large synthetic benchmark mixture with provenance/decontamination burden disproportionate to this pilot.
- `allenai/ai2_arc`: project policy already reserves it for future evaluation.
- GSM8K, MATH, HumanEval, benchmark eval/test splits: explicit exclusions.
- GEmO and MathInstruct: acquisition stops completely because both math families are `DO_NOT_ADD`.

## License conclusion

All Tier 1 components are PASS, but PASS means “terms are clear,” not “no obligations.” CC-BY and Apache sources require attribution/notices; CC-BY-SA sources require attribution and ShareAlike handling for redistributed adapted material; ODC-BY requires database attribution. Component-level licensing is mandatory for Nemotron. No NC, unknown-license, gated-unreviewed, or conflicting-license source is Tier 1.

## Leakage conclusion

General V0.1 is a frozen, seeded, programmatically authored 100-case evaluation with zero previously detected overlap against the 841-row pool. The selected datasets are not its source. Nevertheless, structured-output patterns can be semantically close, so candidate-level exact/normalized/lexical/semantic checks remain mandatory.

Benchmark-derived Tier 1 use is defensible only with the following irreversible boundary: SQuAD train, RuleTaker train, bAbI train, and MBPP full/train IDs 601–974 become training-source lineages; their validation/test/eval siblings and derived paraphrases can never be used for Pilot V1 or future evaluation. Future holdouts must remain independently authored, consistent with the existing `general_holdout_policy.json`.

## Existing source decisions

- **OASST1:** keep the accepted existing rows; do not expand it in the primary plan because it already forms 57.3% of proposed KEEP (242/422). It remains a Tier 2 emergency source.
- **GEmO / MathInstruct:** stop acquisition completely for this phase. Existing retained math is already at target after downsampling.

## Decision

`READY_FOR_CONTROLLED_HF_ACQUISITION`

This authorizes only the revision-pinned, component-limited, candidate-count-limited Stage 2 reads in `family_source_allocation.json`. It does not authorize bulk download, dataset construction, training, or Tier 2 activation.
