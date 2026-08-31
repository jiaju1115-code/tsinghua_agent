from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
import sys


LLAMA_VERSION = "0.3.35"
LLAMA_WHEEL_ROOT = "https://abetlen.github.io/llama-cpp-python/whl"


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, env=env)


def nvidia_cuda_version() -> tuple[float | None, str]:
    try:
        output = subprocess.run(
            ["nvidia-smi"], check=True, capture_output=True, text=True, errors="replace"
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None, ""
    matched = re.search(r"CUDA Version:\s*(\d+\.\d+)", output)
    return (float(matched.group(1)) if matched else 12.1), output


def choose_backend(requested: str) -> tuple[str, float | None]:
    requested = os.getenv("TSINGASK_GPU_BACKEND", requested).strip().lower()
    if requested != "auto":
        return requested, nvidia_cuda_version()[0]
    if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        return "metal", None
    cuda, _ = nvidia_cuda_version()
    if cuda is None:
        return "cpu", None
    if cuda >= 12.5:
        return "cu125", cuda
    if cuda >= 12.4:
        return "cu124", cuda
    if cuda >= 12.3:
        return "cu123", cuda
    if cuda >= 12.2:
        return "cu122", cuda
    if cuda >= 12.1:
        return "cu121", cuda
    return "cu118", cuda


def install_torch(backend: str, cuda: float | None) -> None:
    command = [sys.executable, "-m", "pip", "install", "--upgrade", "torch>=2.2,<3"]
    if backend.startswith("cu"):
        torch_channel = "cu126" if (cuda or 0) >= 12.6 else "cu124" if (cuda or 0) >= 12.4 else "cu118"
        command += ["--index-url", f"https://download.pytorch.org/whl/{torch_channel}"]
    run(command)


def install_llama(backend: str) -> None:
    package = f"llama-cpp-python=={LLAMA_VERSION}"
    base = [sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "--no-deps"]
    if backend in {"cpu", "metal", "cu118", "cu121", "cu122", "cu123", "cu124", "cu125"}:
        run(base + ["--only-binary=:all:", package, "--extra-index-url", f"{LLAMA_WHEEL_ROOT}/{backend}"])
        return
    if backend not in {"vulkan", "cuda-source", "hipblas"}:
        raise SystemExit(f"Unsupported accelerator backend: {backend}")
    flags = {
        "vulkan": "-DGGML_VULKAN=on",
        "cuda-source": "-DGGML_CUDA=on",
        "hipblas": "-DGGML_HIPBLAS=on",
    }
    env = dict(os.environ, CMAKE_ARGS=flags[backend], FORCE_CMAKE="1")
    run(base + ["--no-cache-dir", package], env=env)


def verify(expected: str) -> None:
    code = (
        "import json,torch,llama_cpp; "
        "print(json.dumps({'torch_cuda':torch.cuda.is_available(),"
        "'torch_devices':torch.cuda.device_count(),"
        "'llama_gpu_offload':bool(llama_cpp.llama_supports_gpu_offload())},ensure_ascii=False))"
    )
    run([sys.executable, "-c", code])
    print(f"TsingAsk accelerator backend installed: {expected}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install TsingAsk PyTorch and llama.cpp acceleration backends")
    parser.add_argument(
        "--backend", default="auto",
        choices=["auto", "cpu", "cu118", "cu121", "cu122", "cu123", "cu124", "cu125", "metal", "vulkan", "cuda-source", "hipblas"],
    )
    args = parser.parse_args()
    backend, cuda = choose_backend(args.backend)
    print(f"Detected/selected backend: {backend}; NVIDIA driver CUDA capability: {cuda or 'n/a'}")
    try:
        install_torch(backend, cuda)
        install_llama(backend)
    except subprocess.CalledProcessError:
        if args.backend != "auto" or backend == "cpu":
            raise
        print("GPU backend installation failed; falling back to the portable CPU wheels.", file=sys.stderr)
        backend = "cpu"
        install_torch(backend, None)
        install_llama(backend)
    verify(backend)


if __name__ == "__main__":
    main()
