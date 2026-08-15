from __future__ import annotations

import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromName("evaluation.evidence_sufficiency.v1.tests.test_runtime")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    payload = {
        "artifact": "Evidence Sufficiency Runtime V1 unit test result",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_module": "evaluation.evidence_sufficiency.v1.tests.test_runtime",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "successful": result.wasSuccessful(),
        "required_coverage": [
            "SUFFICIENT",
            "PARTIAL",
            "INSUFFICIENT",
            "missing requested attribute",
            "optional-only missing",
            "empty evidence",
            "irrelevant evidence",
            "conflict evidence",
            "malformed retrieval result",
            "frozen version mismatch",
            "deterministic repeatability",
        ],
        "runner_output": stream.getvalue().splitlines(),
    }
    target = ROOT / "evaluation" / "evidence_sufficiency" / "v1" / "tests" / "unit_test_results.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
