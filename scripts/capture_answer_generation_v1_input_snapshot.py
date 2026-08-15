"""Capture deterministic hashes for frozen Answer Generation V1 inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCOPES = [
    "data/03_knowledge_base/v1",
    "src/retrieval_v1/adapter.py",
    "src/evidence_sufficiency_v1",
    "evaluation/evidence_sufficiency/v1",
    "src/citation_support_v1",
    "evaluation/citation_support/v1",
    "reports/citation_support_v1_report.md",
    "experiments/evidence_sufficiency_v0_1",
    "experiments/evidence_sufficiency_v0_2",
    "experiments/evidence_sufficiency_v0_3",
    "experiments/evidence_sufficiency_v0_4",
    "evaluation/citation",
    "evaluation/answer_generation/v0",
    "evaluation/answer_generation/v1",
    "experiments/generation_citation_eval_v0",
    "evaluation/rag",
    "data/02_public_expansion/v2/human_check",
    "data/06_human_annotation",
    "experiments/router_v0_2",
    "evaluation/prompt_v3_2_blind_test_v1",
    "evaluation/e2e/v1/benchmark/exclusion_registry.jsonl",
]
MODEL_RELATIVE_TO_HOME = Path(
    ".cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct-GGUF/"
    "snapshots/91cad51170dc346986eccefdc2dd33a9da36ead9/"
    "qwen2.5-1.5b-instruct-q4_k_m.gguf"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory() -> dict[str, str]:
    files: set[Path] = set()

    def within_project(candidate: Path) -> bool:
        try:
            candidate.resolve().relative_to(ROOT.resolve())
            return True
        except ValueError:
            return False

    for item in SCOPES:
        path = ROOT / item
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            files.update(candidate for candidate in path.rglob("*") if candidate.is_file() and within_project(candidate))
    return {
        path.resolve().relative_to(ROOT.resolve()).as_posix(): sha256(path)
        for path in sorted(files, key=lambda value: value.resolve().relative_to(ROOT.resolve()).as_posix())
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    files = inventory()
    canonical = (json.dumps(files, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    model = Path.home() / MODEL_RELATIVE_TO_HOME
    model_record = {
        "path_relative_to_home": MODEL_RELATIVE_TO_HOME.as_posix(),
        "exists": model.is_file(),
        "size_bytes": model.stat().st_size if model.is_file() else None,
        "sha256": sha256(model) if model.is_file() else None,
        "revision": "91cad51170dc346986eccefdc2dd33a9da36ead9",
    }
    payload = {
        "artifact": "Answer Generation Runtime V1 frozen-input snapshot",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scopes": SCOPES,
        "file_count": len(files),
        "inventory_sha256": hashlib.sha256(canonical).hexdigest(),
        "external_generation_model": model_record,
        "files": files,
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.resolve().relative_to(ROOT.resolve()).as_posix(), "file_count": len(files), "inventory_sha256": payload["inventory_sha256"], "model_sha256": model_record["sha256"]}))


if __name__ == "__main__":
    main()
