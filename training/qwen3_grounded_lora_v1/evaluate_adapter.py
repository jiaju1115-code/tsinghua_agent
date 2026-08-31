from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a base Qwen3 model or a trained PEFT adapter")
    parser.add_argument("--model", default="Qwen/Qwen3-4B")
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "evaluation.json")
    args = parser.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", torch_dtype=torch.bfloat16, trust_remote_code=False)
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    rows = [json.loads(line) for line in (ROOT / "data" / "validation.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    results = []
    for row in rows:
        prompt = tokenizer.apply_chat_template(row["messages"][:2], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=420, do_sample=False, pad_token_id=tokenizer.eos_token_id)
        answer = tokenizer.decode(output[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        evidence = json.loads(row["messages"][1]["content"])
        markers = set(re.findall(r"\[(F\d+)\]", answer))
        valid_markers = bool(markers) and markers <= set(evidence["facts"])
        answer_numbers = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"\[F\d+\]", "", answer)))
        evidence_numbers = set(re.findall(r"\d+(?:\.\d+)?", " ".join(evidence["facts"].values())))
        numeric_grounded = not (answer_numbers - evidence_numbers)
        partial_clear = evidence["evidence_status"] != "PARTIAL" or any(word in answer for word in ("部分", "目前", "暂时", "尚不能", "还不能", "未能确认", "没有包含"))
        results.append({"id": row["id"], "answer": answer, "valid_markers": valid_markers, "numeric_grounded": numeric_grounded, "partial_clear": partial_clear})
    count = max(1, len(results))
    metrics = {
        "model": args.model,
        "adapter": str(args.adapter) if args.adapter else None,
        "count": len(results),
        "citation_format_rate": sum(r["valid_markers"] for r in results) / count,
        "numeric_grounding_rate": sum(r["numeric_grounded"] for r in results) / count,
        "partial_limitation_rate": sum(r["partial_clear"] for r in results) / count,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in metrics.items() if key != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
