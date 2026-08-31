from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IGNORE_INDEX = -100
ROOT = Path(__file__).resolve().parent


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def feature(tokenizer: Any, messages: list[dict[str, str]], max_length: int) -> dict[str, list[int]]:
    prompt = messages[:-1]
    prefix = tokenizer.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False, enable_thinking=False)
    prefix_ids = tokenizer(prefix, add_special_tokens=False)["input_ids"]
    full_ids = tokenizer(full, add_special_tokens=False)["input_ids"]
    if full_ids[:len(prefix_ids)] != prefix_ids:
        raise ValueError("chat template prefix mismatch")
    answer_ids = full_ids[len(prefix_ids):]
    kept_answer = answer_ids[:max_length]
    kept_prompt = prefix_ids[-max(0, max_length - len(kept_answer)):]
    return {
        "input_ids": kept_prompt + kept_answer,
        "attention_mask": [1] * (len(kept_prompt) + len(kept_answer)),
        "labels": [IGNORE_INDEX] * len(kept_prompt) + kept_answer,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "adapter")
    parser.add_argument("--no-4bit", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    import torch
    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU is required for this controlled QLoRA training run")
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments

    tokenizer = AutoTokenizer.from_pretrained(cfg["base_model"], trust_remote_code=False)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    quantization = None
    if not args.no_4bit:
        quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"], device_map="auto", torch_dtype=torch.bfloat16,
        quantization_config=quantization, trust_remote_code=False,
    )
    if quantization:
        model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False
    lora = cfg["lora"]
    model = get_peft_model(model, LoraConfig(
        r=lora["r"], lora_alpha=lora["alpha"], lora_dropout=lora["dropout"],
        target_modules=lora["target_modules"], task_type="CAUSAL_LM",
    ))
    train = [feature(tokenizer, row["messages"], cfg["max_length"]) for row in load_rows(ROOT / "data" / "train.jsonl")]
    validation = [feature(tokenizer, row["messages"], cfg["max_length"]) for row in load_rows(ROOT / "data" / "validation.jsonl")]

    class Collator:
        def __call__(self, items: list[dict[str, list[int]]]) -> dict[str, torch.Tensor]:
            length = max(len(item["input_ids"]) for item in items)
            pad = tokenizer.pad_token_id
            return {
                "input_ids": torch.tensor([item["input_ids"] + [pad] * (length - len(item["input_ids"])) for item in items]),
                "attention_mask": torch.tensor([item["attention_mask"] + [0] * (length - len(item["attention_mask"])) for item in items]),
                "labels": torch.tensor([item["labels"] + [IGNORE_INDEX] * (length - len(item["labels"])) for item in items]),
            }

    training_args = TrainingArguments(
        output_dir=str(args.output), num_train_epochs=cfg["epochs"], learning_rate=cfg["learning_rate"],
        per_device_train_batch_size=cfg["batch_size"], per_device_eval_batch_size=1,
        gradient_accumulation_steps=cfg["gradient_accumulation_steps"], gradient_checkpointing=True,
        bf16=torch.cuda.is_bf16_supported(), fp16=not torch.cuda.is_bf16_supported(),
        eval_strategy="steps", save_strategy="steps", eval_steps=25, save_steps=25,
        logging_steps=5, save_total_limit=2, report_to="none", seed=cfg["seed"], remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train, eval_dataset=validation, data_collator=Collator())
    trainer.train()
    metrics = trainer.evaluate()
    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    (args.output / "validation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
