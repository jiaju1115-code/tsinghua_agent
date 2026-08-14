from __future__ import annotations

import hashlib
import json
from pathlib import Path

from safetensors import safe_open

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
WEIGHTS = DATA / "rag_v1" / "indexes" / "reranker" / "model" / "model.safetensors"


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parameter_count = 0
    tensor_count = 0
    with safe_open(WEIGHTS, framework="pt", device="cpu") as f:
        for key in f.keys():
            shape = f.get_slice(key).get_shape()
            size = 1
            for dim in shape:
                size *= dim
            parameter_count += size
            tensor_count += 1
    metrics = json.loads((ROOT / "results" / "citation_metrics_v2.json").read_text(encoding="utf-8"))
    sanity = json.loads((ROOT / "evaluation" / "verifier_sanity_results.json").read_text(encoding="utf-8"))
    record = {
        "model_name": "BAAI/bge-reranker-base",
        "revision": "2cfc18c9415c912f9d8155881c133215df768a70",
        "local_path": str(WEIGHTS.parent),
        "weight_sha256": sha(WEIGHTS),
        "weight_bytes": WEIGHTS.stat().st_size,
        "parameter_count": parameter_count,
        "parameter_scale": f"{parameter_count/1e6:.1f}M",
        "tensor_count": tensor_count,
        "framework": "PyTorch / Transformers AutoModelForSequenceClassification",
        "inference_device": "CPU",
        "training_performed": False,
        "downloaded_for_v2": False,
        "role": "pretrained cross-encoder relevance gate; not entailment",
        "sanity_status": sanity["status"],
        "selected_threshold": sanity["selected_threshold"],
        "claim_pair_latency_seconds": metrics["performance_seconds"]["verifier_claim_pairs"],
        "sanity_latency_seconds": metrics["performance_seconds"]["verifier_sanity"]
    }
    (ROOT / "results" / "verifier_model_record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    positive = [x["verifier_score"] for x in sanity["results"] if x["anchor_type"] == "POSITIVE"]
    negative = [x["verifier_score"] for x in sanity["results"] if x["anchor_type"] != "POSITIVE"]
    sensitivity = []
    for threshold in sanity["threshold_candidates"]:
        sensitivity.append({"threshold": threshold, "positive_pass": sum(x >= threshold for x in positive), "positive_total": len(positive), "hard_negative_pass": sum(x >= threshold for x in negative), "hard_negative_total": len(negative), "positive_pass_rate": sum(x >= threshold for x in positive)/len(positive) if positive else None, "hard_negative_false_positive_rate": sum(x >= threshold for x in negative)/len(negative) if negative else None})
    payload = {"selection_method": sanity["threshold_selection_method"], "selected_threshold": sanity["selected_threshold"], "sanity_status": sanity["status"], "sensitivity": sensitivity}
    (ROOT / "evaluation" / "verifier_threshold_sensitivity.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": record["model_name"], "parameters": parameter_count, "sha256": record["weight_sha256"], "thresholds": len(sensitivity)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
