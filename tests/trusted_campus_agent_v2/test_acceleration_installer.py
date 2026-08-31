from __future__ import annotations

import pytest

from scripts import install_tsingask_acceleration as installer


def test_auto_uses_matched_cuda_wheel_families(monkeypatch) -> None:
    monkeypatch.delenv("TSINGASK_GPU_BACKEND", raising=False)
    monkeypatch.setattr(installer, "nvidia_cuda_version", lambda: (13.0, "driver"))
    assert installer.choose_backend("auto") == ("cu124", 13.0)


def test_cu124_torch_install_does_not_switch_to_cu126(monkeypatch) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(installer, "run", lambda command, env=None: commands.append(command))
    installer.install_torch("cu124", 13.0)
    assert commands
    assert "https://download.pytorch.org/whl/cu124" in commands[0]
    assert all("cu126" not in part for part in commands[0])


def test_verify_cuda_requires_both_torch_device_and_llama_offload(monkeypatch) -> None:
    monkeypatch.setattr(
        installer,
        "probe_runtime",
        lambda: {
            "torch_cuda": True,
            "torch_devices": 1,
            "torch_mps": False,
            "llama_gpu_offload": False,
            "errors": [],
        },
    )
    with pytest.raises(installer.AcceleratorVerificationError, match="GPU offload"):
        installer.verify("cu124")


def test_auto_falls_back_when_gpu_verification_fails(monkeypatch) -> None:
    calls: list[tuple[str, str, bool]] = []
    reports = iter(
        [
            installer.AcceleratorVerificationError("llama CUDA DLL failed to load"),
            {"torch_cuda": False, "torch_devices": 0, "llama_gpu_offload": False},
        ]
    )
    monkeypatch.delenv("TSINGASK_GPU_BACKEND", raising=False)
    monkeypatch.setattr(installer, "choose_backend", lambda requested: ("cu124", 12.4))
    monkeypatch.setattr(
        installer,
        "install_torch",
        lambda backend, cuda, force=False: calls.append(("torch", backend, force)),
    )
    monkeypatch.setattr(
        installer,
        "install_llama",
        lambda backend: calls.append(("llama", backend, False)),
    )

    def fake_verify(backend: str):
        result = next(reports)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(installer, "verify", fake_verify)
    backend, report = installer.install_requested_backend("auto")

    assert backend == "cpu"
    assert report["torch_cuda"] is False
    assert calls == [
        ("torch", "cu124", False),
        ("llama", "cu124", False),
        ("torch", "cpu", True),
        ("llama", "cpu", False),
    ]


def test_explicit_gpu_backend_does_not_silently_fall_back(monkeypatch) -> None:
    monkeypatch.delenv("TSINGASK_GPU_BACKEND", raising=False)
    monkeypatch.setattr(installer, "choose_backend", lambda requested: ("cu124", 12.4))
    monkeypatch.setattr(installer, "install_torch", lambda *args, **kwargs: None)
    monkeypatch.setattr(installer, "install_llama", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        installer,
        "verify",
        lambda backend: (_ for _ in ()).throw(installer.AcceleratorVerificationError("no CUDA device")),
    )

    with pytest.raises(installer.AcceleratorVerificationError, match="no CUDA device"):
        installer.install_requested_backend("cu124")
