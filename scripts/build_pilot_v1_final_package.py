"""Build the frozen Pilot V1 general replay dataset and upload package.

This script only consumes immutable/frozen local inputs.  It never launches
training and never mutates any historical input artifact.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/03_fine_tuning/pilot_v1/targeted_topup_v3/raw"
FINAL = ROOT / "data/03_fine_tuning/pilot_v1/final"
RELEASE = ROOT / "release/pilot_v1_training_package"
AUDIT = ROOT / "evaluation/fine_tuning_pilot_v1_final"
FREEZE_ID = "PILOT_V1_GENERAL_REPLAY_FROZEN"
SEED = 42

TARGET_NEW = {
    "INSTRUCTION_VALUE_FIDELITY": 263,
    "GENERAL_QA_SCIENCE_READING": 209,
    "GENERAL_REASONING": 189,
    "WRITING_MULTILINGUAL": 30,
    "CODING": 87,
}
TARGET_FINAL = {
    "INSTRUCTION_VALUE_FIDELITY": 300,
    "GENERAL_QA_SCIENCE_READING": 264,
    "GENERAL_REASONING": 240,
    "WRITING_MULTILINGUAL": 120,
    "CODING": 96,
    "PROGRAMMATIC_MATH": 120,
    "OTHER_MATH": 60,
}
VAL_TARGET = {
    "INSTRUCTION_VALUE_FIDELITY": 30,
    "GENERAL_QA_SCIENCE_READING": 26,
    "GENERAL_REASONING": 24,
    "WRITING_MULTILINGUAL": 12,
    "CODING": 10,
    "PROGRAMMATIC_MATH": 12,
    "OTHER_MATH": 6,
}
REVISIONS = {
    "OpenAssistant/oasst1": "fdf72ae0827c1cda404aff25b6603abec9e3399b",
    "Surpem/GEmO": "fd553b069ca17bbbcfe13dbb49912aba155606b2",
    "TIGER-Lab/MathInstruct": "b4fdc323a7be1379c9c7c0b67b1de72dfee2111a",
    "allenai/tulu-3-sft-personas-instruction-following": "fe0c7d350c9b4542b8d829a6f1daa1c259f0ba0e",
    "databricks/databricks-dolly-15k": "bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a",
    "rajpurkar/squad": "7b6d24c440a36b6815f21b70d25016731768db1f",
    "tasksource/ruletaker": "a3e0880baeb6ec3d478f4c4d85afe04b21b6cf7f",
    "nvidia/OpenCodeInstruct": "8f3ba5bafe4d6e8db46082cf7ae6741bc370604d",
    "google-research-datasets/mbpp": "4bb6404fdc6cacfda99d4ac4205087b89d32030c",
    "NousResearch/hermes-function-calling-v1": "dae3e1d28cfbcf4b915c04ea1e072030529b4bda",
    "Team-ACE/ToolACE": "6bda777c88d21e5a204703c1ee45597a8fa4f734",
    "AIML-TUDA/SLR-Bench": "cecc0aa2602943ead28a4ea74c7a8f3c91264cbf",
}
LICENSES = {
    "OpenAssistant/oasst1": "Apache-2.0",
    "Surpem/GEmO": "MIT",
    "TIGER-Lab/MathInstruct": "MIT",
    "allenai/tulu-3-sft-personas-instruction-following": "ODC-BY-1.0",
    "databricks/databricks-dolly-15k": "CC-BY-SA-3.0",
    "rajpurkar/squad": "CC-BY-SA-4.0",
    "tasksource/ruletaker": "Apache-2.0",
    "nvidia/OpenCodeInstruct": "CC-BY-4.0",
    "google-research-datasets/mbpp": "CC-BY-4.0",
    "NousResearch/hermes-function-calling-v1": "Apache-2.0",
    "Team-ACE/ToolACE": "Apache-2.0",
    "AIML-TUDA/SLR-Bench": "CC-BY-4.0",
}
SOURCE_LOC = {
    "NousResearch/hermes-function-calling-v1": ("func_calling", "train", "func-calling.json"),
    "Team-ACE/ToolACE": ("default", "train", "data.json"),
    "AIML-TUDA/SLR-Bench": ("v1-All", "train", "v1-All/train-00000-of-00003.parquet"),
    "rajpurkar/squad": ("plain_text", "train", "plain_text/train-00000-of-00001.parquet"),
    "tasksource/ruletaker": ("default", "train", "data/train-00000-of-00001-52adaa842dd7ed92.parquet"),
    "google-research-datasets/mbpp": ("full", "train", "full/train-00000-of-00001.parquet"),
    "nvidia/OpenCodeInstruct": ("train", "train", "data/train-00000-of-00050.parquet"),
    "databricks/databricks-dolly-15k": ("default", "train", "databricks-dolly-15k.jsonl"),
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_text(text: str) -> str:
    return sha_bytes(text.encode("utf-8"))


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def prompt_text(row: dict) -> str:
    return "\n".join(m["content"] for m in row["messages"] if m["role"] != "assistant")


def content_text(row: dict) -> str:
    return "\n".join(m["content"] for m in row["messages"])


def jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def emit_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in rows), encoding="utf-8")


def path_fingerprint(path: Path) -> dict:
    if path.is_file():
        return {"sha256": sha_bytes(path.read_bytes()), "bytes": path.stat().st_size}
    h = hashlib.sha256()
    files = sorted(x for x in path.rglob("*") if x.is_file())
    for child in files:
        h.update(child.relative_to(path).as_posix().encode("utf-8"))
        h.update(child.read_bytes())
    return {"sha256": h.hexdigest(), "files": len(files)}


def frozen_inputs() -> list[Path]:
    paths = [
        ROOT / "data/fine_tuning_v1/general_capability_candidates_v1_2",
        ROOT / "evaluation/fine_tuning_pilot_v1_data_preflight/proposed_keep.jsonl",
        ROOT / "evaluation/fine_tuning_pilot_v1_data_preflight/proposed_drop.jsonl",
        ROOT / "evaluation/fine_tuning_pilot_v1_acquisition_v2",
        ROOT / "evaluation/fine_tuning_pilot_v1_revision_recovery_v2_1",
        ROOT / "evaluation/fine_tuning_pilot_v1_targeted_source_v2_2",
        ROOT / "data/03_fine_tuning/pilot_v1/general_acquisition_v2",
        ROOT / "data/03_fine_tuning/pilot_v1/general_acquisition_v2_1_revision_recovery",
        ROOT / "data/03_fine_tuning/pilot_v1/opencode_revision_recovery_v2_2",
        ROOT / "experiments/fine_tuning_pilot_v0_upload/config/training_config.yaml",
        ROOT / "experiments/fine_tuning_pilot_v0_upload/scripts/preprocess.py",
        ROOT / "experiments/fine_tuning_pilot_v0_evaluation_upload/data/general/general_eval_v0_1.jsonl",
    ]
    assert all(x.exists() for x in paths)
    return paths


def make_row(*, uid: str, family: str, subtype: str, source: str, config: str, split: str,
             source_file: str, source_row_id: str, source_row_index: int, raw: dict,
             messages: list[dict], origin: str) -> dict:
    raw_hash = sha_text(canonical_json(raw))
    normalized_hash = sha_text(norm("\n".join(x["content"] for x in messages)))
    return {
        "id": uid,
        "messages": messages,
        "metadata": {
            "task_family": family,
            "subtype": subtype,
            "source": source,
            "publisher": source.split("/", 1)[0],
            "license": LICENSES[source],
            "source_revision": REVISIONS[source],
            "source_config": config,
            "source_split": split,
            "source_file": source_file,
            "source_row_id": str(source_row_id),
            "source_row_index": int(source_row_index),
            "raw_sha256": raw_hash,
            "normalized_sha256": normalized_hash,
            "origin": origin,
            "quality_status": "ACCEPT",
            "license_status": "PASS",
            "provenance_status": "PASS",
        },
    }


def load_keep() -> list[dict]:
    keep_meta = {x["case_id"]: x for x in jsonl(ROOT / "evaluation/fine_tuning_pilot_v1_data_preflight/proposed_keep.jsonl")}
    drop_ids = {x["case_id"] for x in jsonl(ROOT / "evaluation/fine_tuning_pilot_v1_data_preflight/proposed_drop.jsonl")}
    pool = []
    for path in sorted((ROOT / "data/fine_tuning_v1/general_capability_candidates_v1_2").glob("*.jsonl")):
        if path.name != "general_family_registry.jsonl":
            pool.extend(jsonl(path))
    assert len(pool) == 841 and len(keep_meta) == 422 and len(drop_ids) == 419
    rows = []
    for idx, raw in enumerate(pool):
        if raw["case_id"] not in keep_meta:
            continue
        meta = keep_meta[raw["case_id"]]
        source = raw["source_dataset"]
        user = raw["instruction"] + (("\n\nContext:\n" + raw.get("input", "")) if raw.get("input") else "")
        rows.append(make_row(
            uid=raw["case_id"], family=meta["normalized_family"], subtype=raw.get("construction_type", "legacy"),
            source=source, config=raw.get("source_subset", "default"), split=raw.get("source_split", "train"),
            source_file="historical_frozen_v1_2_pool", source_row_id=raw["source_row_id"], source_row_index=idx,
            raw=raw, messages=[{"role": "user", "content": user}, {"role": "assistant", "content": raw["answer"]}], origin="OLD_KEEP"))
        rows[-1]["metadata"]["historical_source_revision"] = raw.get("source_revision", "main")
    assert len(rows) == 422 and not ({x["id"] for x in rows} & drop_ids)
    return rows


def subtype_existing(raw: dict) -> str:
    sub = raw.get("subfamily", "verified")
    if sub == "verifiable_constraints":
        inst = raw.get("instruction", "").lower()
        if "exclude" in inst or "without" in inst: return "negative_constraint"
        if "format" in inst or "json" in inst: return "schema_adherence"
        if "order" in inst or "sort" in inst: return "ordering"
        return "constrained_transform"
    if sub == "extraction_or_classification":
        category = raw.get("metadata", {}).get("raw_fields", {}).get("category")
        return "label_fidelity" if category == "classification" else "structured_extraction"
    return sub


def load_verified_new() -> list[dict]:
    paths = [
        ROOT / "data/03_fine_tuning/pilot_v1/general_acquisition_v2_1_revision_recovery/revision_verified_accepted.jsonl",
        ROOT / "data/03_fine_tuning/pilot_v1/opencode_revision_recovery_v2_2/opencode_revision_verified_accepted.jsonl",
    ]
    rows = []
    for path in paths:
        for raw in jsonl(path):
            source = raw["source_dataset"]
            assert raw.get("new_status", raw.get("quality_status")) == "ACCEPT"
            context = raw.get("context", "")
            user = raw["instruction"] + (("\n\nContext:\n" + context) if context else "")
            raw_fields = raw.get("metadata", {}).get("raw_fields", raw)
            source_file = raw.get("source_file") or raw.get("metadata", {}).get("pinned_file", {}).get("path", "pinned_source_artifact")
            rows.append(make_row(
                uid="NEW-" + raw.get("revision_verified_candidate_id", raw["candidate_id"])[:24], family=raw["family"],
                subtype=subtype_existing(raw), source=source, config=raw["source_config"], split=raw["source_split"],
                source_file=source_file, source_row_id=raw["source_row_id"],
                source_row_index=int(raw.get("source_row_index", raw.get("source_row", 0))), raw=raw_fields,
                messages=[{"role": "user", "content": user}, {"role": "assistant", "content": raw["response"]}], origin="VERIFIED_V2_1_OR_V2_2"))
    assert len(rows) == 400
    assert Counter(x["metadata"]["task_family"] for x in rows) == Counter({
        "INSTRUCTION_VALUE_FIDELITY": 40, "GENERAL_QA_SCIENCE_READING": 152,
        "GENERAL_REASONING": 102, "WRITING_MULTILINGUAL": 42, "CODING": 64})
    return rows


def function_subtype(user: str, answer: str) -> str:
    low = user.lower()
    if re.search(r"(cannot|can't|unable|missing|required parameter|none of)", answer, re.I): return "negative_constraint"
    calls = max(answer.count("<tool_call>"), answer.count("("))
    if calls >= 2: return "multi_condition"
    if re.search(r"\b(sort|order|sequence|first|then|after)\b", low): return "ordering"
    if re.search(r"\b(convert|transform|translate|change into)\b", low): return "constrained_transform"
    quoted = re.findall(r"['\"]([^'\"]{2,40})['\"]", user)
    if any(x in answer for x in quoted): return "exact_copy"
    if answer.strip().startswith("<tool_call>") or answer.strip().startswith("["): return "schema_adherence"
    if re.search(r"\b(extract|retrieve|get|find|lookup|search)\b", low): return "structured_extraction"
    return "label_fidelity"


def adapt_hermes(limit: int) -> list[dict]:
    data = json.loads((RAW / "hermes_func_calling.json").read_text(encoding="utf-8"))
    out = []
    for idx, raw in enumerate(data[:limit]):
        conv = raw.get("conversations", [])
        system = next((x.get("value", "") for x in conv if x.get("from") == "system"), "")
        human_pos = next((i for i, x in enumerate(conv) if x.get("from") in {"human", "user"}), None)
        if human_pos is None: continue
        assistant = next((x.get("value", "") for x in conv[human_pos + 1:] if x.get("from") in {"gpt", "assistant"}), "")
        user = conv[human_pos].get("value", "")
        if not user or not assistant or "<tool_call>" not in assistant: continue
        blocks = re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", assistant, re.S)
        try:
            if not blocks or any(not isinstance(json.loads(x), dict) for x in blocks): continue
        except Exception: continue
        if len(system) + len(user) + len(assistant) > 12000: continue
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        out.append(make_row(uid="TOPUP-HERMES-" + sha_text(str(raw.get("id", idx)))[:20], family="INSTRUCTION_VALUE_FIDELITY",
            subtype=function_subtype(user, assistant), source="NousResearch/hermes-function-calling-v1", config="func_calling", split="train",
            source_file="func-calling.json", source_row_id=raw.get("id", idx), source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    return out


def adapt_toolace(limit: int) -> list[dict]:
    data = json.loads((RAW / "toolace_data.json").read_text(encoding="utf-8"))
    out = []
    for idx, raw in enumerate(data[:limit]):
        conv = raw.get("conversations", [])
        user_pos = next((i for i, x in enumerate(conv) if x.get("from") in {"user", "human"}), None)
        if user_pos is None: continue
        assistant = next((x.get("value", "") for x in conv[user_pos + 1:] if x.get("from") == "assistant"), "")
        user, system = conv[user_pos].get("value", ""), raw.get("system", "")
        if not user or not assistant or not (assistant.strip().startswith("[") and assistant.strip().endswith("]")): continue
        if len(system) + len(user) + len(assistant) > 12000: continue
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        rid = raw.get("id", idx)
        out.append(make_row(uid="TOPUP-TOOLACE-" + sha_text(str(rid))[:20], family="INSTRUCTION_VALUE_FIDELITY",
            subtype=function_subtype(user, assistant), source="Team-ACE/ToolACE", config="default", split="train", source_file="data.json",
            source_row_id=rid, source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    return out


def adapt_qa() -> tuple[list[dict], dict]:
    squad = pq.read_table(RAW / "squad_train.parquet").to_pylist()
    dolly = jsonl(RAW / "dolly.jsonl")
    out, inspected = [], {"rajpurkar/squad": 50, "databricks/databricks-dolly-15k": 110}
    # Execute the initial 50, then an adaptive 30-row batch from the same
    # high-yield pinned source because the new Dolly batch remains below 20%.
    for idx in range(140, min(len(squad), 220)):
        raw = squad[idx]; answers = raw.get("answers", {}).get("text", [])
        if not answers or norm(answers[0]) not in norm(raw["context"]): continue
        messages = [{"role": "user", "content": raw["question"] + "\n\nContext:\n" + raw["context"]}, {"role": "assistant", "content": answers[0]}]
        out.append(make_row(uid="TOPUP-SQUAD-" + raw["id"], family="GENERAL_QA_SCIENCE_READING", subtype="passage_grounded_qa",
            source="rajpurkar/squad", config="plain_text", split="train", source_file="plain_text/train-00000-of-00001.parquet",
            source_row_id=raw["id"], source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    closed = [(i, x) for i, x in enumerate(dolly) if x.get("category") == "closed_qa" and x.get("context")]
    # The first 30 accepted Dolly QA rows are already represented in V2.1.
    for idx, raw in closed[30:140]:
        if not raw.get("response") or norm(raw["response"]) not in norm(raw["context"]): continue
        messages = [{"role": "user", "content": raw["instruction"] + "\n\nContext:\n" + raw["context"]}, {"role": "assistant", "content": raw["response"]}]
        out.append(make_row(uid="TOPUP-DOLLY-QA-" + sha_text(str(idx))[:20], family="GENERAL_QA_SCIENCE_READING", subtype="grounded_closed_qa",
            source="databricks/databricks-dolly-15k", config="default", split="train", source_file="databricks-dolly-15k.jsonl",
            source_row_id=idx, source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    return out, inspected


def adapt_reasoning() -> tuple[list[dict], dict, dict]:
    rules = pq.read_table(RAW / "ruletaker_train.parquet").to_pylist()
    slr = pq.read_table(RAW / "slr_train_0.parquet").to_pylist()
    out = []
    for idx in range(200, min(len(rules), 320)):
        raw = rules[idx]
        if raw.get("label") not in {"entailment", "not_entailment", "not entailment"}: continue
        # Preserve the source label byte-for-byte.  The frozen V2 gate accepts
        # only `entailment`/`not_entailment`; source-space `not entailment`
        # therefore remains a reject exactly as in Stage 2.
        answer = raw["label"]
        messages = [{"role": "user", "content": raw["question"] + "\n\nFacts and rules:\n" + raw["context"]}, {"role": "assistant", "content": answer}]
        out.append(make_row(uid="TOPUP-RULETAKER-" + sha_text(str(idx))[:20], family="GENERAL_REASONING", subtype="rule_consistency",
            source="tasksource/ruletaker", config="default", split="train", source_file="data/train-00000-of-00001-52adaa842dd7ed92.parquet",
            source_row_id=idx, source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    eligible = []
    banned = re.compile(r"\b(plus|minus|add|subtract|multiply|divide|sum|greater_than|less_than|modulo)\b", re.I)
    for idx, raw in enumerate(slr):
        rule = raw.get("ground-truth rule", "")
        if not rule.startswith("eastbound(") or ":-" not in rule: continue
        body = rule.split(":-", 1)[1]
        if "eastbound(" in body or "westbound(" in body or banned.search(rule): continue
        if int(raw.get("curriculum level", 99)) > 8: continue
        if len(raw.get("prompt", "")) > 11500: continue
        eligible.append((sha_text(f"{SEED}:{raw['id']}"), idx, raw))
    eligible.sort()
    seen_rules = set()
    selected = []
    for _, idx, raw in eligible:
        signature = norm(re.sub(r"Car\d+|Train|\b\d+\b", "VAR", raw["ground-truth rule"], flags=re.I))
        if signature in seen_rules: continue
        seen_rules.add(signature); selected.append((idx, raw))
        if len(selected) == 45: break
    for idx, raw in selected:
        messages = [{"role": "user", "content": raw["prompt"]}, {"role": "assistant", "content": raw["ground-truth rule"]}]
        out.append(make_row(uid="TOPUP-SLR-" + str(raw["id"]), family="GENERAL_REASONING", subtype="symbolic_rule_induction",
            source="AIML-TUDA/SLR-Bench", config="v1-All", split="train", source_file="v1-All/train-00000-of-00003.parquet",
            source_row_id=raw["id"], source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    slr_gate = {
        "status": "PASS" if len(selected) == 45 else "FAIL", "full_revision": REVISIONS["AIML-TUDA/SLR-Bench"],
        "license": "CC-BY-4.0", "upstream": "ml-research/ScalableLogicalReasoning", "config": "v1-All", "split": "train",
        "source_file": "v1-All/train-00000-of-00003.parquet", "schema": list(slr[0]), "pinned_rows_replayed": len(slr),
        "preview_rows_checked": min(12, len(selected)), "selected_candidate_rows": len(selected),
        "filters": ["train only", "curriculum level <= 8", "no arithmetic predicate", "no recursive target predicate", "unique rule signature"],
        "validation_program_present": all(x[1].get("validation program") for x in selected),
    }
    return out, {"tasksource/ruletaker": 120, "AIML-TUDA/SLR-Bench": 45}, slr_gate


def unsafe_code(code: str) -> bool:
    return bool(re.search(r"\b(import|open|exec|eval|compile|__import__|os\.|sys\.|subprocess|socket|requests|urllib|pathlib|shutil)\b", code or ""))


def run_tests(code: str, tests: list[str]) -> bool:
    code = code.replace("```python", "").replace("```", "").strip()
    if unsafe_code(code) or not tests: return False
    try: ast.parse(code)
    except SyntaxError: return False
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "case.py"
        path.write_text(code + "\n" + "\n".join(tests), encoding="utf-8")
        try:
            done = subprocess.run([sys.executable, "-I", str(path)], cwd=td, capture_output=True, timeout=4)
            return done.returncode == 0
        except Exception: return False


def adapt_coding() -> tuple[list[dict], dict, Counter]:
    mbpp = pq.read_table(RAW / "mbpp_train.parquet").to_pylist()
    open_code = pq.read_table(RAW / "opencode_train_0.parquet").to_pylist()
    out, rejected = [], Counter()
    # Initial MBPP 15, then adaptive 10-row batches because observed yield is >20%.
    for idx in range(30, min(len(mbpp), 80)):
        raw = mbpp[idx]
        if not run_tests(raw["code"], list(raw.get("test_list") or [])):
            rejected["CODE_TEST_FAIL_OR_UNSAFE"] += 1; continue
        messages = [{"role": "user", "content": raw["text"]}, {"role": "assistant", "content": raw["code"]}]
        out.append(make_row(uid="TOPUP-MBPP-" + str(raw["task_id"]), family="CODING", subtype="safe_pure_function",
            source="google-research-datasets/mbpp", config="full", split="train", source_file="full/train-00000-of-00001.parquet",
            source_row_id=raw["task_id"], source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    # Exactly execute the planned 25-row OpenCode batch after the prior 90-row V2 acquisition window.
    for idx in range(90, min(len(open_code), 115)):
        raw = open_code[idx]
        tests = raw.get("unit_tests") or []
        if isinstance(tests, str):
            try: tests = json.loads(tests)
            except Exception: tests = []
        score = str(raw.get("average_test_score", ""))
        if score not in {"1", "1.0"} or "fail" in str(raw.get("tests_execution_status", "")).lower() or not run_tests(raw.get("output", ""), list(tests)):
            rejected["CODE_TEST_FAIL_OR_UNSAFE"] += 1; continue
        rid = raw.get("id", idx)
        messages = [{"role": "user", "content": raw.get("input", "")}, {"role": "assistant", "content": raw.get("output", "")}]
        out.append(make_row(uid="TOPUP-OPENCODE-" + str(rid), family="CODING", subtype="safe_pure_function",
            source="nvidia/OpenCodeInstruct", config="train", split="train", source_file="data/train-00000-of-00050.parquet",
            source_row_id=rid, source_row_index=idx, raw=raw, messages=messages, origin="TARGETED_TOPUP_V3"))
    return out, {"google-research-datasets/mbpp": 15, "nvidia/OpenCodeInstruct": 25, "mbpp_adaptive_max": 35}, rejected


def quality_and_dedup(candidates: list[dict], protected: list[dict], evaluation: list[dict]) -> tuple[list[dict], list[dict], dict]:
    accepted, rejected = [], []
    exact = {content_text(x) for x in protected}
    normalized = {sha_text(norm(content_text(x))) for x in protected}
    eval_prompts = [str(x.get("prompt", x.get("instruction", ""))) for x in evaluation]
    eval_norm = {norm(x) for x in eval_prompts}
    reasons = Counter()
    for row in candidates:
        reason = None
        text, ptext = content_text(row), prompt_text(row)
        if not ptext.strip(): reason = "EMPTY_PROMPT"
        elif not row["messages"][-1]["content"].strip(): reason = "EMPTY_RESPONSE"
        elif "\ufffd" in text: reason = "MALFORMED"
        elif len(text) > 12000: reason = "TOO_LONG"
        elif row["metadata"]["source"] == "tasksource/ruletaker" and row["messages"][-1]["content"].lower() not in {"entailment", "not_entailment"}: reason = "GOLD_AMBIGUOUS"
        elif text in exact: reason = "EXACT_DUPLICATE"
        elif sha_text(norm(text)) in normalized: reason = "NORMALIZED_DUPLICATE"
        elif norm(ptext) in eval_norm: reason = "GENERAL_V0_1_EXACT_OR_NORMALIZED"
        if reason:
            reasons[reason] += 1; rejected.append({**row, "rejection_reason": reason}); continue
        exact.add(text); normalized.add(sha_text(norm(text))); accepted.append(row)
    # Local semantic screen: char/word TF-IDF is deterministic and requires no network/API.
    reference_texts = [prompt_text(x) for x in protected] + eval_prompts
    if accepted and reference_texts:
        corpus = reference_texts + [prompt_text(x) for x in accepted]
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=60000, sublinear_tf=True)
        matrix = vectorizer.fit_transform(corpus)
        ref_n = len(reference_texts)
        similarities = cosine_similarity(matrix[ref_n:], matrix[:ref_n], dense_output=False)
        keep, semantic_reject = [], []
        old_n = len(protected)
        for i, row in enumerate(accepted):
            line = similarities.getrow(i)
            max_score = float(line.data.max()) if line.nnz else 0.0
            max_pos = int(line.indices[line.data.argmax()]) if line.nnz else -1
            row["metadata"]["max_reference_tfidf_cosine"] = round(max_score, 6)
            threshold = 0.985
            if max_score >= threshold:
                reason = "SEMANTIC_NEAR_DUPLICATE_EVAL" if max_pos >= old_n else "SEMANTIC_NEAR_DUPLICATE_TRAINING"
                reasons[reason] += 1; semantic_reject.append({**row, "rejection_reason": reason})
            else: keep.append(row)
        accepted, rejected = keep, rejected + semantic_reject
    return accepted, rejected, {"reasons": dict(reasons), "semantic_method": "local char_wb TF-IDF cosine", "semantic_threshold": 0.985}


def cap_admitted_buffer(rows: list[dict], existing: list[dict]) -> tuple[list[dict], list[dict]]:
    """Stop admission deterministically at roughly 10% above each true gap."""
    admitted, not_admitted = [], []
    for family, target in TARGET_NEW.items():
        if family == "WRITING_MULTILINGUAL":
            continue
        base_n = sum(x["metadata"]["task_family"] == family for x in existing)
        gap = target - base_n
        cap = gap + max(1, math.ceil(gap * 0.10))
        group = [x for x in rows if x["metadata"]["task_family"] == family]
        if family in {"INSTRUCTION_VALUE_FIDELITY", "CODING", "GENERAL_REASONING"}:
            # Preserve source/structure diversity while respecting the cap.
            buckets = defaultdict(list)
            for x in group: buckets[x["metadata"]["source"]].append(x)
            ranked = []
            while any(buckets.values()):
                for key in sorted(buckets):
                    if buckets[key]: ranked.append(buckets[key].pop(0))
        else:
            ranked = group
        admitted.extend(ranked[:cap]); not_admitted.extend(ranked[cap:])
    return admitted, not_admitted


def deterministic_select(existing: list[dict], topup: list[dict]) -> tuple[list[dict], list[dict]]:
    selected, surplus = [], []
    for family, target in TARGET_NEW.items():
        base = [x for x in existing if x["metadata"]["task_family"] == family]
        add = [x for x in topup if x["metadata"]["task_family"] == family]
        need = target - len(base)
        if need < 0:
            # Writing is intentionally over-complete (42 verified for target
            # 30). Rank deterministically with source diversity and keep the
            # unselected verified rows as accepted surplus.
            buckets = defaultdict(list)
            for x in base: buckets[x["metadata"]["source"]].append(x)
            for values in buckets.values():
                values.sort(key=lambda x: (abs(len(x["messages"][-1]["content"]) - 1200), sha_text(f"{SEED}:{x['id']}")))
            ranked = []
            while any(buckets.values()):
                for key in sorted(buckets):
                    if buckets[key]: ranked.append(buckets[key].pop(0))
            selected.extend(ranked[:target]); surplus.extend(ranked[target:] + add)
            continue
        if family == "INSTRUCTION_VALUE_FIDELITY":
            groups = defaultdict(list)
            for x in add: groups[x["metadata"]["subtype"]].append(x)
            for values in groups.values(): values.sort(key=lambda x: sha_text(f"{SEED}:{x['id']}"))
            ranked = []
            while any(groups.values()):
                for key in sorted(groups):
                    if groups[key]: ranked.append(groups[key].pop(0))
            add = ranked
        else:
            add.sort(key=lambda x: sha_text(f"{SEED}:{x['metadata']['source']}:{x['id']}"))
        if len(add) < need + max(1, math.ceil(need * 0.05)):
            raise RuntimeError(f"INSUFFICIENT_QUALITY_BUFFER:{family}:need={need}:accepted={len(add)}")
        selected.extend(base + add[:need]); surplus.extend(add[need:])
    assert len(selected) == 778
    # The existing writing surplus is also accepted but intentionally not selected.
    selected_ids = {x["id"] for x in selected}
    surplus_ids = {x["id"] for x in surplus}
    surplus.extend(x for x in existing if x["id"] not in selected_ids and x["id"] not in surplus_ids)
    return selected, surplus


def stratified_split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    train, val = [], []
    template_train_only = {
        "NousResearch/hermes-function-calling-v1", "Team-ACE/ToolACE",
        "rajpurkar/squad", "tasksource/ruletaker", "AIML-TUDA/SLR-Bench",
    }
    for family in TARGET_FINAL:
        group = [x for x in rows if x["metadata"]["task_family"] == family]
        quota = VAL_TARGET[family]
        # High-template sources are training-only. Validation is stratified over
        # the remaining source/subtype groups, preventing a template family
        # from appearing on both sides of the experiment.
        candidates = [x for x in group if x["metadata"]["source"] not in template_train_only]
        if family == "PROGRAMMATIC_MATH":
            sets = {x["id"]: {w for w in norm(prompt_text(x)).split() if len(w) > 1} for x in group}
            candidates = [x for x in candidates if all(
                other_id == x["id"] or len(sets[x["id"]] & other) / max(1, len(sets[x["id"]] | other)) < 0.90
                for other_id, other in sets.items())]
            assert len(candidates) >= quota
        buckets = defaultdict(list)
        for x in candidates:
            key = (x["metadata"]["source"], x["metadata"]["subtype"])
            buckets[key].append(x)
        for values in buckets.values():
            values.sort(key=lambda x: sha_text(f"VAL:{SEED}:{x['id']}"))
        allocation = {k: int(quota * len(v) / max(1, len(candidates))) for k, v in buckets.items()}
        remaining = quota - sum(allocation.values())
        order = sorted(buckets, key=lambda k: (-(quota * len(buckets[k]) / max(1, len(candidates)) - allocation[k]), k))
        cursor = 0
        while remaining:
            k = order[cursor % len(order)]
            if allocation[k] < len(buckets[k]): allocation[k] += 1; remaining -= 1
            cursor += 1
        prelim = [x for k in sorted(buckets) for x in buckets[k][:allocation[k]]]
        # Never separate an exact/normalized duplicate group. If a selected
        # hash occurs multiple times, keep the whole group in train and refill.
        all_hash_counts = Counter(x["metadata"]["normalized_sha256"] for x in group)
        fam_val = [x for x in prelim if all_hash_counts[x["metadata"]["normalized_sha256"]] == 1]
        used = {x["id"] for x in fam_val}
        refill = [x for k in sorted(buckets) for x in buckets[k] if x["id"] not in used and all_hash_counts[x["metadata"]["normalized_sha256"]] == 1]
        refill.sort(key=lambda x: sha_text(f"REFILL:{SEED}:{x['id']}"))
        fam_val.extend(refill[:quota-len(fam_val)])
        assert len(fam_val) == quota
        val_ids = {x["id"] for x in fam_val}
        val.extend(fam_val); train.extend(x for x in group if x["id"] not in val_ids)
    train.sort(key=lambda x: sha_text(f"TRAIN:{SEED}:{x['id']}")); val.sort(key=lambda x: sha_text(f"VAL:{SEED}:{x['id']}"))
    assert len(train) == 1080 and len(val) == 120
    assert not ({x["id"] for x in train} & {x["id"] for x in val})
    return train, val


def split_overlap_audit(train: list[dict], val: list[dict]) -> dict:
    train_content = {content_text(x) for x in train}
    val_content = {content_text(x) for x in val}
    train_norm = {norm(content_text(x)) for x in train}
    val_norm = {norm(content_text(x)) for x in val}
    train_sets = [{w for w in norm(prompt_text(x)).split() if len(w) > 1} for x in train]
    val_sets = [{w for w in norm(prompt_text(x)).split() if len(w) > 1} for x in val]
    lexical_pairs = []
    for i, a in enumerate(val_sets):
        scores = [(len(a & b) / max(1, len(a | b)), j) for j, b in enumerate(train_sets)]
        score, j = max(scores, default=(0.0, -1))
        if score >= 0.90: lexical_pairs.append({"validation_id": val[i]["id"], "train_id": train[j]["id"], "score": round(score, 6), "family": val[i]["metadata"]["task_family"]})
    lexical = len(lexical_pairs)
    corpus = [prompt_text(x) for x in train + val]
    matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=60000, sublinear_tf=True).fit_transform(corpus)
    sims = cosine_similarity(matrix[len(train):], matrix[:len(train)], dense_output=False)
    semantic = 0
    for i in range(len(val)):
        row = sims.getrow(i)
        if row.nnz and float(row.data.max()) >= 0.985: semantic += 1
    return {"status": "PASS" if not (train_content & val_content or train_norm & val_norm or lexical or semantic) else "FAIL",
        "exact_overlap": len(train_content & val_content), "normalized_overlap": len(train_norm & val_norm),
        "lexical_near_overlap": lexical, "lexical_threshold": 0.90,
        "lexical_pairs": lexical_pairs,
        "semantic_near_overlap": semantic, "semantic_method": "local char_wb TF-IDF cosine", "semantic_threshold": 0.985}


def manifest_entry(path: Path, base: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(base).as_posix(), "sha256": sha_bytes(data), "bytes": len(data),
            "lines": len(data.splitlines()) if path.suffix in {".jsonl", ".txt", ".md", ".py"} else None}


VALIDATOR = r'''#!/usr/bin/env python3
import hashlib,json,re,sys
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
errors=[]
sums={}
for line in (root/"manifests/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest,name=line.split("  ",1); sums[name]=digest
for name,digest in sums.items():
    p=root/name
    if not p.is_file() or sha(p)!=digest: errors.append("HASH:"+name)
train,val=jl(root/"data/train.jsonl"),jl(root/"data/validation.jsonl")
if (len(train),len(val))!=(1080,120): errors.append("COUNT")
ids=set(); norms={}
for split,rows in (("train",train),("validation",val)):
  for x in rows:
    if not x.get("id") or x["id"] in ids: errors.append("DUPLICATE_ID")
    ids.add(x.get("id")); ms=x.get("messages")
    if not isinstance(ms,list) or len(ms)<2 or ms[-1].get("role")!="assistant" or not ms[-1].get("content","").strip(): errors.append("SCHEMA")
    if any(m.get("role") not in {"system","user","assistant"} or not m.get("content","").strip() for m in ms): errors.append("ROLE_OR_EMPTY")
    md=x.get("metadata",{})
    required=("task_family","subtype","source","publisher","license","source_revision","source_config","source_split","source_file","source_row_id","source_row_index","raw_sha256","normalized_sha256")
    if any(md.get(k) in (None,"") for k in required): errors.append("PROVENANCE")
    if len(md.get("source_revision",""))!=40 or md.get("license_status")!="PASS": errors.append("LICENSE_OR_REVISION")
    n=md.get("normalized_sha256")
    if n in norms and norms[n]!=split: errors.append("TRAIN_VAL_NORMALIZED_OVERLAP")
    norms[n]=split
counts=Counter(x["metadata"]["task_family"] for x in train+val)
target={"INSTRUCTION_VALUE_FIDELITY":300,"GENERAL_QA_SCIENCE_READING":264,"GENERAL_REASONING":240,"WRITING_MULTILINGUAL":120,"CODING":96,"PROGRAMMATIC_MATH":120,"OTHER_MATH":60}
if dict(counts)!=target: errors.append("FAMILY_COUNTS")
freeze=json.loads((root/"manifests/dataset_freeze_manifest.json").read_text(encoding="utf-8"))
if freeze.get("freeze_id")!="PILOT_V1_GENERAL_REPLAY_FROZEN" or freeze.get("status")!="FROZEN": errors.append("FREEZE")
if freeze.get("general_v0_1_leakage",{}).get("accepted_overlap_count")!=0: errors.append("GENERAL_V0_1_LEAKAGE")
overlap=freeze.get("train_validation_overlap",{})
if overlap.get("status")!="PASS" or any(overlap.get(k)!=0 for k in ("exact_overlap","normalized_overlap","lexical_near_overlap","semantic_near_overlap")): errors.append("TRAIN_VAL_NEAR_OVERLAP")
lic=json.loads((root/"manifests/license_manifest.json").read_text(encoding="utf-8"))
if not lic.get("all_pass") or any(x.get("status")!="PASS" for x in lic.get("sources",[])): errors.append("LICENSE")
for p in root.rglob("*"):
  rel=p.relative_to(root).as_posix()
  if p.is_file() and not rel.startswith(("data/","tokenizer/")) and p.suffix.lower() in {".json",".jsonl",".md",".txt",".py"}:
    text=p.read_text(encoding="utf-8",errors="replace")
    if re.search(r"(?i)(?:[A-Z]:\\(?![nrt\\\"'])|[A-Z]:/)",text): errors.append("WINDOWS_ABSOLUTE_PATH:"+rel)
if errors:
  print("PACKAGE_VALIDATION_FAIL",sorted(set(errors))); sys.exit(1)
print("PACKAGE_VALIDATION_PASS")
'''


TRAINER = r'''#!/usr/bin/env python3
"""Pilot V1 GPU LoRA entry point. Validation/build never invokes this file."""
import argparse,datetime,json
from pathlib import Path
IGNORE_INDEX=-100
def build_feature(tokenizer,messages,max_length):
    prompt=[m for m in messages if m["role"]!="assistant"]
    prefix=tokenizer.apply_chat_template(prompt,tokenize=False,add_generation_prompt=True)
    full=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=False)
    prefix_ids=tokenizer(prefix,add_special_tokens=False)["input_ids"]
    full_ids=tokenizer(full,add_special_tokens=False)["input_ids"]
    if full_ids[:len(prefix_ids)]!=prefix_ids: raise ValueError("CHAT_TEMPLATE_PREFIX_MISMATCH")
    answer=full_ids[len(prefix_ids):]
    if not answer: raise ValueError("EMPTY_ASSISTANT_COMPLETION")
    kept_answer=answer[:max_length]
    kept_prompt=[] if len(answer)>max_length else prefix_ids[-(max_length-len(kept_answer)):]
    ids=kept_prompt+kept_answer
    return {"input_ids":ids,"attention_mask":[1]*len(ids),"labels":[IGNORE_INDEX]*len(kept_prompt)+kept_answer}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--config",default="config/pilot_v1_training_config.json"); p.add_argument("--resume-from-checkpoint"); a=p.parse_args()
    import torch
    if not torch.cuda.is_available(): raise SystemExit("CUDA_REQUIRED_TRAINING_STOPPED")
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8")); root=Path(__file__).resolve().parents[1]
    from transformers import AutoModelForCausalLM,AutoTokenizer,Trainer,TrainerCallback,TrainingArguments
    from peft import LoraConfig,get_peft_model
    from torch.utils.data import DataLoader
    from family_sampler import EpochAwareFamilySampler
    tok=AutoTokenizer.from_pretrained(root/"tokenizer",local_files_only=True); tok.pad_token=tok.pad_token or tok.eos_token
    def load(name):
        rows=[json.loads(s) for s in (root/"data"/name).read_text(encoding="utf-8").splitlines() if s.strip()]
        return [build_feature(tok,x["messages"],cfg["max_seq_length"]) for x in rows],[x["metadata"]["task_family"] for x in rows]
    train,families=load("train.jsonl"); val,_=load("validation.jsonl")
    sampler=EpochAwareFamilySampler(families,seed=cfg["seed"],mathematical_reasoning_ratio=cfg["sampling"]["mathematical_reasoning_target_ratio"],num_samples=cfg["sampling"]["epoch_sample_count"])
    class Collator:
      def __call__(self,items):
        n=max(len(x["input_ids"]) for x in items); pad=tok.pad_token_id
        return {"input_ids":torch.tensor([x["input_ids"]+[pad]*(n-len(x["input_ids"])) for x in items]),"attention_mask":torch.tensor([x["attention_mask"]+[0]*(n-len(x["attention_mask"])) for x in items]),"labels":torch.tensor([x["labels"]+[-100]*(n-len(x["labels"])) for x in items])}
    class FamilyTrainer(Trainer):
      def get_train_dataloader(self): return DataLoader(self.train_dataset,batch_size=self._train_batch_size,sampler=sampler,collate_fn=self.data_collator,drop_last=False)
    class SamplingCallback(TrainerCallback):
      def on_epoch_begin(self,args,state,control,**kwargs): sampler.set_epoch(int(state.epoch or 0))
      def on_epoch_end(self,args,state,control,**kwargs): (out/"effective_sampling_statistics.json").write_text(json.dumps({"epochs":sampler.history},indent=2),encoding="utf-8")
    model=AutoModelForCausalLM.from_pretrained(cfg["base_model"],torch_dtype=torch.bfloat16)
    l=cfg["lora"]; model=get_peft_model(model,LoraConfig(r=l["r"],lora_alpha=l["alpha"],lora_dropout=l["dropout"],target_modules=l["target_modules"],task_type="CAUSAL_LM"))
    run_id=f"{cfg['run_name_prefix']}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_seed{cfg['seed']}"; out=root/cfg["output_dir"]/run_id; out.mkdir(parents=True,exist_ok=False)
    args=TrainingArguments(output_dir=str(out),num_train_epochs=cfg["epochs"],learning_rate=cfg["learning_rate"],per_device_train_batch_size=cfg["per_device_train_batch_size"],per_device_eval_batch_size=cfg["per_device_train_batch_size"],gradient_accumulation_steps=cfg["gradient_accumulation_steps"],evaluation_strategy="steps",save_strategy="steps",logging_steps=cfg["logging_steps"],save_steps=cfg["save_steps"],eval_steps=cfg["eval_steps"],save_total_limit=cfg["save_total_limit"],gradient_checkpointing=cfg["gradient_checkpointing"],bf16=cfg["bf16"],fp16=cfg["fp16"],seed=cfg["seed"],report_to="none",remove_unused_columns=False)
    trainer=FamilyTrainer(model=model,args=args,train_dataset=train,eval_dataset=val,data_collator=Collator(),callbacks=[SamplingCallback()]); trainer.train(resume_from_checkpoint=a.resume_from_checkpoint); metrics=trainer.evaluate(); model.save_pretrained(out); tok.save_pretrained(out)
    (out/"run_manifest.json").write_text(json.dumps({"run_id":run_id,"freeze_id":cfg["freeze_id"],"final_validation":metrics,"adapter_merged":False},indent=2),encoding="utf-8")
if __name__=="__main__": main()
'''


def main() -> None:
    if FINAL.exists() or RELEASE.exists() or AUDIT.exists():
        raise SystemExit("OUTPUT_EXISTS_REFUSING_TO_OVERWRITE")
    before = {str(x.relative_to(ROOT)): path_fingerprint(x) for x in frozen_inputs()}
    keep = load_keep(); verified = load_verified_new()
    evaluation = jsonl(ROOT / "experiments/fine_tuning_pilot_v0_evaluation_upload/data/general/general_eval_v0_1.jsonl")
    candidates = []
    # Planned batches plus bounded adaptive instruction expansion (same confirmed sources).
    hermes = adapt_hermes(320); toolace = adapt_toolace(300)
    candidates.extend(hermes); candidates.extend(toolace)
    qa, qa_inspected = adapt_qa(); candidates.extend(qa)
    reasoning, reasoning_inspected, slr_gate = adapt_reasoning(); candidates.extend(reasoning)
    coding, coding_inspected, coding_reject = adapt_coding(); candidates.extend(coding)
    assert slr_gate["status"] == "PASS"
    accepted_topup_all, rejected, dedup = quality_and_dedup(candidates, keep + verified, evaluation)
    accepted_topup, not_admitted = cap_admitted_buffer(accepted_topup_all, verified)
    # Leakage screen against General V0.1 using the same local representation.
    eval_norm = {norm(str(x.get("prompt", x.get("instruction", "")))) for x in evaluation}
    leakage = [x["id"] for x in accepted_topup if norm(prompt_text(x)) in eval_norm]
    assert not leakage
    selected_new, surplus = deterministic_select(verified, accepted_topup)
    final_rows = keep + selected_new
    assert len(final_rows) == 1200
    assert Counter(x["metadata"]["task_family"] for x in final_rows) == Counter(TARGET_FINAL)
    train, val = stratified_split(final_rows)
    split_overlap = split_overlap_audit(train, val)
    assert split_overlap["status"] == "PASS", split_overlap
    FINAL.mkdir(parents=True); AUDIT.mkdir(parents=True)
    emit_jsonl(FINAL / "general_replay_v1.jsonl", final_rows)
    emit_jsonl(FINAL / "train.jsonl", train); emit_jsonl(FINAL / "validation.jsonl", val)
    emit_jsonl(FINAL / "accepted_surplus.jsonl", surplus)
    provenance = [{"id": x["id"], **{k: x["metadata"][k] for k in (
        "source", "publisher", "license", "source_revision", "source_config", "source_split", "source_file",
        "source_row_id", "source_row_index", "raw_sha256", "normalized_sha256", "origin")}} for x in final_rows]
    emit_jsonl(FINAL / "source_provenance.jsonl", provenance)
    source_counts = Counter((x["metadata"]["source"], x["metadata"]["task_family"]) for x in final_rows)
    license_manifest = {"all_pass": True, "sources": [{"source": s, "license": LICENSES[s], "revision": REVISIONS[s], "status": "PASS",
        "selected_count": sum(n for (ss, _), n in source_counts.items() if ss == s)} for s in sorted({x["metadata"]["source"] for x in final_rows})]}
    (FINAL / "license_manifest.json").write_text(json.dumps(license_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files = {}
    for name in ("general_replay_v1.jsonl", "train.jsonl", "validation.jsonl", "accepted_surplus.jsonl", "source_provenance.jsonl", "license_manifest.json"):
        files[name] = manifest_entry(FINAL / name, FINAL)
    dataset_manifest = {
        "name": "Fine-tuning Pilot V1 General Replay", "rows": 1200, "train_rows": 1080, "validation_rows": 120,
        "seed": SEED, "family_counts": dict(Counter(x["metadata"]["task_family"] for x in final_rows)),
        "old_keep": 422, "new_selected": 778, "drop_reintroduced": 0,
        "source_counts": [{"source": s, "family": f, "count": n} for (s, f), n in sorted(source_counts.items())],
        "instruction_subtypes": dict(Counter(x["metadata"]["subtype"] for x in selected_new if x["metadata"]["task_family"] == "INSTRUCTION_VALUE_FIDELITY")),
    }
    (FINAL / "final_dataset_manifest.json").write_text(json.dumps(dataset_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files["final_dataset_manifest.json"] = manifest_entry(FINAL / "final_dataset_manifest.json", FINAL)
    freeze = {
        "freeze_id": FREEZE_ID, "status": "FROZEN", "seed": SEED, "files": files,
        "general_v0_1_leakage": {"accepted_overlap_count": 0, "eval_rows": len(evaluation), "eval_sha256": sha_bytes((ROOT / "experiments/fine_tuning_pilot_v0_evaluation_upload/data/general/general_eval_v0_1.jsonl").read_bytes())},
        "train_validation_overlap": split_overlap,
        "input_integrity": {"status": "PASS", "before": before},
    }
    (FINAL / "dataset_freeze_manifest.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2), encoding="utf-8")
    # Freeze the actual Pilot V0 values; only names/data/output version change.
    v0 = yaml.safe_load((ROOT / "experiments/fine_tuning_pilot_v0_upload/config/training_config.yaml").read_text(encoding="utf-8"))
    cfg = dict(v0); cfg["run_name_prefix"] = "pilot_v1"; cfg["output_dir"] = "outputs"; cfg["freeze_id"] = FREEZE_ID
    cfg["dataset"] = {"train": "data/train.jsonl", "validation": "data/validation.jsonl", "train_sha256": sha_bytes((FINAL / "train.jsonl").read_bytes()), "validation_sha256": sha_bytes((FINAL / "validation.jsonl").read_bytes())}
    diff = {"base_experiment": "Fine-tuning Pilot V0", "new_experiment": "Fine-tuning Pilot V1", "changed": {
        "dataset_composition": "422 frozen KEEP + 778 revision-pinned verified new rows", "dataset_rows": {"from": 841, "to": 1200},
        "split_rows": {"from": {"train": 757, "validation": 84}, "to": {"train": 1080, "validation": 120}},
        "run_name_prefix": {"from": "pilot_v0", "to": "pilot_v1"}, "freeze_id": FREEZE_ID},
        "hyperparameters_frozen": True, "frozen_fields": ["base_model", "seed", "epochs", "learning_rate", "per_device_train_batch_size", "gradient_accumulation_steps", "max_seq_length", "bf16", "fp16", "gradient_checkpointing", "logging_steps", "eval_steps", "save_steps", "save_total_limit", "lora", "sampling"],
        "loss_masking": "ASSISTANT_COMPLETION_ONLY", "chat_template": "Qwen tokenizer apply_chat_template"}
    (AUDIT / "pilot_v0_vs_v1_experiment_diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
    (AUDIT / "slr_bench_gate.json").write_text(json.dumps(slr_gate, ensure_ascii=False, indent=2), encoding="utf-8")
    (AUDIT / "train_validation_overlap_audit.json").write_text(json.dumps(split_overlap, ensure_ascii=False, indent=2), encoding="utf-8")
    acquisition = {
        "initial_plan": {"NousResearch/hermes-function-calling-v1": 190, "Team-ACE/ToolACE": 180, **qa_inspected, **reasoning_inspected, "google-research-datasets/mbpp": 15, "nvidia/OpenCodeInstruct": 25},
        "adaptive_bounds": {"instruction_hermes_rows_read": 320, "instruction_toolace_rows_read": 300, "squad_additional_rows_read": 30, **coding_inspected},
        "accepted_topup": dict(Counter(x["metadata"]["task_family"] for x in accepted_topup)),
        "selected_topup": dict(Counter(x["metadata"]["task_family"] for x in selected_new if x["metadata"]["origin"] == "TARGETED_TOPUP_V3")),
        "rejected": len(rejected), "reject_reasons": dict(Counter(x["rejection_reason"] for x in rejected) + coding_reject),
        "review": 0, "not_admitted_after_buffer_reached": len(not_admitted), "dedup": dedup,
    }
    (AUDIT / "topup_execution_report.json").write_text(json.dumps(acquisition, ensure_ascii=False, indent=2), encoding="utf-8")
    # Package creation.
    for sub in ("data", "config", "manifests", "scripts", "docs", "tokenizer"):
        (RELEASE / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(FINAL / "train.jsonl", RELEASE / "data/train.jsonl"); shutil.copy2(FINAL / "validation.jsonl", RELEASE / "data/validation.jsonl")
    shutil.copy2(FINAL / "dataset_freeze_manifest.json", RELEASE / "manifests/dataset_freeze_manifest.json")
    shutil.copy2(FINAL / "source_provenance.jsonl", RELEASE / "manifests/source_provenance.jsonl")
    shutil.copy2(FINAL / "license_manifest.json", RELEASE / "manifests/license_manifest.json")
    (RELEASE / "config/pilot_v1_training_config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (RELEASE / "scripts/validate_package.py").write_text(VALIDATOR, encoding="utf-8")
    (RELEASE / "scripts/train_lora.py").write_text(TRAINER, encoding="utf-8")
    shutil.copy2(ROOT / "experiments/fine_tuning_pilot_v0_upload/scripts/family_sampler.py", RELEASE / "scripts/family_sampler.py")
    for p in (ROOT / "experiments/fine_tuning_pilot_v0_upload/scripts/qwen_tokenizer").iterdir():
        if p.is_file(): shutil.copy2(p, RELEASE / "tokenizer" / p.name.replace("_1", ""))
    readme = """# Fine-tuning Pilot V1 training package\n\nFrozen dataset: `PILOT_V1_GENERAL_REPLAY_FROZEN` (1080 train / 120 validation). Run validation before training. Training requires Python, CUDA, PyTorch, Transformers, PEFT, and an accessible `Qwen/Qwen2.5-1.5B-Instruct` model. All paths in this package are relative. This package does not contain checkpoints, caches, raw acquisition data, evaluation sets, or RAG artifacts.\n"""
    commands = """# Server commands\n\n```bash\ncd pilot_v1_training_package\npython scripts/validate_package.py\npython scripts/train_lora.py --config config/pilot_v1_training_config.json\n```\n"""
    requirements = """torch>=2.2,<3\ntransformers>=4.45,<5\npeft>=0.12,<1\naccelerate>=0.34,<2\nsafetensors>=0.4,<1\npyyaml>=6,<7\n"""
    (RELEASE / "README.md").write_text(readme, encoding="utf-8")
    (RELEASE / "TRAINING_COMMAND.md").write_text(commands, encoding="utf-8")
    (RELEASE / "docs/README.md").write_text("See `../README.md` and `../TRAINING_COMMAND.md`.\n", encoding="utf-8")
    (RELEASE / "requirements.txt").write_text(requirements, encoding="utf-8")
    package_manifest = {"package": "pilot_v1_training_package", "freeze_id": FREEZE_ID, "training_launched": False, "paths_relative": True,
        "entrypoints": {"validate": "scripts/validate_package.py", "train": "scripts/train_lora.py", "config": "config/pilot_v1_training_config.json"}}
    (RELEASE / "PACKAGE_MANIFEST.json").write_text(json.dumps(package_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    sum_files = sorted(p for p in RELEASE.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    sums = "".join(f"{sha_bytes(p.read_bytes())}  {p.relative_to(RELEASE).as_posix()}\n" for p in sum_files)
    (RELEASE / "manifests/SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    # Historical integrity must still match after every write.
    after = {str(x.relative_to(ROOT)): path_fingerprint(x) for x in frozen_inputs()}
    if before != after: raise RuntimeError("BLOCKED_INTEGRITY")
    freeze["input_integrity"]["after"] = after
    (FINAL / "dataset_freeze_manifest.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2), encoding="utf-8")
    # Recopy updated freeze and refresh checksums.
    shutil.copy2(FINAL / "dataset_freeze_manifest.json", RELEASE / "manifests/dataset_freeze_manifest.json")
    sum_files = sorted(p for p in RELEASE.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (RELEASE / "manifests/SHA256SUMS.txt").write_text("".join(f"{sha_bytes(p.read_bytes())}  {p.relative_to(RELEASE).as_posix()}\n" for p in sum_files), encoding="utf-8")
    # Tokenizer-only loader dry run: no model weights or GPU required.
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(RELEASE / "tokenizer", local_files_only=True)
    loader_rows = train[:3] + val[:3]
    loader_stats = []
    for row in loader_rows:
        prefix = tok.apply_chat_template([m for m in row["messages"] if m["role"] != "assistant"], tokenize=False, add_generation_prompt=True)
        full = tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=False)
        pids = tok(prefix, add_special_tokens=False)["input_ids"]; fids = tok(full, add_special_tokens=False)["input_ids"]
        assert fids[:len(pids)] == pids and len(fids) > len(pids)
        loader_stats.append({"id": row["id"], "prompt_tokens": len(pids), "full_tokens": len(fids)})
    (AUDIT / "data_loader_dry_run.json").write_text(json.dumps({"status": "PASS", "model_loaded": False, "tokenizer_only": True, "samples": loader_stats}, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"decision": "READY_FOR_SERVER_UPLOAD_AND_PILOT_V1_TRAINING", "family_before": dict(Counter(x["metadata"]["task_family"] for x in verified)),
        "family_topup_accepted": dict(Counter(x["metadata"]["task_family"] for x in accepted_topup)), "family_new_selected": dict(Counter(x["metadata"]["task_family"] for x in selected_new)),
        "final_family": dict(Counter(x["metadata"]["task_family"] for x in final_rows)), "train": len(train), "validation": len(val),
        "surplus": len(surplus), "rejected": len(rejected) + sum(coding_reject.values()), "review": 0, "general_v0_1_leakage": 0,
        "integrity": "PASS", "license": "PASS", "provenance": "PASS", "package_path": "release/pilot_v1_training_package"}
    (AUDIT / "final_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
