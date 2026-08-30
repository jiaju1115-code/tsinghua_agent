from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "05_trusted_campus_kb_v2_public" / "refresh_report.json"


def run(command: list[str]) -> dict[str, object]:
    started = datetime.now().astimezone()
    process = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
    result = {
        "command": command, "started_at": started.isoformat(),
        "finished_at": datetime.now().astimezone().isoformat(), "returncode": process.returncode,
        "stdout_tail": process.stdout[-4000:], "stderr_tail": process.stderr[-4000:],
    }
    if process.returncode:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally refresh public TsingAsk V2 candidates and atomically promote a clean serving bundle.")
    parser.add_argument("--max-pages", type=int, default=300)
    parser.add_argument("--max-files", type=int, default=80)
    parser.add_argument("--skip-crawl", action="store_true")
    parser.add_argument("--skip-attachments", action="store_true")
    parser.add_argument("--no-dense", action="store_true")
    args = parser.parse_args()
    steps = []
    try:
        if not args.skip_crawl:
            steps.append(run([sys.executable, "scripts/crawl_trusted_campus_v2_public.py", "--max-pages", str(args.max_pages), "--max-depth", "3", "--concurrency", "3", "--delay", "1.0", "--retry-failed"]))
        steps.append(run([sys.executable, "scripts/process_trusted_campus_v2_crawl.py", "--force"]))
        if not args.skip_attachments:
            steps.append(run([sys.executable, "scripts/download_trusted_campus_v2_attachments.py", "--max-files", str(args.max_files), "--force"]))
        command = [sys.executable, "scripts/build_trusted_campus_public_kb_v2.py"]
        if args.no_dense:
            command.append("--no-dense")
        steps.append(run(command))
        status = "SUCCESS"
    except Exception as exc:
        status = "FAILED"
        steps.append({"error": f"{type(exc).__name__}: {exc}"})
    payload = {"status": status, "finished_at": datetime.now().astimezone().isoformat(), "steps": steps, "serving_bundle_atomic": True}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((rendered + "\n").encode("utf-8", errors="replace"))
    if status != "SUCCESS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
