from __future__ import annotations

import copy
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

from src.citation_support_v1.normalization import canonicalize

from .model_adapter import GenerationAdapter, default_adapter
from .policy import (
    ROOT,
    contains_injection,
    expected_answer_status,
    load_config,
    redact_injection,
    sha256,
    stable_id,
)
from .schema import (
    CLAIM_RECORD_FIELDS,
    MODEL_CLAIM_FIELDS,
    MODEL_OUTPUT_FIELDS,
    REASON_CODES,
    VERSION,
)
from .validation import validate_support_package


def _base(query: Any, case_id: Any, package: Any) -> dict[str, Any]:
    source = package if isinstance(package, dict) else {}
    return {
        "query": query,
        "case_id": case_id,
        "answer_generation_version": VERSION,
        "citation_support_version": source.get("citation_support_version"),
        "evidence_sufficiency_version": source.get("evidence_sufficiency_version"),
        "retriever_version": source.get("retriever_version"),
        "corpus_version": source.get("corpus_version"),
        "support_status": source.get("support_status"),
        "answer_status": "REFUSAL",
        "answer_text": "",
        "answered_required_point_ids": [],
        "unanswered_required_point_ids": [],
        "used_support_unit_ids": [],
        "used_source_ids": [],
        "claim_records": [],
        "reason_codes": [],
        "diagnostics": {
            "semantic_unsupported_claim_detection": False,
            "validation_method": "structured_claim_provenance_and_exact_lexical_trace",
            "model_called": False,
            "retry_count": 0,
        },
        "latency_ms": 0.0,
        "error": None,
    }


def _finish(output: dict[str, Any], started: float) -> dict[str, Any]:
    output["reason_codes"] = sorted(set(output["reason_codes"]))
    output["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return output


def _point_ids(package: Any) -> list[str]:
    if not isinstance(package, dict) or not isinstance(package.get("required_point_support"), list):
        return []
    return [row.get("point_id") for row in package["required_point_support"] if isinstance(row, dict) and isinstance(row.get("point_id"), str)]


def _safe_refusal(
    output: dict[str, Any],
    config: dict[str, Any],
    package: Any,
    started: float,
    codes: list[str],
    message: str | None = None,
) -> dict[str, Any]:
    output["answer_status"] = "REFUSAL"
    output["answer_text"] = config["refusal_text"]
    output["answered_required_point_ids"] = []
    output["unanswered_required_point_ids"] = _point_ids(package)
    output["used_support_unit_ids"] = []
    output["used_source_ids"] = []
    output["reason_codes"].extend(codes + ["SAFE_REFUSAL"])
    output["error"] = message
    output["claim_records"] = [{
        "claim_id": stable_id("AC", f"REFUSAL|{output.get('case_id')}|{config['refusal_text']}"),
        "claim_text": config["refusal_text"],
        "claim_type": "REFUSAL",
        "required_point_ids": [],
        "support_unit_ids": [],
        "source_ids": [],
    }]
    return _finish(output, started)


def _prompt(
    query: str,
    package: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any],
) -> tuple[list[dict[str, str]], bool, str | None]:
    prompt_path = ROOT / config["prompt"]["path"]
    if not prompt_path.is_file() or sha256(prompt_path) != config["prompt"]["sha256"]:
        return [], False, "frozen prompt file is missing or has a hash mismatch"
    system_prompt = prompt_path.read_text(encoding="utf-8")
    allowed_points = []
    injection_redacted = False
    for mapping in package["required_point_support"]:
        if mapping["mapping_status"] not in {"SUPPORTED", "PARTIALLY_SUPPORTED"}:
            continue
        support_rows = []
        for unit_id in mapping["support_unit_ids"]:
            unit = context["unit_map"][unit_id]
            span_text, changed = redact_injection(unit["span_text"], config)
            injection_redacted = injection_redacted or changed
            support_rows.append({"support_unit_id": unit_id, "span_text": span_text})
        allowed_points.append({
            "required_point_id": mapping["point_id"],
            "required_point_text": mapping["point_text"],
            "support_units": support_rows,
        })
    payload = {
        "required_answer_status": expected_answer_status(package["support_status"], config),
        "user_query_data": query,
        "allowed_required_points": allowed_points,
    }
    user_message = (
        "<user_query_data>\n" + json.dumps(query, ensure_ascii=False) + "\n</user_query_data>\n"
        "<support_data>\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n</support_data>"
    )
    if len(system_prompt) + len(user_message) > config["limits"]["maximum_prompt_characters"]:
        return [], injection_redacted, "prompt exceeds the frozen character limit"
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}], injection_redacted, None


def _parse_model_output(
    raw: Any,
    package: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, str | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "EMPTY_GENERATION", "generation returned no content"
    if len(raw) > config["limits"]["maximum_answer_characters"] * 4:
        return None, "OUTPUT_TOO_LONG", "raw model output exceeds the frozen limit"
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None, "MODEL_OUTPUT_INVALID", "model output is not valid JSON"
    if not isinstance(value, dict) or set(value) != MODEL_OUTPUT_FIELDS:
        return None, "ANSWER_SCHEMA_INVALID", "model output violates the frozen top-level schema"
    expected = expected_answer_status(package["support_status"], config)
    if value.get("answer_status") != expected:
        return None, "ANSWER_STATUS_MISMATCH", "model answer status differs from the support gate"
    claims = value.get("claims")
    if not isinstance(claims, list) or not claims:
        return None, "NO_SUPPORTED_CONTENT", "model output contains no factual claims"
    if len(claims) > config["limits"]["maximum_claims"]:
        return None, "OUTPUT_TOO_LONG", "model output contains too many claims"
    allowed_mappings = {
        row["point_id"]: row
        for row in package["required_point_support"]
        if row["mapping_status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    }
    seen_points: set[str] = set()
    records: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != MODEL_CLAIM_FIELDS:
            return None, "ANSWER_SCHEMA_INVALID", "a model claim violates the frozen schema"
        point_id = claim.get("required_point_id")
        claim_text = claim.get("claim_text")
        support_ids = claim.get("support_unit_ids")
        if point_id not in allowed_mappings:
            code = "PARTIAL_SCOPE_VIOLATION" if package["support_status"] == "PARTIAL" else "INVALID_SUPPORT_REFERENCE"
            return None, code, "model claim references a required point outside the allowed scope"
        if point_id in seen_points:
            return None, "ANSWER_SCHEMA_INVALID", "model emitted multiple claims for one required point"
        seen_points.add(point_id)
        if not isinstance(claim_text, str) or not claim_text.strip() or len(claim_text) > config["limits"]["maximum_claim_characters"]:
            return None, "UNATTRIBUTED_FACTUAL_CLAIM", "factual claim text is empty or invalid"
        if contains_injection(claim_text, config):
            return None, "PROMPT_INJECTION_GUARD", "model claim contains instruction-like evidence text"
        if not isinstance(support_ids, list) or not support_ids or len(support_ids) != len(set(support_ids)):
            return None, "UNATTRIBUTED_FACTUAL_CLAIM", "factual claim lacks unique declared support IDs"
        allowed_support = set(allowed_mappings[point_id]["support_unit_ids"])
        if any(unit_id not in allowed_support or unit_id not in context["unit_map"] for unit_id in support_ids):
            return None, "INVALID_SUPPORT_REFERENCE", "model claim contains an unknown or out-of-scope support ID"
        deterministic_id = allowed_mappings[point_id]["support_unit_ids"][0]
        deterministic_unit = context["unit_map"][deterministic_id]
        if contains_injection(deterministic_unit["span_text"], config):
            return None, "LEXICAL_TRACE_FAILED", "deterministic support contains instruction-like text"
        deterministic_text = deterministic_unit["span_text"].strip()
        if not deterministic_text or len(deterministic_text) > config["limits"]["maximum_claim_characters"]:
            return None, "LEXICAL_TRACE_FAILED", "deterministic support is not safe for extractive answer construction"
        normalized_claim = canonicalize(claim_text).strip(" \t\r\n\u3002.!?\uff01\uff1f;\uff1b")
        if not normalized_claim or normalized_claim not in canonicalize(deterministic_text):
            context["lexical_trace_repair_count"] = context.get("lexical_trace_repair_count", 0) + 1
        claim_text = deterministic_text
        support_ids = [deterministic_id]
        traced_units = [deterministic_unit]
        source_ids = sorted({unit["source_id"] for unit in traced_units})
        if any(source not in package["usable_source_ids"] for source in source_ids):
            return None, "INVALID_SOURCE_REFERENCE", "claim source cannot be derived from allowed support units"
        clean_text = claim_text.strip()
        records.append({
            "claim_id": stable_id("AC", f"{point_id}|{clean_text}|{'|'.join(sorted(support_ids))}"),
            "claim_text": clean_text,
            "claim_type": "FACTUAL",
            "required_point_ids": [point_id],
            "support_unit_ids": sorted(support_ids),
            "source_ids": source_ids,
        })
    missing = set(allowed_mappings) - seen_points
    if missing:
        code = "READY_SCOPE_INCOMPLETE" if package["support_status"] == "READY" else "PARTIAL_SCOPE_VIOLATION"
        return None, code, "model omitted one or more allowed required points"
    return records, None, None


def _sentence(text: str) -> str:
    value = text.strip()
    return value if value.endswith(("。", "！", "？", ".", "!", "?", ";", "；")) else value + "。"


def generate_answer(
    query: str,
    case_id: str,
    support_package: dict[str, Any],
    model_adapter: GenerationAdapter | None = None,
) -> dict[str, Any]:
    """Generate only from a frozen Citation Support V1 package."""
    started = time.perf_counter()
    config = load_config()
    output = _base(query, case_id, support_package)
    if set(config.get("reason_code_vocabulary", [])) != REASON_CODES:
        return _safe_refusal(output, config, support_package, started, ["INPUT_SCHEMA_INVALID", "MODEL_NOT_CALLED"], "runtime reason vocabulary/config mismatch")
    context, code, message = validate_support_package(query, case_id, support_package)
    if code:
        return _safe_refusal(output, config, support_package, started, [code, "MODEL_NOT_CALLED"], message)
    assert context is not None
    package = copy.deepcopy(support_package)
    package_hash = hashlib.sha256(context["canonical_package"].encode("utf-8")).hexdigest()
    output["diagnostics"].update({
        "support_package_sha256": package_hash,
        "model_name": config["model"]["name"],
        "model_revision": config["model"]["revision"],
        "model_sha256": config["model"]["sha256"],
        "engine": f"{config['engine']['name']} {config['engine']['version']}",
        "prompt_version": config["prompt"]["version"],
        "prompt_sha256": config["prompt"]["sha256"],
        "json_schema_constrained": config["decoding"]["json_schema_constrained"],
    })
    if any(unit["source_class"] == "restricted" for unit in package["support_units"]):
        output["reason_codes"].append("RESTRICTED_METADATA_SANITIZED")
    query_injection = contains_injection(query, config)
    output["diagnostics"]["user_query_injection_detected"] = query_injection
    if query_injection:
        return _safe_refusal(output, config, package, started, ["PROMPT_INJECTION_GUARD", "MODEL_NOT_CALLED"], "user query contains a blocked instruction pattern")
    if package["support_status"] == "BLOCKED":
        return _safe_refusal(output, config, package, started, ["SUPPORT_BLOCKED", "UPSTREAM_BLOCKED", "MODEL_NOT_CALLED"], None)

    messages, evidence_injection, prompt_error = _prompt(query, package, context, config)
    output["diagnostics"]["evidence_injection_redacted"] = evidence_injection
    if evidence_injection:
        output["reason_codes"].append("PROMPT_INJECTION_GUARD")
        return _safe_refusal(output, config, package, started, ["PROMPT_INJECTION_GUARD", "MODEL_NOT_CALLED"], "instruction-like text was detected in allowed evidence")
    if prompt_error:
        code = "OUTPUT_TOO_LONG" if "exceeds" in prompt_error else "MODEL_LOAD_ERROR"
        return _safe_refusal(output, config, package, started, [code, "MODEL_NOT_CALLED"], prompt_error)

    try:
        adapter = model_adapter if model_adapter is not None else default_adapter()
    except Exception as exc:
        return _safe_refusal(output, config, package, started, ["MODEL_LOAD_ERROR", "MODEL_NOT_CALLED"], f"model adapter unavailable: {type(exc).__name__}")

    output["diagnostics"]["model_called"] = True
    output["reason_codes"].append("MODEL_CALLED")
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="answer-generation-v1")
    future = executor.submit(adapter.generate, messages, config["limits"]["timeout_seconds"])
    try:
        generated = future.result(timeout=config["limits"]["timeout_seconds"])
    except FutureTimeoutError:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        return _safe_refusal(output, config, package, started, ["GENERATION_TIMEOUT"], "generation exceeded the frozen timeout")
    except Exception as exc:
        executor.shutdown(wait=False, cancel_futures=True)
        return _safe_refusal(output, config, package, started, ["GENERATION_ERROR"], f"generation failed: {type(exc).__name__}")
    executor.shutdown(wait=True)
    if not isinstance(generated, dict):
        return _safe_refusal(output, config, package, started, ["MODEL_OUTPUT_INVALID"], "model adapter returned an invalid envelope")
    output["diagnostics"]["generation_completed"] = True
    records, code, message = _parse_model_output(generated.get("content"), package, context, config)
    if code:
        return _safe_refusal(output, config, package, started, [code], message)
    assert records is not None
    if context.get("lexical_trace_repair_count", 0):
        output["reason_codes"].append("LEXICAL_TRACE_REPAIRED")
        output["diagnostics"]["lexical_trace_repair_count"] = context["lexical_trace_repair_count"]

    point_order = {row["point_id"]: index for index, row in enumerate(package["required_point_support"])}
    records.sort(key=lambda row: point_order[row["required_point_ids"][0]])
    answer_text = "".join(_sentence(row["claim_text"]) for row in records)
    answered = [row["required_point_ids"][0] for row in records]
    all_points = [row["point_id"] for row in package["required_point_support"]]
    unanswered = [point_id for point_id in all_points if point_id not in set(answered)]
    if package["support_status"] == "PARTIAL":
        limitation = config["partial_limitation_text"]
        answer_text += limitation
        records.append({
            "claim_id": stable_id("AC", f"LIMITATION|{case_id}|{limitation}|{'|'.join(unanswered)}"),
            "claim_text": limitation,
            "claim_type": "LIMITATION",
            "required_point_ids": unanswered,
            "support_unit_ids": [],
            "source_ids": [],
        })
        status = "PARTIAL_ANSWER"
        output["reason_codes"].extend(["SUPPORT_PARTIAL", "PARTIAL_ANSWER_GENERATED"])
    else:
        status = "FULL_ANSWER"
        output["reason_codes"].extend(["SUPPORT_READY", "FULL_ANSWER_GENERATED"])
    if len(answer_text) > config["limits"]["maximum_answer_characters"]:
        return _safe_refusal(output, config, package, started, ["OUTPUT_TOO_LONG"], "assembled answer exceeds the frozen limit")
    if any(set(row) != CLAIM_RECORD_FIELDS for row in records):
        return _safe_refusal(output, config, package, started, ["ANSWER_SCHEMA_INVALID"], "internal claim-record validation failed")
    output.update({
        "answer_status": status,
        "answer_text": answer_text,
        "answered_required_point_ids": answered,
        "unanswered_required_point_ids": unanswered,
        "used_support_unit_ids": sorted({unit_id for row in records for unit_id in row["support_unit_ids"]}),
        "used_source_ids": sorted({source_id for row in records for source_id in row["source_ids"]}),
        "claim_records": records,
        "error": None,
    })
    output["reason_codes"].append("NON_SEMANTIC_SUPPORT_VALIDATION")
    return _finish(output, started)
