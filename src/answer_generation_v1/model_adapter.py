from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Protocol

from .policy import ROOT, load_config, sha256
from .schema import MODEL_RESPONSE_JSON_SCHEMA


class GenerationAdapter(Protocol):
    def generate(self, messages: list[dict[str, str]], timeout_seconds: int) -> dict[str, Any]: ...


class LocalQwenGGUFAdapter:
    """Verified offline adapter for the frozen local GGUF artifact."""

    def __init__(self) -> None:
        self.config = load_config()
        model_cfg = self.config["model"]
        engine_cfg = self.config["engine"]
        self.model_path = Path.home() / model_cfg["file_relative_to_home"]
        if not self.model_path.is_file():
            raise RuntimeError("frozen local generation model is unavailable")
        if self.model_path.stat().st_size != model_cfg["file_size_bytes"] or sha256(self.model_path) != model_cfg["sha256"]:
            raise RuntimeError("frozen local generation model hash/size mismatch")
        vendor = ROOT / engine_cfg["vendor_path"]
        if str(vendor) not in sys.path:
            sys.path.insert(0, str(vendor))
        import llama_cpp  # type: ignore

        if llama_cpp.__version__ != engine_cfg["version"]:
            raise RuntimeError("llama-cpp-python version mismatch")
        decoding = self.config["decoding"]
        self._llm = llama_cpp.Llama(
            model_path=str(self.model_path),
            n_ctx=decoding["context_length"],
            n_threads=decoding["threads"],
            n_threads_batch=decoding["batch_threads"],
            n_batch=decoding["prompt_batch_size"],
            n_ubatch=decoding["micro_batch_size"],
            seed=decoding["seed"],
            n_gpu_layers=engine_cfg["gpu_layers"],
            verbose=False,
        )

    def generate(self, messages: list[dict[str, str]], timeout_seconds: int) -> dict[str, Any]:
        del timeout_seconds  # Native llama.cpp has no cancellable per-call timeout; caller enforces the deadline.
        decoding = self.config["decoding"]
        started = time.perf_counter()
        response = self._llm.create_chat_completion(
            messages=messages,
            temperature=decoding["temperature"],
            max_tokens=decoding["max_output_tokens"],
            seed=decoding["seed"],
            repeat_penalty=decoding["repeat_penalty"],
            response_format={"type": "json_object", "schema": MODEL_RESPONSE_JSON_SCHEMA},
        )
        content = response["choices"][0]["message"]["content"]
        return {
            "content": content,
            "usage": response.get("usage", {}),
            "finish_reason": response["choices"][0].get("finish_reason"),
            "generation_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "raw_output_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }


_DEFAULT_ADAPTER: LocalQwenGGUFAdapter | None = None


def default_adapter() -> LocalQwenGGUFAdapter:
    global _DEFAULT_ADAPTER
    if _DEFAULT_ADAPTER is None:
        _DEFAULT_ADAPTER = LocalQwenGGUFAdapter()
    return _DEFAULT_ADAPTER
