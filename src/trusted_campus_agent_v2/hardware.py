from __future__ import annotations

import os
from typing import Any


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def force_cpu() -> bool:
    return _enabled("TSINGASK_FORCE_CPU")


def torch_acceleration() -> dict[str, Any]:
    info: dict[str, Any] = {"device": "cpu", "available": False, "device_count": 0}
    try:
        import torch

        if force_cpu():
            info["reason"] = "TSINGASK_FORCE_CPU"
        elif torch.cuda.is_available():
            info.update({
                "device": "cuda",
                "available": True,
                "device_count": torch.cuda.device_count(),
                "devices": [torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())],
                "torch_cuda": torch.version.cuda,
            })
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            info.update({"device": "mps", "available": True, "device_count": 1, "devices": ["Apple Metal"]})
        else:
            info["reason"] = "no accelerator-enabled PyTorch device detected"
    except Exception as exc:
        info["reason"] = f"{type(exc).__name__}: {exc}"
    return info


def place_dense_encoder(dense: Any) -> dict[str, Any]:
    """Move the frozen encoder only; its weights and retrieval contract stay unchanged."""
    info = torch_acceleration()
    target = info["device"] if info["available"] else "cpu"
    model = getattr(dense, "model", None)
    if model is not None and hasattr(model, "to"):
        model.to(target)
        setattr(dense, "_tsingask_device", target)
    info["component"] = "dense_encoder"
    return info


def move_batch_to_dense_device(dense: Any, batch: Any) -> Any:
    device = getattr(dense, "_tsingask_device", "cpu")
    if hasattr(batch, "to"):
        return batch.to(device)
    if isinstance(batch, dict):
        return {key: value.to(device) if hasattr(value, "to") else value for key, value in batch.items()}
    return batch


def llama_acceleration(llama_cpp: Any) -> dict[str, Any]:
    requested = os.getenv("TSINGASK_GPU_LAYERS", "auto").strip().lower() or "auto"
    supports = False
    try:
        supports = bool(llama_cpp.llama_supports_gpu_offload())
    except Exception:
        pass
    if force_cpu():
        layers = 0
        reason = "TSINGASK_FORCE_CPU"
    elif requested == "auto":
        layers = -1 if supports else 0
        reason = "all layers" if supports else "installed llama_cpp wheel has no GPU backend"
    else:
        try:
            layers = int(requested)
        except ValueError as exc:
            raise RuntimeError("TSINGASK_GPU_LAYERS must be auto, -1, 0, or a positive integer") from exc
        if layers != 0 and not supports:
            raise RuntimeError("GPU layers were requested, but installed llama_cpp has no GPU backend")
        reason = "explicit configuration"
    return {
        "component": "local_llm",
        "backend": os.getenv("TSINGASK_GPU_BACKEND", "auto"),
        "gpu_backend_available": supports,
        "requested_gpu_layers": requested,
        "n_gpu_layers": layers,
        "mode": "gpu" if layers != 0 else "cpu",
        "reason": reason,
    }
