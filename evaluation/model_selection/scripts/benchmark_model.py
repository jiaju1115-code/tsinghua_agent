from __future__ import annotations

import argparse
import gc
import json
import math
import os
import platform
import shutil
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import torch
import psutil
from transformers import AutoModelForCausalLM, AutoTokenizer
try:
    from transformers import AutoModelForMultimodalLM
except ImportError:
    AutoModelForMultimodalLM = None


ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = ROOT / "model_selection"
HELDOUT = MODEL_ROOT / "heldout"
OUT = MODEL_ROOT / "base_model_benchmark.jsonl"
PROMPTS = [
    "清华大学校园服务信息通常包括",
    "办理学生事务时，申请人首先应当",
    "图书馆借阅规则的主要作用是",
]


def rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def token_stats(tokenizer, text: str) -> dict:
    ids = tokenizer(text, add_special_tokens=False)["input_ids"]
    chinese_chars = sum("\u4e00" <= ch <= "\u9fff" for ch in text)
    return {
        "characters": len(text),
        "chinese_characters": chinese_chars,
        "tokens": len(ids),
        "tokens_per_character": round(len(ids) / max(1, len(text)), 6),
        "tokens_per_chinese_character": round(len(ids) / max(1, chinese_chars), 6),
    }


def mean_loss(model, tokenizer, text: str, max_length: int = 256, windows: int = 3) -> dict:
    ids = tokenizer(text, return_tensors="pt", add_special_tokens=False)["input_ids"][0]
    losses = []
    token_counts = []
    for start in range(0, min(ids.numel(), max_length * windows), max_length):
        chunk = ids[start : start + max_length].unsqueeze(0)
        if chunk.shape[1] < 8:
            continue
        with torch.inference_mode():
            loss = model(input_ids=chunk, labels=chunk).loss.detach().float().item()
        losses.append(loss)
        token_counts.append(int(chunk.shape[1]))
    if not losses:
        return {"loss": None, "perplexity": None, "tokens": 0, "windows": 0}
    weighted = sum(v * n for v, n in zip(losses, token_counts)) / sum(token_counts)
    return {
        "loss": round(weighted, 6),
        "perplexity": round(math.exp(min(weighted, 20)), 6),
        "tokens": sum(token_counts),
        "windows": len(losses),
    }


def lora_smoke(model, tokenizer, adapter_dir: Path) -> dict:
    from peft import LoraConfig, PeftModel, get_peft_model

    cfg = LoraConfig(r=2, lora_alpha=4, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM", target_modules="all-linear")
    peft_model = get_peft_model(model, cfg)
    batch = tokenizer("校园服务信息应当准确。", return_tensors="pt")
    peft_model.train()
    result = peft_model(**batch, labels=batch["input_ids"])
    result.loss.backward()
    trainable = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    peft_model.save_pretrained(adapter_dir)
    model = peft_model.unload()
    del peft_model
    gc.collect()
    reloaded = PeftModel.from_pretrained(model, adapter_dir, is_trainable=False)
    reloaded.eval()
    with torch.inference_mode():
        reload_loss = reloaded(**batch, labels=batch["input_ids"]).loss.detach().float().item()
    return {
        "status": "pass",
        "forward_loss": round(float(result.loss.detach().float().item()), 6),
        "backward": True,
        "trainable_parameters": trainable,
        "adapter_saved": True,
        "adapter_reloaded": True,
        "reload_loss": round(reload_loss, 6),
        "adapter_dir": str(adapter_dir),
    }


def append(record: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--mode", choices=["tokenizer", "full"], default="tokenizer")
    parser.add_argument("--revision")
    parser.add_argument("--trust-remote-code", action="store_true")
    args = parser.parse_args()
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": args.model,
        "revision": args.revision,
        "mode": args.mode,
        "host": {"os": platform.platform(), "python": platform.python_version(), "torch": torch.__version__, "device": "cpu"},
        "status": "started",
    }
    started = time.perf_counter()
    try:
        tok_start = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision, trust_remote_code=args.trust_remote_code)
        record["tokenizer_load_seconds"] = round(time.perf_counter() - tok_start, 4)
        general = (HELDOUT / "general_chinese_heldout.txt").read_text(encoding="utf-8")
        campus = (HELDOUT / "campus_heldout.txt").read_text(encoding="utf-8")
        record["tokenization"] = {
            "general_chinese": token_stats(tokenizer, general),
            "campus_chinese": token_stats(tokenizer, campus[:12000]),
        }
        if args.mode == "tokenizer":
            record["status"] = "tokenizer_pass"
            return

        load_start = time.perf_counter()
        auto_cls = AutoModelForMultimodalLM if args.model.startswith("Qwen/Qwen3.5-") and AutoModelForMultimodalLM else AutoModelForCausalLM
        model = auto_cls.from_pretrained(
            args.model,
            revision=args.revision,
            trust_remote_code=args.trust_remote_code,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        model.eval()
        record["model_load_seconds"] = round(time.perf_counter() - load_start, 4)
        record["parameter_count"] = sum(p.numel() for p in model.parameters())
        record["model_memory_footprint_bytes"] = int(model.get_memory_footprint())
        record["peak_process_rss_mb_after_load"] = round(rss_mb(), 2)
        record["loss_eval"] = {
            "general_chinese": mean_loss(model, tokenizer, general),
            "campus_heldout": mean_loss(model, tokenizer, campus),
        }
        completions = []
        for prompt in PROMPTS:
            inputs = tokenizer(prompt, return_tensors="pt")
            t0 = time.perf_counter()
            with torch.inference_mode():
                output = model.generate(**inputs, max_new_tokens=12, do_sample=False, pad_token_id=tokenizer.eos_token_id)
            elapsed = time.perf_counter() - t0
            new_tokens = int(output.shape[1] - inputs["input_ids"].shape[1])
            completions.append({
                "prompt": prompt,
                "completion": tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True),
                "new_tokens": new_tokens,
                "seconds": round(elapsed, 4),
                "tokens_per_second": round(new_tokens / max(elapsed, 1e-9), 4),
            })
        record["completions"] = completions
        try:
            safe_name = args.model.replace("/", "__")
            record["lora_smoke"] = lora_smoke(model, tokenizer, MODEL_ROOT / "smoke_adapters" / safe_name)
        except Exception as exc:
            record["lora_smoke"] = {"status": "fail", "error": repr(exc), "traceback": traceback.format_exc()}
        record["peak_process_rss_mb_end"] = round(rss_mb(), 2)
        record["status"] = "full_pass" if record["lora_smoke"].get("status") == "pass" else "full_partial"
    except Exception as exc:
        record["status"] = "fail"
        record["error"] = repr(exc)
        record["traceback"] = traceback.format_exc()
    finally:
        record["total_seconds"] = round(time.perf_counter() - started, 4)
        append(record)
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
