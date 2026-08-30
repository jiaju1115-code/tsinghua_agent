from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "trusted_campus_agent_v2" / "local_model.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def download(target: Path) -> Path:
    model = json.loads(CONFIG.read_text(encoding="utf-8"))["recommended_upgrade"]
    expected_size = int(model["size_bytes"])
    expected_hash = model["sha256"]
    if target.is_file() and target.stat().st_size == expected_size and digest(target) == expected_hash:
        print(f"Verified model already exists: {target}")
        return target
    part = target.with_suffix(target.suffix + ".part")
    offset = part.stat().st_size if part.is_file() else 0
    url = f"https://huggingface.co/{model['name']}/resolve/main/{model['filename']}?download=true"
    request = urllib.request.Request(url, headers={"User-Agent": "TsingAsk-V2/2.0"})
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading official {model['name']} to {target} (resume={offset} bytes)")
    with urllib.request.urlopen(request, timeout=120) as response:
        if offset and response.status != 206:
            offset = 0
        mode = "ab" if offset else "wb"
        with part.open(mode) as handle:
            while True:
                block = response.read(4 * 1024 * 1024)
                if not block:
                    break
                handle.write(block)
                done = handle.tell()
                print(f"\r{done / 1024 / 1024:.1f} / {expected_size / 1024 / 1024:.1f} MiB", end="", flush=True)
    print()
    if part.stat().st_size != expected_size:
        raise RuntimeError(f"model size mismatch: {part.stat().st_size} != {expected_size}")
    actual = digest(part)
    if actual != expected_hash:
        raise RuntimeError(f"model SHA256 mismatch: {actual}")
    part.replace(target)
    print(f"Verified SHA256: {actual}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))["recommended_upgrade"]
    target = (args.target or ROOT / "models" / config["filename"]).resolve()
    try:
        download(target)
    except Exception as exc:
        print(f"Download failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
