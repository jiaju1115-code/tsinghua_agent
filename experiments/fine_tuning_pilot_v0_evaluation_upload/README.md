# Fine-tuning Pilot V0 Evaluation Package

This package performs a strictly paired, offline comparison of the Base model and the unmerged Pilot V0 LoRA. It never trains, merges adapters, converts GGUF, changes production, mutates frozen assets, calls an external LLM/API, or uses validation data as a test set.

## What is prepared

- Campus Layer A: the current 50-case copy has a SHA-256 mismatch against its own freeze manifest (`958887…` actual vs `8194d0…` recorded). It is packaged for forensic review only, and preflight blocks execution until reconciled. If reconciled, both models receive identical system prompt, evidence, chat template, decoding policy, seed, and max tokens.
- Campus scoring: deterministic, rule-based `PROVISIONAL` proxies only. The frozen cases intentionally have no generated answers/gold correctness labels, so correctness/required-point/partial-answer metrics remain unavailable rather than fabricated.
- Campus Layer B: `NOT_EXECUTED`; this package does not modify or insert a model into the frozen production system.
- General V0 is retained but retired before inference due to duplicate-prompt composition. General V0.1 is `POST_TRAINING_BLIND_GENERAL_EVAL_V0_1_FROZEN`: 100 unique, deterministic, machine-checkable cases constructed after training and before model inference. The full 841-row training/validation pool was checked for exact ID/text, normalized text, source-row, lexical, and generated-parameter overlap.

## Remote use

```bash
cd /gpfs/home/zhaobindq/linyx/fine_tuning_pilot_v0_evaluation_upload
source /gpfs/home/zhaobindq/linyx/wrf_ai_env/bin/activate
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES=0

ARGS="--base-model-path /gpfs/home/zhaobindq/linyx/Qwen2.5-1.5B-Instruct --adapter-path /gpfs/home/zhaobindq/linyx/fine_tuning_pilot_v0_upload/outputs/pilot_v0_20260817T025613Z_seed42"
bash run_preflight.sh $ARGS
bash run_general_eval.sh $ARGS
bash run_campus_eval.sh $ARGS
python scripts/build_general_comparison.py
python scripts/compare_results.py
python scripts/validate_outputs.py
python scripts/build_final_report.py
```

For a resumed run, append `--resume` to the relevant evaluator command. General uses a user-only message and never receives the Campus RAG system prompt/evidence. The runner uses only PyTorch, Transformers, and PEFT: no Trainer, Accelerate, DeepSpeed, bitsandbytes, CUDA_HOME, or internet dependency.

`integrity/SHA256SUMS.txt` covers immutable inputs and package code; generated `results/` are deliberately excluded.
