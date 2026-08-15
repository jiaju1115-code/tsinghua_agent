"""Minimal, isolated candidate pipeline; it never writes to KB V1."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


def record(raw: dict, sequence: int, duplicate_of: str | None) -> dict:
    text = raw.get("text", "")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    url = raw.get("source_url", "")
    return {
        "record_id": f"CAND-{sequence:06d}",
        "raw": {"source_url": url, "title": raw.get("title", ""), "text": text},
        "source_validation": {"status": "pass" if urlparse(url).scheme in {"http", "https"} else "fail", "reason": "URL scheme check only; provenance needs review"},
        "dedup": {"status": "duplicate" if duplicate_of else "unique", "content_sha256": digest, "duplicate_of": duplicate_of},
        "quality_privacy": {"status": "manual_review", "flags": ["privacy_review_required", "quality_review_required"]},
        "category": {"status": "pending", "value": None},
        "chunk_candidate": {"status": "pending", "chunks": []},
        "kb_v2_candidate": {"status": "pending", "reason": "candidate only; not admitted to KB V1 or KB V2"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create isolated KB V2 candidate records from raw JSONL.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite output: {args.output}")
    raw_rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    records, first_record_for_digest = [], {}
    for i, row in enumerate(raw_rows, 1):
        digest = hashlib.sha256(row.get("text", "").encode("utf-8")).hexdigest()
        record_id = f"CAND-{i:06d}"
        records.append(record(row, i, first_record_for_digest.get(digest)))
        first_record_for_digest.setdefault(digest, record_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")
    print(json.dumps({"status": "CANDIDATE_ONLY", "records": len(raw_rows), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
