# Held-out E2E Evaluation V1

Status: `HELD_OUT_E2E_V1_DATASET_FROZEN`.

This is a 50-case held-out dataset for one-shot end-to-end evaluation of the frozen Unified E2E Orchestrator V1. It contains no system answers, expected statuses, or model-generated labels. Development, prompt, threshold, runtime, and retrieval work must not read or use these cases.

The next authorized stage runs the frozen dataset once only:

`python evaluation/e2e_heldout/v1/runner/run_e2e_50.py --execute`
