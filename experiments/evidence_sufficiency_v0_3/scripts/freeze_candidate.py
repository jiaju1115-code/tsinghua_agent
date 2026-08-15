"""Freeze the selected V0.3 candidate before any historical regression."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "candidates" / "candidate_config.json",
    ROOT / "candidates" / "candidate_model.joblib",
    ROOT / "candidates" / "candidate_v0_3-a.md",
    ROOT / "candidates" / "candidate_v0_3-b.md",
    ROOT / "candidates" / "candidate_v0_3-c.md",
    ROOT / "candidates" / "candidate_v0_3-d.md",
    ROOT / "candidates" / "evidence_sufficiency_v0_3_final.md",
    ROOT / "scripts" / "run_v0_3_cross_validation.py",
    ROOT / "results" / "candidate_selection.json",
    ROOT / "results" / "real_cross_validation_metrics.json",
    ROOT / "results" / "synthetic_cross_validation_metrics.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config = json.loads((ROOT / "candidates" / "candidate_config.json").read_text(encoding="utf-8"))
    payload = {
        "freeze_type": "EVIDENCE_SUFFICIENCY_V0_3_CANDIDATE_FREEZE",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_variant": config["variant"],
        "data_policy": "ALL_INPUTS_ARE_SEEN_CALIBRATION_DATA",
        "post_freeze_rule": "No classifier, feature, threshold, parser, or model mutation is permitted during regression.",
        "artifacts": {
            str(path.relative_to(ROOT)).replace("\\", "/"): {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in FILES
        },
    }
    out = ROOT / "audit" / "candidate_freeze.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"candidate": config["variant"], "frozen_artifacts": len(FILES)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
