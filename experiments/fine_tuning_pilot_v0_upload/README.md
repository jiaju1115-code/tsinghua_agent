# Fine-tuning Pilot V0

This is an upload-ready experimental LoRA package, not a final training dataset and not a training result. It uses the frozen current General pool `general_capability_candidates_v1_2` (841 rows) and the fixed base model `Qwen/Qwen2.5-1.5B-Instruct`. Campus, production, frozen evaluations, and the General source pool are not modified.

## Package status

- Experimental split: YES; 757 train / 84 validation; seed 42; family-stratified.
- Test set: NO. Future General/Campus test data remains independent and frozen.
- Training executed: NO. GPU validation is pending.
- Default method: LoRA, `r=16`, `alpha=32`, dropout `0.05`, learning rate `1e-4`, two epochs.
- Authoritative Qwen-token audit (pre-truncation, complete Qwen chat template): median 265, P90 595, P95 739, max 1416. One sample (0.12%) exceeds 1024; none exceed 2048. Default `max_seq_length=2048` retains every audited sample.
- The earlier 653 / 1735 / 2049 / 3705 figures were character counts from `inspect_dataset.py`, not token counts; see `audit/token_length_discrepancy_audit.json`.
- Supervision is assistant-completion-only: user and chat-template system/prefix tokens are masked with `-100`; assistant completion tokens (including terminal message token) are supervised.
- Truncation safety keeps completion tokens first and truncates left-side context before any completion token. The current audit found no completion truncation at 2048.
- Runtime target: NVIDIA A800 80GB PCIe; batch size 8 × gradient accumulation 2 (effective batch 16), bf16 enabled, fp16 disabled, and gradient checkpointing disabled. QLoRA/bitsandbytes are not used.
- Family-aware sampler is deterministic (seed 42), epoch-aware, draws 757 rows per epoch, targets 35% Mathematical Reasoning, and samples the remaining 65% from the non-math pool according to its original aggregate distribution.
- Static input integrity is separate from runtime-generated audits/logs. `run_validate.sh` validates the frozen uploaded split and does not regenerate it.

## Remote Linux GPU usage

From this directory:

```bash
bash run_environment_check.sh
bash run_validate.sh
bash run_train.sh
```

The environment check must report CUDA and bf16 support. CPU fallback is intentionally refused. Install `requirements.txt` first. `run_train.sh` verifies static input hashes and base-model access before invoking the GPU-only entry point. Training outputs are isolated under `outputs/<run_id>/`; the adapter is not merged or converted to GGUF.

## Evaluation and rollback

Run the existing baseline/reference evaluations before and after the pilot. General capability should improve without a clear Campus grounding, refusal, citation, or unsupported-claim regression. Keep the adapter separate; do not merge it or convert it to GGUF. Rollback is deleting/ignoring the pilot adapter and retaining the unchanged base model and production runtime.
