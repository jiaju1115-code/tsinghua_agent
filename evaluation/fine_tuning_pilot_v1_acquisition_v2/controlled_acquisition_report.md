# Controlled Acquisition & Quality Gate — Stage 2

## 1. Input Integrity
Frozen input hashes unchanged: **True**. Stage 1 revisions are recorded in `source_revisions.json`.

## 2. Acquisition Summary
| source | requested | inspected rows | candidate records |
|---|---:|---:|---:|
| nvidia/Nemotron-Instruction-Following-Chat-v1 | 220 | 220 | 220 |
| allenai/tulu-3-sft-personas-instruction-following | 120 | 120 | 120 |
| allenai/tulu-3-sft-personas-instruction-following | 20 | 20 | 20 |
| databricks/databricks-dolly-15k | 60 | 60 | 60 |
| databricks/databricks-dolly-15k | 180 | 180 | 180 |
| databricks/databricks-dolly-15k | 30 | 30 | 30 |
| rajpurkar/squad | 140 | 140 | 140 |
| tasksource/ruletaker | 200 | 200 | 200 |
| facebook/babi_qa | 100 | 20 | 100 |
| nvidia/OpenCodeInstruct | 90 | 90 | 90 |
| google-research-datasets/mbpp | 30 | 30 | 30 |

## 3. Family Acceptance
| family | gap | candidates | accepted | remaining | yield |
|---|---:|---:|---:|---:|---:|
| INSTRUCTION_VALUE_FIDELITY | 263 | 400 | 42 | 221 | 10.5% |
| GENERAL_QA_SCIENCE_READING | 209 | 320 | 152 | 57 | 47.5% |
| GENERAL_REASONING | 189 | 300 | 102 | 87 | 34.0% |
| WRITING_MULTILINGUAL | 30 | 50 | 42 | 0 | 84.0% |
| CODING | 87 | 120 | 64 | 23 | 53.3% |

## 4. Quality Gate
Reject reasons: {'HIDDEN_COT_DEPENDENCY': 179, 'TOO_LONG': 39, 'WRONG_FAMILY': 237, 'ALIGNMENT_FAIL': 4, 'SUBJECTIVE_GOLD': 7, 'CONTEXT_UNSUPPORTED': 150, 'TIME_SENSITIVE': 18, 'GOLD_AMBIGUOUS': 98, 'CODE_TEST_FAIL': 46, 'UNSAFE_CODE': 10}

## 5. Dedup & Leakage
Exact, normalized, and lexical screens ran against the frozen old pools and General V0.1; accepted General V0.1 leakage is zero. No preinstalled local embedding model was found, so no semantic model was downloaded or substituted.

## 6. License
All Stage 1 selected source licenses remain PASS.

## 7. Source Diversity
Dolly remains one underlying source; no accepted result is represented as independent publishers.

## 8. Decision
**ACQUISITION_BLOCKED**

The Dataset Server row API returned no immutable revision identifier and its
request contract does not expose a revision pin. The recorded Stage 1 hashes
are declared source revisions, but cannot be verified as the exact content
served in this run. Therefore the accepted rows must not be used to build Pilot
V1 until the same controlled selections are replayed from revision-addressable
source artifacts. No automatic top-up is authorized.

## 9. Artifacts
Data files and audit manifests are in the two Stage 2 output directories.
