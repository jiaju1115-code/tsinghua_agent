"""Freeze the adjudicated evidence-sufficiency holdout before candidate work."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "generation_citation_eval_v0" / "results" / "independent_review_packet_adjudicated.xlsx"
SALT = "evidence_sufficiency_v0_1"


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    ws = wb["Review Packet"]
    rows = list(ws.iter_rows(values_only=True))
    headers = list(rows[0])
    records = [dict(zip(headers, row)) for row in rows[1:] if row[1]]
    for record in records:
        record["label"] = record.pop("evidence_reassessment")
        record["selection_hash"] = hashlib.sha256(
            f"{record['track']}||{record['sample_id']}||{record['query']}||{SALT}".encode("utf-8")
        ).hexdigest()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["label"]].append(record)
    # Stratified deterministic split: reserve one sample per observed label, then fill to five.
    holdout = []
    for label in sorted(grouped):
        holdout.append(sorted(grouped[label], key=lambda x: x["selection_hash"])[0])
    remaining = sorted((r for r in records if r not in holdout), key=lambda x: x["selection_hash"])
    holdout.extend(remaining[: max(0, 5 - len(holdout))])
    holdout_ids = {r["sample_id"] for r in holdout}
    development = [r for r in records if r["sample_id"] not in holdout_ids]
    for record in records:
        record["frozen_source_sha256"] = sha256_bytes(SOURCE)
    payload = {
        "schema_version": "evidence_sufficiency_v0_1_holdout_freeze_v1",
        "selection_method": "Stratified by adjudicated label; SHA256(track || sample_id || query || 'evidence_sufficiency_v0_1'), one per label then lowest remaining hashes to n=5.",
        "canonical_sha256": sha256_bytes(SOURCE),
        "source": str(SOURCE),
        "source_sha256": sha256_bytes(SOURCE),
        "holdout_sample_ids": sorted(holdout_ids),
        "holdout_label_distribution": {k: sum(r["label"] == k for r in holdout) for k in sorted(grouped)},
        "development_label_distribution": {k: sum(r["label"] == k for r in development) for k in sorted(grouped)},
        "records": [{k: v for k, v in r.items() if k not in {"frozen_evidence"}} for r in sorted(records, key=lambda x: x["sample_id"])],
    }
    (ROOT / "evaluation").mkdir(parents=True, exist_ok=True)
    (ROOT / "audit").mkdir(parents=True, exist_ok=True)
    (ROOT / "development").mkdir(parents=True, exist_ok=True)
    (ROOT / "evaluation" / "adjudicated_holdout.json").write_text(json.dumps(holdout, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "development" / "adjudicated_development_set.json").write_text(json.dumps(development, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "audit" / "holdout_freeze.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
