from __future__ import annotations

import hashlib
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REVISION = "2cfc18c9415c912f9d8155881c133215df768a70"
TOTAL_BYTES = 1_112_206_140
EXPECTED_SHA256 = "ced967c45fd1902eb92716c9ceeca7c95a936770ea9db611f5a841b926e33fbd"
URL = f"https://huggingface.co/BAAI/bge-reranker-base/resolve/{REVISION}/model.safetensors?download=true"
V1 = Path(__file__).resolve().parents[1]
MODEL_DIR = V1 / "indexes" / "reranker" / "model"
PARTS_DIR = V1 / "indexes" / "reranker" / "_small_parts"
ASSEMBLED = MODEL_DIR / "model.download.safetensors"
FINAL = MODEL_DIR / "model.safetensors"
CHUNK_BYTES = 8 * 1024 * 1024
WORKERS = 4
SMALL_FILES = ["config.json", "sentencepiece.bpe.model", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def spec(index: int) -> tuple[int, int, Path]:
    start = index * CHUNK_BYTES
    end = min(TOTAL_BYTES - 1, start + CHUNK_BYTES - 1)
    return start, end, PARTS_DIR / f"part-{index:04d}.bin"


def download(index: int) -> tuple[int, int]:
    start, end, path = spec(index)
    expected = end - start + 1
    if path.is_file() and path.stat().st_size == expected:
        return index, expected
    command = ["curl.exe", "--silent", "--show-error", "-L", "--fail", "--retry", "5",
               "--connect-timeout", "60", "--range", f"{start}-{end}", "--output", str(path), URL]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"curl failed for part {index} with code {completed.returncode}")
    actual = path.stat().st_size if path.is_file() else -1
    if actual != expected:
        raise RuntimeError(f"part {index} length mismatch: actual={actual}, expected={expected}")
    return index, actual


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    if V1 not in PARTS_DIR.parents:
        raise RuntimeError("Temporary path escaped RAG V1")
    for name in SMALL_FILES:
        target = MODEL_DIR / name
        if target.is_file() and target.stat().st_size > 0:
            continue
        small_url = f"https://huggingface.co/BAAI/bge-reranker-base/resolve/{REVISION}/{name}?download=true"
        completed = subprocess.run(["curl.exe", "--silent", "--show-error", "-L", "--fail", "--retry", "5",
                                    "--output", str(target), small_url], check=False)
        if completed.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError(f"failed to download required model file: {name}")
    if FINAL.is_file() and FINAL.stat().st_size == TOTAL_BYTES and sha256(FINAL) == EXPECTED_SHA256:
        print(f"RERANKER_DOWNLOAD_PASS bytes={TOTAL_BYTES} sha256={EXPECTED_SHA256} revision={REVISION}", flush=True)
        return
    count = (TOTAL_BYTES + CHUNK_BYTES - 1) // CHUNK_BYTES
    completed = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(download, i) for i in range(count)]
        for future in as_completed(futures):
            index, size = future.result()
            completed += size
            print(f"part={index:04d} completed_parts={completed // CHUNK_BYTES}/{count} bytes={completed}", flush=True)
    with ASSEMBLED.open("wb") as out:
        for i in range(count):
            _, _, path = spec(i)
            with path.open("rb") as inp:
                shutil.copyfileobj(inp, out, 1024 * 1024)
    if ASSEMBLED.stat().st_size != TOTAL_BYTES:
        raise RuntimeError(f"assembled length mismatch: {ASSEMBLED.stat().st_size}")
    actual_hash = sha256(ASSEMBLED)
    if actual_hash != EXPECTED_SHA256:
        raise RuntimeError(f"assembled SHA-256 mismatch: {actual_hash}")
    ASSEMBLED.replace(FINAL)
    shutil.rmtree(PARTS_DIR)
    print(f"RERANKER_DOWNLOAD_PASS bytes={TOTAL_BYTES} sha256={actual_hash} revision={REVISION}", flush=True)


if __name__ == "__main__":
    main()
