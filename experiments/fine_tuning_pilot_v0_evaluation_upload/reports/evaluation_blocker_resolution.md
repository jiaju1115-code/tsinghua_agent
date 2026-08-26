# Evaluation Blocker Resolution

## Campus Held-out 50

The historical manifest declares `8194d0272a29fce8b5f97fea65c4efb47f96b0dc93b04f4a3da1865fa588582f` for `cases/e2e_50_cases.jsonl`. No project file has that raw-byte hash. The current 50-case file has raw SHA-256 `958887cf2ce556f85e37cfd281e985980d6dae4f7fc6f381d8da0cbd95483a16`, but its normalized-LF SHA-256 is exactly the historical value. IDs remain `E2E001` through `E2E050`.

Resolution: `SEMANTIC_MATCH_RAW_HASH_MISMATCH`. The likely cause is CRLF/LF byte representation. Raw canonical bytes were not recovered, the historical manifest was not modified, and runtime preflight records the provenance warning.

## General

`POST_TRAINING_BLIND_GENERAL_EVAL_V0_FROZEN` contains 100 new deterministic cases. It was constructed after training and before any Base or LoRA inference, with machine-checkable scoring and a generator seed of `20260817`. Its contamination audit against 757 training and 84 validation rows reports zero overlaps.
