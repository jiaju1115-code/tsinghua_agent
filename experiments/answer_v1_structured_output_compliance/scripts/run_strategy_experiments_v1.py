from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.answer_generation_v1.model_adapter import default_adapter
from src.runtime_v1 import RuntimeV1

CASES = {"POS002", "POS006", "POS008"}
DATA = ROOT / "experiments/positive_demo_validation_v1/data/positive_demo_question_set_v1.jsonl"
OUT = ROOT / "experiments/answer_v1_structured_output_compliance/results"


def support_payload(messages: list[dict[str, str]]) -> dict:
    content = messages[-1]["content"]
    body = content.split("<support_data>\n", 1)[1].split("\n</support_data>", 1)[0]
    return json.loads(body)


def dynamic_schema(messages: list[dict[str, str]]) -> dict:
    payload = support_payload(messages)
    points = payload["allowed_required_points"]
    claim_variants = []
    for point in points:
        ids = [row["support_unit_id"] for row in point["support_units"]]
        claim_variants.append({
            "type": "object",
            "properties": {
                "required_point_id": {"type": "string", "enum": [point["required_required_point_id"] if "required_required_point_id" in point else point["required_point_id"]]},
                "claim_text": {"type": "string", "minLength": 1},
                "support_unit_ids": {"type": "array", "items": {"type": "string", "enum": ids}, "minItems": 1, "maxItems": 1, "uniqueItems": True},
            },
            "required": ["required_point_id", "claim_text", "support_unit_ids"],
            "additionalProperties": False,
        })
    return {
        "type": "object",
        "properties": {
            "answer_status": {"type": "string", "enum": [payload["required_answer_status"]]},
            "claims": {"type": "array", "items": {"oneOf": claim_variants}, "minItems": len(points), "maxItems": len(points)},
        },
        "required": ["answer_status", "claims"],
        "additionalProperties": False,
    }


class ConstrainedAdapter:
    name = "CONSTRAINED_DECODING"

    def __init__(self, base):
        self.base = base
        self.calls = 0
        self.errors: list[str] = []

    def generate(self, messages, timeout_seconds):
        self.calls += 1
        try:
            import llama_cpp
            grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(dynamic_schema(messages), ensure_ascii=False), verbose=False)
            started = time.perf_counter()
            decoding = self.base.config["decoding"]
            response = self.base._llm.create_chat_completion(
                messages=messages,
                temperature=decoding["temperature"],
                max_tokens=decoding["max_output_tokens"],
                seed=decoding["seed"],
                repeat_penalty=decoding["repeat_penalty"],
                grammar=grammar,
            )
            content = response["choices"][0]["message"]["content"]
            return {"content": content, "finish_reason": response["choices"][0].get("finish_reason"), "generation_latency_ms": round((time.perf_counter() - started) * 1000, 3), "raw_output_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(), "strategy": self.name}
        except Exception as exc:
            self.errors.append(f"{type(exc).__name__}: {exc}")
            return self.base.generate(messages, timeout_seconds)


def contract_feedback(raw: str, messages: list[dict[str, str]]) -> str | None:
    try:
        value = json.loads(raw)
        payload = support_payload(messages)
        allowed = {p["required_point_id"]: {u["support_unit_id"] for u in p["support_units"]} for p in payload["allowed_required_points"]}
        claims = value.get("claims", [])
        seen = [c.get("required_point_id") for c in claims if isinstance(c, dict)]
        if len(seen) != len(set(seen)):
            return "duplicate required_point_id; emit at most one claim per allowed required point"
        for claim in claims:
            if claim.get("required_point_id") not in allowed:
                return "required_point_id is outside the allowed required-point set"
            if not set(claim.get("support_unit_ids", [])) <= allowed[claim["required_point_id"]]:
                return "support binding is invalid; use only support IDs mapped to the same required point"
        missing = sorted(set(allowed) - set(seen))
        if missing:
            return "missing allowed required-point coverage; emit one claim for every allowed required point"
    except Exception:
        return "output must remain valid JSON and obey the existing structured-output shape"
    return None


class BoundedRetryAdapter:
    name = "BOUNDED_RETRY"

    def __init__(self, base):
        self.base = base
        self.calls = 0

    def generate(self, messages, timeout_seconds):
        self.calls += 1
        first = self.base.generate(messages, timeout_seconds)
        feedback = contract_feedback(first.get("content", ""), messages)
        if not feedback:
            first["strategy"] = self.name
            first["retry_count"] = 0
            return first
        retry_messages = copy.deepcopy(messages)
        retry_messages[-1]["content"] += f"\n<contract_feedback>\n{feedback}\nReturn corrected JSON only. Do not add facts or invent support.\n</contract_feedback>"
        self.calls += 1
        second = self.base.generate(retry_messages, timeout_seconds)
        second["strategy"] = self.name
        second["retry_count"] = 1
        second["contract_feedback"] = feedback
        return second


def run_strategy(name: str, adapter_factory):
    base = default_adapter()
    adapter = adapter_factory(base)
    runtime = RuntimeV1(model_adapter=adapter)
    questions = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip() and json.loads(line)["demo_id"] in CASES]
    rows = []
    for q in questions:
        result = runtime.answer_query(q["query"], request_id=q["demo_id"])
        answer = result["diagnostics"].get("answer_runtime") or {}
        rows.append({"case_id": q["demo_id"], "strategy": name, "final_status": result.get("status"), "answer_status": answer.get("answer_status"), "reason_codes": answer.get("reason_codes", []), "error": answer.get("error"), "model_called": answer.get("diagnostics", {}).get("model_called"), "latency_ms": (result["diagnostics"].get("orchestrator") or {}).get("total_latency_ms"), "adapter_calls": adapter.calls, "adapter_errors": getattr(adapter, "errors", [])})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    constrained = run_strategy("CONSTRAINED_DECODING", ConstrainedAdapter)
    retry = run_strategy("BOUNDED_RETRY", BoundedRetryAdapter)
    result = {"version": "ANSWER_V1_STRUCTURED_OUTPUT_STRATEGY_RESULTS_V1", "baseline": {"source": "answer_v1_partial_contract_runtime_trace_v1.json", "cases": 3, "note": "deterministic baseline captured previously; no additional baseline calls required"}, "constrained_decoding": constrained, "bounded_retry": retry}
    (OUT / "constrained_decoding_results.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in constrained) + "\n", encoding="utf-8")
    (OUT / "bounded_retry_results.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in retry) + "\n", encoding="utf-8")
    (OUT / "strategy_raw_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"constrained": constrained, "retry": retry}, ensure_ascii=False))


if __name__ == "__main__":
    main()
