import json
from pathlib import Path
from datasets import load_dataset
from huggingface_hub import hf_hub_url

dataset = "nvidia/Nemotron-Instruction-Following-Chat-v1"
revision = "83dcd3aded0d289b0bbc018d3f9af4c5dd4005df"
url = hf_hub_url(dataset, "data/structured_outputs.jsonl", repo_type="dataset", revision=revision)
try:
    stream = load_dataset("json", data_files={"train": url}, split="train", streaming=True)
    result = {"ok": True, "uuid": next(iter(stream))["uuid"]}
except Exception as exc:
    result = {"ok": False, "type": type(exc).__name__, "message": str(exc)}
Path("evaluation/fine_tuning_pilot_v1_revision_recovery_v2_1_loader_preflight.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(result)
