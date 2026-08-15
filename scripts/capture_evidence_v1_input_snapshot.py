"""Capture a deterministic hash inventory of frozen Evidence V1 upstream inputs."""
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
    "experiments/evidence_sufficiency_v0_1",
    "experiments/evidence_sufficiency_v0_2",
    "experiments/evidence_sufficiency_v0_3",
    "experiments/evidence_sufficiency_v0_4",
    "data/02_public_expansion/v2/human_check",
    "data/06_human_annotation",
    "experiments/router_v0_2",
    "experiments/web_search_v0_followup",
    "evaluation/answer_generation",
    "evaluation/citation",
    "evaluation/e2e/v1/benchmark/exclusion_registry.jsonl",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def within_project(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def inventory() -> dict[str, str]:
    files: list[Path] = []
    for item in SCOPES:
        path = ROOT / item
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file() and within_project(candidate))
    unique = sorted(set(files), key=lambda path: path.resolve().relative_to(ROOT.resolve()).as_posix())
    return {path.resolve().relative_to(ROOT.resolve()).as_posix(): sha256(path) for path in unique}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = inventory()
    canonical = (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    artifact = {
        "artifact": "Evidence Sufficiency Runtime V1 upstream input snapshot",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scopes": SCOPES,
        "file_count": len(rows),
        "inventory_sha256": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
    }
    destination = args.output if args.output.is_absolute() else ROOT / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": destination.resolve().relative_to(ROOT.resolve()).as_posix(), "file_count": len(rows), "inventory_sha256": artifact["inventory_sha256"]}))


if __name__ == "__main__":
    main()
