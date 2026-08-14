from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V0 = ROOT / "rag_v0"
V1 = ROOT / "rag_v1"
CHUNKS_PATH = V0 / "chunks" / "chunks.jsonl"
V0_CHUNK_IDS = V0 / "vector_index" / "chunk_ids.json"
V0_VALIDATION = V0 / "knowledge_base_manifest" / "post_build_validation.json"
OUT = V1 / "audit" / "chunk_integrity_report.json"
REQUIRED = ["chunk_id", "source_id", "title", "category", "url", "original_file", "text", "chunk_index"]


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> None:
    rows = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    frozen_ids = json.loads(V0_CHUNK_IDS.read_text(encoding="utf-8-sig"))
    v0_validation = json.loads(V0_VALIDATION.read_text(encoding="utf-8-sig"))
    ids = [r.get("chunk_id") for r in rows]
    errors: list[dict] = []
    by_source: dict[str, list[int]] = defaultdict(list)

    for pos, row in enumerate(rows):
        for field in REQUIRED:
            if field not in row:
                errors.append({"row": pos, "chunk_id": row.get("chunk_id"), "error": "missing_field", "field": field})
        for field in ["chunk_id", "source_id", "title", "category", "url", "original_file", "text"]:
            if not nonempty(row.get(field)):
                errors.append({"row": pos, "chunk_id": row.get("chunk_id"), "error": "empty_field", "field": field})
        idx = row.get("chunk_index")
        if not isinstance(idx, int) or idx < 0:
            errors.append({"row": pos, "chunk_id": row.get("chunk_id"), "error": "invalid_chunk_index", "value": idx})
        elif nonempty(row.get("source_id")):
            by_source[row["source_id"]].append(idx)
        original = ROOT / str(row.get("original_file", ""))
        if not original.is_file():
            errors.append({"row": pos, "chunk_id": row.get("chunk_id"), "error": "original_file_not_traceable", "path": str(original)})
        expected_hash = row.get("chunk_sha256")
        if expected_hash and nonempty(row.get("text")):
            actual_hash = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
            if actual_hash != expected_hash:
                errors.append({"row": pos, "chunk_id": row.get("chunk_id"), "error": "chunk_text_hash_mismatch"})

    duplicates = [chunk_id for chunk_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        errors.append({"error": "duplicate_chunk_ids", "count": len(duplicates), "examples": duplicates[:20]})
    if ids != frozen_ids:
        errors.append({"error": "chunk_id_order_differs_from_v0_index", "v0_count": len(frozen_ids), "current_count": len(ids)})
    if len(rows) != 717:
        errors.append({"error": "chunk_count_not_717", "actual": len(rows)})
    if v0_validation.get("status") != "PASS":
        errors.append({"error": "v0_validation_not_pass", "v0_status": v0_validation.get("status")})

    for source_id, indexes in by_source.items():
        expected = list(range(len(indexes)))
        if sorted(indexes) != expected:
            errors.append({"error": "non_contiguous_chunk_index", "source_id": source_id, "actual": sorted(indexes), "expected": expected})

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not errors else "FAIL_STOP_INDEX_BUILD",
        "source": str(CHUNKS_PATH),
        "source_sha256": hashlib.sha256(CHUNKS_PATH.read_bytes()).hexdigest(),
        "v0_post_build_validation": v0_validation.get("status"),
        "checks": {
            "chunk_count_is_717": len(rows) == 717,
            "chunk_id_unique": len(set(ids)) == len(ids),
            "chunk_id_order_matches_v0": ids == frozen_ids,
            "source_id_present": all(nonempty(r.get("source_id")) for r in rows),
            "title_present": all(nonempty(r.get("title")) for r in rows),
            "category_present": all(nonempty(r.get("category")) for r in rows),
            "url_preserved": all(nonempty(r.get("url")) for r in rows),
            "original_file_traceable": all((ROOT / str(r.get("original_file", ""))).is_file() for r in rows),
            "text_nonempty": all(nonempty(r.get("text")) for r in rows),
            "chunk_index_valid": all(isinstance(r.get("chunk_index"), int) and r["chunk_index"] >= 0 for r in rows),
            "chunk_text_hash_valid": all(
                not r.get("chunk_sha256") or hashlib.sha256(r["text"].encode("utf-8")).hexdigest() == r["chunk_sha256"]
                for r in rows if nonempty(r.get("text"))
            ),
        },
        "counts": {
            "chunks": len(rows),
            "unique_chunk_ids": len(set(ids)),
            "unique_source_ids": len({r.get("source_id") for r in rows}),
            "urls_present": sum(nonempty(r.get("url")) for r in rows),
            "original_files_traceable": sum((ROOT / str(r.get("original_file", ""))).is_file() for r in rows),
        },
        "errors": errors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], **payload["counts"], "report": str(OUT)}, ensure_ascii=False))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
