from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from typing import Any


LLAMA_VERSION = "0.3.35"
LLAMA_WHEEL_ROOT = "https://abetlen.github.io/llama-cpp-python/whl"
CUDA_BACKENDS = {"cu118", "cu121", "cu122", "cu123", "cu124", "cu125", "cuda-source"}
LLAMA_GPU_BACKENDS = CUDA_BACKENDS | {"metal", "vulkan", "hipblas"}


class AcceleratorVerificationError(RuntimeError):
    """The packages installed, but the requested accelerator is unusable."""


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
    if cuda >= 12.4:
        return "cu124", cuda
    # Auto mode deliberately uses a matching PyTorch/llama.cpp pair. NVIDIA
    # drivers are backward compatible, so CUDA 11.8 is safer than mixing a
    # cu121/122/123 llama wheel with a different PyTorch CUDA runtime.
    return "cu118", cuda


def install_torch(backend: str, cuda: float | None, *, force: bool = False) -> None:
    command = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if force:
        command.append("--force-reinstall")
    command.append("torch>=2.2,<3")
    if backend.startswith("cu") or backend == "cuda-source":
        torch_channel = {
            "cu118": "cu118",
            "cu121": "cu121",
            "cu122": "cu121",
            "cu123": "cu121",
            "cu124": "cu124",
            "cu125": "cu124",
        }.get(backend, "cu124" if (cuda or 0) >= 12.4 else "cu118")
        command += ["--index-url", f"https://download.pytorch.org/whl/{torch_channel}"]
    elif backend == "cpu":
        # An explicit CPU index plus force=True is required during fallback;
        # otherwise pip can keep the already-installed CUDA build because it
        # still satisfies the broad torch version constraint.
        command += ["--index-url", "https://download.pytorch.org/whl/cpu"]
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


def probe_runtime() -> dict[str, Any]:
    """Import each backend independently and preserve the real DLL error."""
    code = r'''
import json
import platform
import sys

report = {
    "python": platform.python_version(),
    "executable": sys.executable,
    "errors": [],
    "torch_cuda": False,
    "torch_mps": False,
    "torch_devices": 0,
    "llama_gpu_offload": False,
}
try:
    import torch
    report["torch_version"] = torch.__version__
    report["torch_cuda_version"] = torch.version.cuda
    report["torch_cuda"] = bool(torch.cuda.is_available())
    report["torch_devices"] = int(torch.cuda.device_count())
    report["torch_mps"] = bool(
        getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
    )
except BaseException as exc:
    report["errors"].append({
        "component": "torch",
        "type": type(exc).__name__,
        "message": str(exc),
    })
try:
    import llama_cpp
    report["llama_version"] = getattr(llama_cpp, "__version__", "unknown")
    report["llama_gpu_offload"] = bool(llama_cpp.llama_supports_gpu_offload())
except BaseException as exc:
    report["errors"].append({
        "component": "llama_cpp",
        "type": type(exc).__name__,
        "message": str(exc),
    })
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(1 if report["errors"] else 0)
'''
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, errors="replace"
    )
    if completed.stderr.strip():
        print(completed.stderr.rstrip(), file=sys.stderr)
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    payload = next((line for line in reversed(lines) if line.startswith("{")), "")
    if not payload:
        raise AcceleratorVerificationError(
            f"accelerator probe exited with code {completed.returncode} without a JSON report"
        )
    try:
        report = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AcceleratorVerificationError(f"invalid accelerator probe report: {payload}") from exc
    print("Accelerator probe:", json.dumps(report, ensure_ascii=False, indent=2))
    if completed.returncode != 0 or report.get("errors"):
        details = "; ".join(
            f"{item.get('component')}: {item.get('type')}: {item.get('message')}"
            for item in report.get("errors", [])
        )
        raise AcceleratorVerificationError(details or f"probe exit code {completed.returncode}")
    return report


def verify(expected: str) -> dict[str, Any]:
    report = probe_runtime()
    problems: list[str] = []
    if expected in CUDA_BACKENDS:
        if not report.get("torch_cuda") or int(report.get("torch_devices", 0)) < 1:
            problems.append("PyTorch cannot see a CUDA device")
    elif expected == "metal" and not report.get("torch_mps"):
        problems.append("PyTorch cannot see the Apple Metal device")
    if expected in LLAMA_GPU_BACKENDS and not report.get("llama_gpu_offload"):
        problems.append("llama_cpp reports that GPU offload is unavailable")
    if problems:
        raise AcceleratorVerificationError("; ".join(problems))
    print(f"TsingAsk accelerator backend verified: {expected}")
    return report


def install_requested_backend(requested: str) -> tuple[str, dict[str, Any]]:
    requested = os.getenv("TSINGASK_GPU_BACKEND", requested).strip().lower()
    backend, cuda = choose_backend(requested)
    print(f"Detected/selected backend: {backend}; NVIDIA driver CUDA capability: {cuda or 'n/a'}")
    if sys.version_info >= (3, 13):
        print(
            "Python 3.13 detected. Current wheels can support it, but TsingAsk is primarily "
            "validated on Python 3.11/3.12; full import diagnostics will run after installation.",
            file=sys.stderr,
        )
    try:
        install_torch(backend, cuda)
        install_llama(backend)
        return backend, verify(backend)
    except (subprocess.CalledProcessError, AcceleratorVerificationError) as exc:
        if requested != "auto" or backend == "cpu":
            raise
        print(
            f"GPU backend {backend} failed installation or verification: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        print("Falling back to freshly reinstalled portable CPU wheels.", file=sys.stderr)
        install_torch("cpu", None, force=True)
        install_llama("cpu")
        return "cpu", verify("cpu")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install TsingAsk PyTorch and llama.cpp acceleration backends")
    parser.add_argument(
        "--backend", default="auto",
        choices=["auto", "cpu", "cu118", "cu121", "cu122", "cu123", "cu124", "cu125", "metal", "vulkan", "cuda-source", "hipblas"],
    )
    args = parser.parse_args()
    backend, _ = install_requested_backend(args.backend)
    print(f"TsingAsk accelerator setup complete: {backend}")


if __name__ == "__main__":
    main()
