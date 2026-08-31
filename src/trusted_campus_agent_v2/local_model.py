from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .answer_planner import GroundedAnswerPlannerV2
from .file_tools.llm_planner import FileToolCall, OpenAICompatibleFileToolPlanner, ToolCallingError
from .file_tools.models import FileRoute
from .file_tools.router import CampusToolRouter


ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG = ROOT / "configs" / "trusted_campus_agent_v2" / "local_model.json"
LEGACY_CONFIG = ROOT / "evaluation" / "answer_generation" / "runtime_v1" / "config" / "answer_generation_v1.json"
VENDOR_PATH = ROOT / "evaluation" / "answer_generation" / "v0" / "vendor"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class LocalModelIdentity:
    name: str
    path: Path
    sha256: str
    size_bytes: int
    backend: str = "llama_cpp"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "backend": self.backend,
            "local_only": True,
        }


def resolve_local_model() -> LocalModelIdentity:
    explicit = os.getenv("TSINGASK_MODEL_PATH", "").strip()
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"TSINGASK_MODEL_PATH does not exist: {path}")
        digest = _sha256(path)
        expected = os.getenv("TSINGASK_MODEL_SHA256", "").strip().lower()
        if expected and digest != expected:
            raise RuntimeError("TSINGASK_MODEL_PATH SHA256 mismatch")
        return LocalModelIdentity(
            name=os.getenv("TSINGASK_MODEL_NAME", path.stem).strip() or path.stem,
            path=path,
            sha256=digest,
            size_bytes=path.stat().st_size,
        )

    local = json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
    upgrade = local["recommended_upgrade"]
    preferred = ROOT / "models" / upgrade["filename"]
    if preferred.is_file():
        if preferred.stat().st_size != int(upgrade["size_bytes"]) or _sha256(preferred) != upgrade["sha256"]:
            raise RuntimeError("recommended Qwen3 model exists but failed size/SHA256 verification")
        return LocalModelIdentity(upgrade["name"], preferred, upgrade["sha256"], preferred.stat().st_size)

    legacy = json.loads(LEGACY_CONFIG.read_text(encoding="utf-8"))["model"]
    fallback = Path.home() / legacy["file_relative_to_home"]
    if not fallback.is_file():
        raise RuntimeError("no verified local generation model is available")
    if fallback.stat().st_size != int(legacy["file_size_bytes"]) or _sha256(fallback) != legacy["sha256"]:
        raise RuntimeError("legacy local generation model failed size/SHA256 verification")
    return LocalModelIdentity(legacy["name"], fallback, legacy["sha256"], fallback.stat().st_size)


class LocalQwenRuntime:
    """Lazy, process-local structured generator backed by verified GGUF weights."""

    def __init__(self, identity: LocalModelIdentity | None = None) -> None:
        self.identity = identity or resolve_local_model()
        self._model: Any | None = None
        self._lock = threading.RLock()
        self._loaded_at: float | None = None
        self._acceleration: dict[str, Any] | None = None
        self.config = json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            if str(VENDOR_PATH) not in sys.path:
                sys.path.insert(0, str(VENDOR_PATH))
            import llama_cpp  # type: ignore

            from .hardware import llama_acceleration

            decoding = self.config["decoding"]
            acceleration = llama_acceleration(llama_cpp)
            kwargs: dict[str, Any] = dict(
                model_path=str(self.identity.path),
                n_ctx=int(decoding["context_length"]),
                n_threads=int(decoding["threads"]),
                n_threads_batch=int(decoding["batch_threads"]),
                n_batch=int(decoding["prompt_batch_size"]),
                n_ubatch=int(decoding["micro_batch_size"]),
                seed=int(decoding["seed"]),
                n_gpu_layers=int(acceleration["n_gpu_layers"]),
                offload_kqv=True,
                verbose=False,
            )
            tensor_split = os.getenv("TSINGASK_TENSOR_SPLIT", "").strip()
            if tensor_split:
                kwargs["tensor_split"] = [float(value) for value in tensor_split.split(",")]
            try:
                self._model = llama_cpp.Llama(**kwargs)
            except Exception as exc:
                if acceleration["requested_gpu_layers"] != "auto" or acceleration["n_gpu_layers"] == 0:
                    raise
                kwargs.pop("tensor_split", None)
                kwargs["n_gpu_layers"] = 0
                self._model = llama_cpp.Llama(**kwargs)
                acceleration.update({
                    "mode": "cpu_fallback", "n_gpu_layers": 0,
                    "reason": f"GPU initialization failed: {type(exc).__name__}: {exc}"[:300],
                })
            self._acceleration = acceleration
            self._loaded_at = time.time()
            return self._model

    def health(self, *, load: bool = False) -> dict[str, Any]:
        if load:
            self._load()
        acceleration = self._acceleration
        if acceleration is None:
            try:
                if str(VENDOR_PATH) not in sys.path:
                    sys.path.insert(0, str(VENDOR_PATH))
                import llama_cpp  # type: ignore
                from .hardware import llama_acceleration
                acceleration = llama_acceleration(llama_cpp)
            except Exception as exc:
                acceleration = {"mode": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}
        return {
            "status": "READY" if self._model is not None else "AVAILABLE",
            "model": self.identity.to_dict(),
            "loaded_at": self._loaded_at,
            "acceleration": acceleration,
        }

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end < start:
            raise ValueError("local model did not return a JSON object")
        value = json.loads(cleaned[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("local model output must be a JSON object")
        return value

    def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        *,
        max_tokens: int = 1200,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        model = self._load()
        decoding = self.config["decoding"]
        normalized = list(messages)
        if normalized and normalized[0].get("role") == "system":
            normalized[0] = dict(normalized[0])
            normalized[0]["content"] = normalized[0]["content"] + "\n/no_think"
        with self._lock:
            response = model.create_chat_completion(
                messages=normalized,
                temperature=float(decoding["temperature"] if temperature is None else temperature),
                max_tokens=max_tokens,
                seed=int(decoding["seed"]),
                repeat_penalty=float(decoding["repeat_penalty"]),
                response_format={"type": "json_object", "schema": schema},
            )
        content = response["choices"][0]["message"]["content"] or ""
        return self._parse_json(content)


class LocalQwenFilePlanner:
    """Produces the same trusted FileToolCall contract without external APIs."""

    external = False

    def __init__(self, runtime: LocalQwenRuntime | None = None) -> None:
        self.runtime = runtime or default_local_runtime()

    def plan(
        self,
        request: str,
        route: FileRoute,
        *,
        evidence_context: list[dict[str, Any]] | None = None,
        uploaded_content: dict[str, Any] | None = None,
    ) -> FileToolCall:
        parameters = CampusToolRouter.tool_schemas(openai_wrapper=False)[0]["parameters"]
        payload = {
            "request": request,
            "trusted_route": route.to_dict(),
            "evidence_context": evidence_context or [],
            "uploaded_content": uploaded_content,
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "你是清问 V2 的本地文件规划器。只输出符合 JSON Schema 的对象。"
                    "不得生成本地路径，不得伪造学校要求或来源；学校规定只能来自 evidence_context。"
                    "create 必须给 structured_content；modify 优先给 replacements 或 cell_updates。"
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)[:18000]},
        ]
        try:
            arguments = self.runtime.generate_json(messages, parameters, max_tokens=1500)
            response = {
                "choices": [{"message": {"tool_calls": [{"function": {
                    "name": "create_or_modify_campus_file",
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                }}]}}]
            }
            return OpenAICompatibleFileToolPlanner._parse(response, route, self.runtime.identity.name)
        except Exception as exc:
            if isinstance(exc, ToolCallingError):
                raise
            raise ToolCallingError(f"local file planning failed: {type(exc).__name__}: {exc}") from exc


class LocalQwenGroundedComposer(GroundedAnswerPlannerV2):
    """Produces natural prose while keeping exact evidence spans as the trust boundary."""

    def __init__(self, runtime: LocalQwenRuntime | None = None, *, generate_fast_path: bool = False) -> None:
        self.runtime = runtime or default_local_runtime()
        self.generate_fast_path = generate_fast_path

    def compose(self, plan: Any, evidence: Any) -> dict[str, Any]:
        response = super().compose(plan, evidence)
        if evidence.status not in {"SUPPORTED", "PARTIAL"}:
            response["generation"] = {"model_called": False, "reason": "evidence_gate_blocked"}
            return response
        if plan.path == "FAST" and not self.generate_fast_path:
            response["generation"] = {"model_called": False, "reason": "fast_path"}
            return response
        facts = response.get("confirmed_facts", [])
        if not facts:
            response["generation"] = {"model_called": False, "reason": "no_grounded_facts"}
            return response
        fact_ids = [f"F{index + 1}" for index in range(len(facts))]
        for fact_id, fact in zip(fact_ids, facts):
            fact["fact_id"] = fact_id
        schema = {
            "type": "object",
            "required": ["natural_answer", "used_fact_ids", "action_order"],
            "properties": {
                "natural_answer": {"type": "string"},
                "used_fact_ids": {"type": "array", "items": {"type": "string", "enum": fact_ids}},
                "action_order": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["conditions", "materials", "steps", "deadlines", "official_entries"]},
                },
            },
        }
        prompt = {
            "query": plan.original_query,
            "evidence_status": evidence.status,
            "facts": {fact_id: fact["text"] for fact_id, fact in zip(fact_ids, facts)},
            "available_action_sections": list((response.get("action_plan") or {}).keys()),
            "writing_requirements": [
                "第一句直接给结论，语气像熟悉校园办事的人，务实、简洁，不要解释程序流程",
                "优先说明用户现在该做什么、先确认什么；避免空话和公文式套话",
                "只能改写 facts 中已经出现的信息，不新增条件、日期、金额、网址或部门",
                "每个自然段末尾至少标一个事实编号，例如 [F1]；PARTIAL 必须明确仍不能确认什么",
                "只能使用 [F1] 这类事实编号，不要输出 [PARTIAL]、[SUPPORTED] 等状态标签",
                "不要把事实编号写成列表标题，不要输出 Markdown 表格",
            ],
        }
        try:
            generated = self.runtime.generate_json(
                [
                    {"role": "system", "content": "你是清华校园事务助手。请把给定证据组织成简洁、友好、可直接阅读的中文回答。严格服从写作约束，只输出 JSON。"},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                schema,
                max_tokens=700,
                temperature=0.0,
            )
            by_id = dict(zip(fact_ids, facts))
            dropped_claims = 0
            try:
                natural_answer = self._validate_natural_answer(
                    generated.get("natural_answer"), fact_ids, facts, evidence.status
                )
            except ValueError:
                natural_answer, dropped_claims = self._salvage_supported_claims(
                    generated.get("natural_answer"), fact_ids, facts, evidence.status
                )
            selected = []
            cited_fact_ids = re.findall(r"\[(F\d+)\]", natural_answer)
            for fact_id in cited_fact_ids:
                if fact_id in by_id and by_id[fact_id] not in selected:
                    selected.append(by_id[fact_id])
            if selected:
                response["confirmed_facts"] = selected
            response["answer"] = natural_answer
            action = response.get("action_plan")
            if action:
                order = generated.get("action_order", [])
                response["action_plan"] = {key: action[key] for key in order if key in action}
                response["action_plan"].update({key: value for key, value in action.items() if key not in response["action_plan"]})
            response["generation"] = {
                "model_called": True, "model": self.runtime.identity.to_dict(),
                "mode": "grounded_natural_answer", "validated": True,
                "dropped_unsupported_claims": dropped_claims,
            }
        except Exception as exc:
            response["generation"] = {
                "model_called": False,
                "reason": "local_model_fallback",
                "error": f"{type(exc).__name__}: {exc}",
            }
        return response

    @classmethod
    def _salvage_supported_claims(
        cls, value: Any, fact_ids: list[str], facts: list[dict[str, Any]], status: str
    ) -> tuple[str, int]:
        if status != "SUPPORTED" or not isinstance(value, str):
            raise ValueError("partial answers cannot be salvaged without an explicit limitation")
        candidates: list[str] = []
        cursor = 0
        for marker_match in re.finditer(r"(?:\[F\d+\])+", value):
            text = value[cursor:marker_match.start()].strip("。！？；\n ")
            if text:
                candidates.append(f"{text}。{marker_match.group(0)}")
            cursor = marker_match.end()
        accepted = []
        for candidate in candidates:
            try:
                accepted.append(cls._validate_natural_answer(candidate, fact_ids, facts, "SUPPORTED"))
            except ValueError:
                continue
        if not accepted:
            raise ValueError("no individually grounded natural-language claims survived validation")
        return "\n\n".join(accepted), len(candidates) - len(accepted)

    @staticmethod
    def _validate_natural_answer(value: Any, fact_ids: list[str], facts: list[dict[str, Any]], status: str) -> str:
        if not isinstance(value, str):
            raise ValueError("natural_answer must be a string")
        answer = re.sub(r"[ \t]+", " ", value).strip()
        if not 20 <= len(answer) <= 1200 or "http://" in answer or "https://" in answer:
            raise ValueError("natural answer length or URL constraint failed")
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", answer) if part.strip()]
        valid = set(fact_ids)
        cited: set[str] = set()
        for paragraph in paragraphs:
            markers = set(re.findall(r"\[(F\d+)\]", paragraph))
            bracket_tokens = set(re.findall(r"\[([^\]]+)\]", paragraph))
            if bracket_tokens != markers or not markers or not markers <= valid:
                raise ValueError("every paragraph must cite valid fact IDs")
            cited.update(markers)
        if not cited:
            raise ValueError("natural answer contains no fact citations")
        by_id = dict(zip(fact_ids, facts))
        claims = []
        cursor = 0
        for marker_match in re.finditer(r"(?:\[F\d+\])+", answer):
            claim_text = answer[cursor:marker_match.start()].strip("。！？；\n ")
            claim_ids = re.findall(r"\[(F\d+)\]", marker_match.group(0))
            if not claim_text:
                raise ValueError("fact citation must follow a claim")
            claims.append((claim_text, claim_ids))
            cursor = marker_match.end()
        for claim_text, claim_ids in claims:
            evidence_for_claim = " ".join(by_id[fact_id]["text"] for fact_id in claim_ids)
            claim_chars = re.findall(r"[\u3400-\u9fff]", claim_text)
            evidence_chars = re.findall(r"[\u3400-\u9fff]", evidence_for_claim)
            claim_bigrams = {"".join(claim_chars[index:index + 2]) for index in range(len(claim_chars) - 1)}
            evidence_bigrams = {"".join(evidence_chars[index:index + 2]) for index in range(len(evidence_chars) - 1)}
            overlap = len(claim_bigrams & evidence_bigrams) / max(1, len(claim_bigrams))
            if overlap < 0.25:
                raise ValueError("natural answer claim is not sufficiently grounded by its cited fact")
        if not claims or answer[cursor:].strip("。！？；\n "):
            raise ValueError("every claim must end with a fact citation")
        evidence_text = " ".join(fact["text"] for fact in facts)
        plain_answer = re.sub(r"\[F\d+\]", "", answer)
        generated_numbers = set(re.findall(r"\d+(?:\.\d+)?", plain_answer))
        evidence_numbers = set(re.findall(r"\d+(?:\.\d+)?", evidence_text))
        if generated_numbers - evidence_numbers:
            raise ValueError("natural answer introduced unsupported numeric claims")
        if status == "PARTIAL" and not any(word in answer for word in ("部分", "目前", "暂时", "尚不能", "还不能", "未能确认")):
            raise ValueError("partial answer must state its limitation")
        return answer


_DEFAULT_RUNTIME: LocalQwenRuntime | None = None


def default_local_runtime() -> LocalQwenRuntime:
    global _DEFAULT_RUNTIME
    if _DEFAULT_RUNTIME is None:
        _DEFAULT_RUNTIME = LocalQwenRuntime()
    return _DEFAULT_RUNTIME
