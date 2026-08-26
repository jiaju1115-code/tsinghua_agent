# General Capability Data Acquisition V2.2 — Targeted Source Reselection & OpenCode Recovery

## Current verified state
OpenCode recovery raises Coding from 28 to 64; total remaining accepted gap is 390.

## Existing Instruction sources
Nemotron STOP; Tulu and Dolly MINOR only. Their low yield is driven by source fit, not relaxed quality thresholds.

## New Instruction Tier 1
Hermes and ToolACE are CONFIRMED_SOURCE: Apache-2.0, full commit SHA, pinned JSON-file replay 12/12, fit 4.25, moderate template risk. Planned 370 candidates / 241 expected accepts / 18 buffer.

## OpenCode recovery
36/36 recovered with OPENCODE_RECOVERY_SUCCESS; accepted leakage remains zero.

## Other families
QA: small SQuAD plus Dolly grounded mix. Reasoning: cap RuleTaker and review one relational source; the provisional source cannot be automatically acquired. Coding: small MBPP and OpenCode plan only. Writing and math: zero acquisition.

## Decision
`READY_FOR_TARGETED_TOP_UP`

No top-up, dataset build, split, or training was executed.
