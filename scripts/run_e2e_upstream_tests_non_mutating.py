from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "evaluation" / "e2e_orchestrator" / "runtime_v1" / "validation" / "upstream_non_mutating"


def load(name: str, relative: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {relative}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def invoke(name: str, relative: str, configure: Any) -> dict[str, Any]:
    module = load(name, relative)
    configure(module)
    stream = io.StringIO()
    exit_code = 0
    exception = None
    try:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            result = module.main()
        if isinstance(result, int):
            exit_code = result
    except SystemExit as exc:
        exit_code = int(exc.code or 0)
    except Exception as exc:  # pragma: no cover - surfaced in the audit output.
        exit_code = 1
        exception = f"{type(exc).__name__}: {exc}"
    return {
        "name": name,
        "source_script": relative,
        "exit_code": exit_code,
        "passed": exit_code == 0 and exception is None,
        "exception": exception,
        "stdout_tail": stream.getvalue().splitlines()[-12:],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    isolated_root = OUT_DIR / "isolated_output_root"
    rag_input = isolated_root / "evaluation" / "rag" / "v1" / "evaluation" / "eval_queries.jsonl"
    rag_input.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "evaluation" / "rag" / "v1" / "evaluation" / "eval_queries.jsonl", rag_input)
    (isolated_root / "data" / "03_knowledge_base" / "v1" / "audit").mkdir(parents=True, exist_ok=True)
    (isolated_root / "evaluation" / "evidence_sufficiency" / "v1" / "tests").mkdir(parents=True, exist_ok=True)

    cases = [
        invoke(
            "e2e_upstream_rag_regression",
            "scripts/run_rag_retrieval_v1_regression.py",
            lambda module: setattr(module, "ROOT", isolated_root),
        ),
        invoke(
            "e2e_upstream_evidence_unit",
            "scripts/run_evidence_sufficiency_v1_unit_tests.py",
            lambda module: setattr(module, "ROOT", isolated_root),
        ),
        invoke(
            "e2e_upstream_evidence_integration",
            "scripts/run_evidence_sufficiency_v1_integration.py",
            lambda module: setattr(module, "ROOT", isolated_root),
        ),
        invoke(
            "e2e_upstream_citation_unit",
            "scripts/run_citation_support_v1_unit_tests.py",
            lambda module: setattr(module, "OUTPUT", OUT_DIR / "citation_unit.json"),
        ),
        invoke(
            "e2e_upstream_citation_integration",
            "scripts/run_citation_support_v1_integration.py",
            lambda module: setattr(module, "OUT_DIR", OUT_DIR / "citation_integration"),
        ),
        invoke(
            "e2e_upstream_answer_unit",
            "scripts/run_answer_generation_v1_unit_tests.py",
            lambda module: setattr(module, "OUTPUT", OUT_DIR / "answer_unit.json"),
        ),
        invoke(
            "e2e_upstream_answer_integration",
            "scripts/run_answer_generation_v1_integration.py",
            lambda module: setattr(module, "OUT_DIR", OUT_DIR / "answer_integration"),
        ),
    ]
    payload = {
        "artifact": "Non-mutating execution of all existing frozen upstream test entry points",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Loaded each existing script unchanged and redirected only its output globals/root to the new orchestrator validation area.",
        "upstream_files_written": False,
        "test_entry_count": len(cases),
        "passed_count": sum(row["passed"] for row in cases),
        "failed_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "overall_status": "PASS" if all(row["passed"] for row in cases) else "FAIL",
    }
    target = OUT_DIR / "upstream_test_results.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["overall_status"], "passed": payload["passed_count"], "total": len(cases), "output": str(target)}, ensure_ascii=False))
    return 0 if payload["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
