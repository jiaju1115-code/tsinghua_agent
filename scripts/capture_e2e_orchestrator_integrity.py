from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "evaluation"
    / "e2e_orchestrator"
    / "runtime_v1"
    / "audit"
    / "orchestrator_pre_integrity.json"
)

FREEZES = {
    "knowledge_base_v1": {
        "path": "data/03_knowledge_base/v1/audit/knowledge_base_v1_freeze.json",
        "status_field": "status",
        "expected_status": "KNOWLEDGE_BASE_V1_FROZEN",
    },
    "rag_retrieval_v1": {
        "path": "data/03_knowledge_base/v1/audit/rag_retrieval_v1_freeze.json",
        "status_field": "status",
        "expected_status": "RAG_RETRIEVAL_V1_FROZEN",
    },
    "evidence_sufficiency_v1": {
        "path": "evaluation/evidence_sufficiency/v1/audit/evidence_sufficiency_v1_freeze.json",
        "status_field": "status",
        "expected_status": "EVIDENCE_SUFFICIENCY_V1_FROZEN",
        "artifact_field": "artifact_manifest",
    },
    "citation_support_v1": {
        "path": "evaluation/citation_support/v1/audit/citation_support_v1_freeze.json",
        "status_field": "status",
        "expected_status": "CITATION_SUPPORT_V1_FROZEN",
        "artifact_field": "artifact_sha256",
    },
    "answer_generation_v1": {
        "path": "evaluation/answer_generation/runtime_v1/audit/answer_generation_v1_freeze.json",
        "status_field": "status",
        "expected_status": "ANSWER_GENERATION_V1_FROZEN",
        "artifact_field": "artifact_sha256",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_record(relative: str, expected: str | None = None) -> dict[str, Any]:
    path = ROOT / relative
    actual = sha256(path) if path.is_file() else None
    return {
        "path": relative,
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": actual,
        "expected_sha256": expected,
        "hash_matches": actual == expected if expected is not None else None,
    }


def declared_artifacts(manifest: dict[str, Any], field: str | None) -> list[dict[str, Any]]:
    if not field:
        return []
    raw = manifest.get(field, {})
    rows = []
    for relative, value in sorted(raw.items()):
        expected = value.get("sha256") if isinstance(value, dict) else value
        rows.append(file_record(relative, expected))
    return rows


def canonical_kb_checks(kb: dict[str, Any], rag: dict[str, Any]) -> list[dict[str, Any]]:
    mapping = {
        "data/03_knowledge_base/v1/chunks/chunks.jsonl": kb["chunks_sha256"],
        "data/03_knowledge_base/v1/config/chunking_v1.json": kb["chunking_config_sha256"],
        "data/03_knowledge_base/v1/config/retriever_v1.json": kb["retriever_config_sha256"],
        "data/03_knowledge_base/v1/index/document_embeddings.npy": kb["index_sha256"],
        "data/03_knowledge_base/v1/index/index_manifest.json": kb["index_manifest_sha256"],
        "data/03_knowledge_base/v1/index/model/model.safetensors": kb["model_weights_sha256"],
        "data/03_knowledge_base/v1/manifests/chunk_manifest.jsonl": kb["chunk_manifest_sha256"],
        "data/03_knowledge_base/v1/manifests/source_manifest.jsonl": kb["source_manifest_sha256"],
        "data/03_knowledge_base/v1/provenance/source_provenance.jsonl": kb["source_provenance_sha256"],
        "scripts/build_knowledge_base_v1.py": kb["relevant_code_hashes"]["builder"],
        "src/retrieval_v1/adapter.py": kb["relevant_code_hashes"]["runtime_adapter"],
    }
    config = read_json(ROOT / "data/03_knowledge_base/v1/config/retriever_v1.json")
    for relative, digest in config.get("artifact_sha256", {}).items():
        mapping[f"data/03_knowledge_base/v1/{relative}"] = digest
    assert rag["retriever_config_sha256"] == kb["retriever_config_sha256"]
    return [file_record(relative, expected) for relative, expected in sorted(mapping.items())]


def capture() -> dict[str, Any]:
    components: dict[str, Any] = {}
    all_declared: dict[str, dict[str, Any]] = {}
    loaded: dict[str, dict[str, Any]] = {}
    for name, specification in FREEZES.items():
        relative = specification["path"]
        path = ROOT / relative
        manifest = read_json(path)
        loaded[name] = manifest
        sidecar_path = Path(str(path) + ".sha256")
        sidecar_expected = sidecar_path.read_text(encoding="ascii").strip() if sidecar_path.is_file() else None
        manifest_hash = sha256(path)
        rows = declared_artifacts(manifest, specification.get("artifact_field"))
        for row in rows:
            all_declared[row["path"]] = row
        components[name] = {
            "freeze_manifest": relative,
            "freeze_manifest_sha256": manifest_hash,
            "sidecar_path": str(Path(relative + ".sha256")).replace("\\", "/"),
            "sidecar_expected_sha256": sidecar_expected,
            "sidecar_matches": sidecar_expected == manifest_hash,
            "declared_status": manifest.get(specification["status_field"]),
            "expected_status": specification["expected_status"],
            "status_matches": manifest.get(specification["status_field"]) == specification["expected_status"],
            "declared_artifact_count": len(rows),
            "declared_artifacts_valid": all(row["exists"] and row["hash_matches"] for row in rows),
        }
    kb_rows = canonical_kb_checks(loaded["knowledge_base_v1"], loaded["rag_retrieval_v1"])
    for row in kb_rows:
        all_declared[row["path"]] = row
    components["knowledge_base_v1"]["canonical_hash_checks"] = len(kb_rows)
    components["knowledge_base_v1"]["canonical_hashes_valid"] = all(
        row["exists"] and row["hash_matches"] for row in kb_rows
    )
    inventory = [all_declared[key] for key in sorted(all_declared)]
    inventory_hash = hashlib.sha256(
        json.dumps(
            [{"path": row["path"], "sha256": row["sha256"]} for row in inventory],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    valid = all(
        component["sidecar_matches"]
        and component["status_matches"]
        and component.get("declared_artifacts_valid", True)
        and component.get("canonical_hashes_valid", True)
        for component in components.values()
    )
    return {
        "artifact": "Unified E2E Orchestrator V1 frozen-upstream integrity snapshot",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope_definition": "Canonical freeze manifests and every artifact hash explicitly declared by them; transient __pycache__/*.pyc files are outside formal frozen scope.",
        "components": components,
        "formal_artifact_count": len(inventory),
        "formal_inventory_sha256": inventory_hash,
        "formal_artifacts": inventory,
        "all_frozen_inputs_valid": valid,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    payload = capture()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "valid": payload["all_frozen_inputs_valid"], "inventory_sha256": payload["formal_inventory_sha256"]}))
    return 0 if payload["all_frozen_inputs_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
