from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    train, validation = load("train.jsonl"), load("validation.jsonl")
    assert train and validation
    train_sources = {row["metadata"]["source_id"] for row in train}
    validation_sources = {row["metadata"]["source_id"] for row in validation}
    assert not train_sources & validation_sources
    ids = set()
    for row in train + validation:
        assert row["id"] not in ids
        ids.add(row["id"])
        user = json.loads(row["messages"][1]["content"])
        answer = row["messages"][2]["content"]
        markers = set(re.findall(r"\[(F\d+)\]", answer))
        assert markers and markers <= set(user["facts"])
        answer_numbers = set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"\[F\d+\]", "", answer)))
        evidence_numbers = set(re.findall(r"\d+(?:\.\d+)?", " ".join(user["facts"].values())))
        assert not answer_numbers - evidence_numbers
    print(json.dumps({"status": "PASS", "train": len(train), "validation": len(validation), "source_overlap": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
