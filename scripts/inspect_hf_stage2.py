"""Small, read-only inventory for the frozen Pilot V1 Stage 2 source list."""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

SAMPLES = [
    ("nvidia/Nemotron-Instruction-Following-Chat-v1", "default", "structured_outputs"),
    ("allenai/tulu-3-sft-personas-instruction-following", "default", "train"),
    ("databricks/databricks-dolly-15k", "default", "train"),
    ("rajpurkar/squad", "plain_text", "train"),
    ("tasksource/ruletaker", "default", "train"),
    ("facebook/babi_qa", "en-10k-qa1", "train"),
    ("facebook/babi_qa", "en-10k-qa2", "train"),
    ("nvidia/OpenCodeInstruct", "train", "train"),
    ("google-research-datasets/mbpp", "full", "train"),
]


def get(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "pilot-v1-stage2-controlled-acquisition/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


for dataset, config, split in SAMPLES:
    query = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split, "offset": 0, "length": 1})
    try:
        payload = get(f"https://datasets-server.huggingface.co/rows?{query}")
        row = (payload.get("rows") or [{}])[0]
        print(json.dumps({"dataset": dataset, "config": config, "split": split, "features": payload.get("features"), "row": row}, ensure_ascii=False))
    except Exception as exc:  # inventory must report a controlled source failure
        print(json.dumps({"dataset": dataset, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
