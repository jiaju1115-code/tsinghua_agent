# General Capability Data Acquisition V2.1 — Revision-Pinned Recovery

## 1. Revision Resolution
| Dataset | Full Commit SHA | Config | Split | Status |
|---|---|---|---|---|
| nvidia/Nemotron-Instruction-Following-Chat-v1 | 83dcd3aded0d289b0bbc018d3f9af4c5dd4005df | default | structured_outputs | RESOLVED |
| allenai/tulu-3-sft-personas-instruction-following | fe0c7d350c9b4542b8d829a6f1daa1c259f0ba0e | default | train | RESOLVED |
| databricks/databricks-dolly-15k | bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a | default | train | RESOLVED |
| rajpurkar/squad | 7b6d24c440a36b6815f21b70d25016731768db1f | plain_text | train | RESOLVED |
| tasksource/ruletaker | a3e0880baeb6ec3d478f4c4d85afe04b21b6cf7f | default | train | RESOLVED |
| facebook/babi_qa | 021d7aeb7307b7856dd0632f92827bc607dc2f1b | en-10k-qa1 | train | RESOLVED |
| nvidia/OpenCodeInstruct | 8f3ba5bafe4d6e8db46082cf7ae6741bc370604d | train | train | RESOLVED |
| google-research-datasets/mbpp | 4bb6404fdc6cacfda99d4ac4205087b89d32030c | full | train | RESOLVED |

## 2. Replay Summary
* Stage 2 candidates: 1190
* Successfully replayed: 780
* Exact raw match: 780
* Normalized match: 0
* Content mismatch: 0
* Not found: 310

## 3. Accepted Recovery
* Legacy accepted: 402
* Revision-verified accepted: 364
* Verification rate: 90.5%

| Family | Legacy Accepted | Verified Accepted | Target | Remaining Gap |
|---|---:|---:|---:|---:|
| INSTRUCTION_VALUE_FIDELITY | 42 | 40 | 263 | 223 |
| GENERAL_QA_SCIENCE_READING | 152 | 152 | 209 | 57 |
| GENERAL_REASONING | 102 | 102 | 189 | 87 |
| WRITING_MULTILINGUAL | 42 | 42 | 30 | 0 |
| CODING | 64 | 28 | 87 | 59 |

## 4. Acceptance Reproducibility
* REJECT->None: 372
* ACCEPT->None: 38
* ACCEPT->ACCEPT: 364
* REJECT->REJECT: 416

## 5. Source Yield
Source-level requested/replayed/accepted figures are in the recovery matrix and summary.

## 6. Instruction Yield Diagnosis
The frozen Stage 2 rules, not new thresholds, determine the replay result; source-by-source reject reasons remain attributable in replay artifacts.

## 7. Dedup / Leakage / License
* General V0.1 accepted leakage: 0
* License: PASS
* Input integrity: True

## 8. Remaining Gap
| Family | Remaining Accepted Gap | Recommended Next Action |
|---|---:|---|
| INSTRUCTION_VALUE_FIDELITY | 223 | REVISIT_SOURCE_SELECTION |
| GENERAL_QA_SCIENCE_READING | 57 | CONTINUE_TIER1_TOP_UP |
| GENERAL_REASONING | 87 | CONTINUE_TIER1_TOP_UP |
| WRITING_MULTILINGUAL | 0 | NO_TOP_UP_NEEDED |
| CODING | 59 | CONTINUE_TIER1_TOP_UP |

## 9. Decision
`REVISION_PROVENANCE_RECOVERED`

## 10. Main Artifacts
See the V2.1 data and evaluation directories.
