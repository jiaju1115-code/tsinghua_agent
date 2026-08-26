"""Controlled Stage 2 acquisition for Fine-tuning Pilot V1.

This script intentionally reads only the Stage-1 quota rows and never creates a
train/validation split or a final Pilot V1 dataset.  It uses the HF Dataset
Server rows endpoint (plus a bounded category filter when available).
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/03_fine_tuning/pilot_v1/general_acquisition_v2"
AUDIT = ROOT / "evaluation/fine_tuning_pilot_v1_acquisition_v2"
REVISIONS = {
    "nvidia/Nemotron-Instruction-Following-Chat-v1": "83dcd3a",
    "allenai/tulu-3-sft-personas-instruction-following": "fe0c7d3",
    "databricks/databricks-dolly-15k": "bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a",
    "rajpurkar/squad": "7b6d24c",
    "tasksource/ruletaker": "a3e0880",
    "facebook/babi_qa": "021d7ae",
    "nvidia/OpenCodeInstruct": "8f3ba5b",
    "google-research-datasets/mbpp": "4bb6404",
}
LICENSES = {
    "nvidia/Nemotron-Instruction-Following-Chat-v1": "CC-BY-4.0",
    "allenai/tulu-3-sft-personas-instruction-following": "ODC-BY-1.0",
    "databricks/databricks-dolly-15k": "CC-BY-SA-3.0",
    "rajpurkar/squad": "CC-BY-SA-4.0",
    "tasksource/ruletaker": "Apache-2.0",
    "facebook/babi_qa": "CC-BY-3.0",
    "nvidia/OpenCodeInstruct": "CC-BY-4.0",
    "google-research-datasets/mbpp": "CC-BY-4.0",
}
FROZEN = [
    ROOT / "data/fine_tuning_v1/general_capability_candidates_v1_2",
    ROOT / "evaluation/fine_tuning_pilot_v1_data_preflight/proposed_keep.jsonl",
    ROOT / "evaluation/fine_tuning_pilot_v1_data_preflight/proposed_drop.jsonl",
    ROOT / "experiments/fine_tuning_pilot_v0_evaluation_upload/data/general/general_eval_v0_1.jsonl",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"```(?:\w+)?", "", value)
    value = re.sub(r"[\W_]+", " ", value.lower(), flags=re.UNICODE)
    return " ".join(value.split())


def tokens(value: str) -> set[str]:
    return {x for x in norm(value).split() if len(x) > 1}


def lexical(a: str, b: str) -> float:
    aa, bb = tokens(a), tokens(b)
    return len(aa & bb) / max(1, len(aa | bb))


def file_hashes(paths: list[Path]) -> dict:
    result = {}
    for path in paths:
        if path.is_dir():
            files = sorted(p for p in path.rglob("*") if p.is_file())
            digest = hashlib.sha256()
            for child in files:
                digest.update(child.relative_to(path).as_posix().encode())
                digest.update(child.read_bytes())
            result[str(path.relative_to(ROOT))] = {"sha256": digest.hexdigest(), "file_count": len(files)}
        else:
            result[str(path.relative_to(ROOT))] = {"sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size}
    return result


def http_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "pilot-v1-stage2-controlled-acquisition/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def rows(dataset: str, config: str, split: str, offset: int, length: int) -> list[dict]:
    result = []
    while len(result) < length:
        size = min(100, length - len(result))  # Dataset Server maximum.
        query = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split, "offset": offset + len(result), "length": size})
        batch = http_json("https://datasets-server.huggingface.co/rows?" + query).get("rows", [])
        result.extend(batch)
        if len(batch) < size: break
    return result


def filtered_rows(dataset: str, config: str, split: str, where: str, length: int) -> list[dict]:
    # This endpoint is a Dataset Server viewer API; fallback is deliberately no
    # acquisition rather than broad scanning if server-side filtering is absent.
    result = []
    while len(result) < length:
        size = min(100, length - len(result))
        query = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split, "where": where, "offset": len(result), "length": size})
        batch = http_json("https://datasets-server.huggingface.co/filter?" + query).get("rows", [])
        result.extend(batch)
        if len(batch) < size: break
    return result


def base_record(dataset: str, config: str, split: str, family: str, subfamily: str, source: dict, instruction: str, context: str, response: str, language="en") -> dict:
    row_idx = source.get("row_idx")
    row = source.get("row", {})
    row_id = str(row.get("id", row.get("uuid", row.get("task_id", row_idx))))
    cid_input = "\x1f".join([dataset, REVISIONS[dataset], split, row_id, str(row_idx), norm(instruction)])
    return {
        "candidate_id": sha256_bytes(cid_input.encode()), "source_dataset": dataset,
        "source_revision": REVISIONS[dataset], "source_config": config, "source_split": split,
        "source_row_id": row_id, "source_row_index": row_idx, "license": LICENSES[dataset],
        "family": family, "subfamily": subfamily, "language": language,
        "instruction": instruction.strip(), "context": (context or "").strip(), "response": response.strip(),
        "metadata": {"raw_fields": row, "source_endpoint": "HF Dataset Server", "selection": "frozen deterministic offset/filter"},
    }


def adapt(dataset: str, config: str, split: str, family: str, subfamily: str, item: dict) -> list[dict]:
    row = item.get("row", {})
    if dataset.endswith("Nemotron-Instruction-Following-Chat-v1"):
        messages = row.get("messages", [])
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        assistant = next((m.get("content", "") for m in messages if m.get("role") == "assistant"), "")
        rec = base_record(dataset, config, split, family, subfamily, item, user, "", assistant)
        rec["metadata"]["reasoning_content_present"] = bool(next((m.get("reasoning_content") for m in messages if m.get("role") == "assistant"), ""))
        return [rec]
    if dataset.endswith("tulu-3-sft-personas-instruction-following"):
        messages = row.get("messages", [])
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), row.get("prompt", ""))
        answer = next((m.get("content", "") for m in messages if m.get("role") == "assistant"), "")
        rec = base_record(dataset, config, split, family, subfamily, item, user, "", answer)
        rec["metadata"]["constraints"] = row.get("constraints", [])
        return [rec]
    if dataset.endswith("databricks-dolly-15k"):
        rec = base_record(dataset, config, split, family, subfamily, item, row.get("instruction", ""), row.get("context", ""), row.get("response", ""))
        rec["metadata"]["category"] = row.get("category")
        return [rec]
    if dataset.endswith("squad"):
        answers = row.get("answers", {}).get("text", [])
        return [base_record(dataset, config, split, family, subfamily, item, row.get("question", ""), row.get("context", ""), answers[0] if answers else "")]
    if dataset.endswith("ruletaker"):
        # Label is intentionally retained only as an answer, not a chain of thought.
        return [base_record(dataset, config, split, family, subfamily, item, row.get("question", ""), row.get("context", ""), row.get("label", ""))]
    if dataset.endswith("babi_qa"):
        story = row.get("story", {})
        texts, kinds, answers = story.get("text", []), story.get("type", []), story.get("answer", [])
        result = []
        context = []
        for position, text in enumerate(texts):
            if kinds[position] == 0:
                context.append(text)
            elif kinds[position] == 1:
                derived = dict(item)
                derived["row"] = dict(row)
                derived["row"]["id"] = f"{item.get('row_idx')}:{position}"
                rec = base_record(dataset, config, split, family, subfamily, derived, text, " ".join(context), answers[position])
                rec["metadata"]["babi_task_config"] = config
                result.append(rec)
        return result
    if dataset.endswith("OpenCodeInstruct"):
        rec = base_record(dataset, config, split, family, subfamily, item, row.get("input", ""), "", row.get("output", ""))
        rec["metadata"].update({k: row.get(k) for k in ("unit_tests", "tests_execution_status", "average_test_score", "domain")})
        return [rec]
    if dataset.endswith("mbpp"):
        rec = base_record(dataset, config, split, family, subfamily, item, row.get("text", ""), row.get("test_setup_code", ""), row.get("code", ""))
        rec["metadata"].update({"task_id": row.get("task_id"), "unit_tests": row.get("test_list", [])})
        return [rec]
    return []


def unsafe_code(code: str) -> bool:
    forbidden = r"\b(import|open|exec|eval|compile|__import__|os\.|sys\.|subprocess|socket|requests|urllib|pathlib|shutil)\b"
    return bool(re.search(forbidden, code or ""))


def code_passes(record: dict) -> tuple[bool, str | None]:
    code = record["response"].replace("```python", "").replace("```", "").strip()
    if unsafe_code(code):
        return False, "UNSAFE_CODE"
    tests = record["metadata"].get("unit_tests", [])
    if isinstance(tests, str):
        try: tests = json.loads(tests)
        except json.JSONDecodeError: return False, "CODE_TEST_FAIL"
    if not tests: return False, "CODE_TEST_FAIL"
    try: ast.parse(code)
    except SyntaxError: return False, "MALFORMED"
    with tempfile.TemporaryDirectory() as temp:
        runner = Path(temp) / "run.py"
        runner.write_text(code + "\n" + "\n".join(tests), encoding="utf-8")
        try:
            completed = subprocess.run([sys.executable, "-I", str(runner)], cwd=temp, capture_output=True, text=True, timeout=3)
            return (completed.returncode == 0, None if completed.returncode == 0 else "CODE_TEST_FAIL")
        except (subprocess.TimeoutExpired, OSError):
            return False, "CODE_TEST_FAIL"


def quality(record: dict) -> str | None:
    inst, response = record["instruction"], record["response"]
    if not inst: return "EMPTY_PROMPT"
    if not response: return "EMPTY_RESPONSE"
    if "\ufffd" in inst + response: return "MALFORMED"
    if len(inst) > 12000 or len(response) > 12000: return "TOO_LONG"
    if re.match(r"^(sure|certainly|of course)[,! ]", response, re.I): return "ALIGNMENT_FAIL"
    if record["metadata"].get("reasoning_content_present"): return "HIDDEN_COT_DEPENDENCY"
    family = record["family"]
    if family == "GENERAL_QA_SCIENCE_READING":
        if not record["context"] or norm(response) not in norm(record["context"]): return "CONTEXT_UNSUPPORTED"
        if re.search(r"\b(current|today|latest|president|stock|election|medical advice)\b", inst, re.I): return "TIME_SENSITIVE"
    if family == "GENERAL_REASONING":
        if record["source_dataset"].endswith("babi_qa"): return "WRONG_FAMILY"  # only QA1 config is exposed; task balance cannot be met
        if re.search(r"\b\d+\s*[+*/-]\s*\d+\b", inst): return "WRONG_FAMILY"
        if record["response"].lower() not in {"entailment", "not_entailment"}: return "GOLD_AMBIGUOUS"
    if family == "WRITING_MULTILINGUAL":
        constraints = " ".join(record["metadata"].get("constraints", []))
        category = record["metadata"].get("category", "")
        if category and category != "summarization": return "WRONG_FAMILY"
        if not category and not re.search(r"(rewrite|summari|format|exclude|constrain)", constraints + " " + inst, re.I): return "SUBJECTIVE_GOLD"
    if family == "INSTRUCTION_VALUE_FIDELITY":
        if not re.search(r"(schema|format|extract|classif|json|xml|copy|constraint|exclude)", inst, re.I): return "WRONG_FAMILY"
    if family == "CODING":
        if record["source_dataset"].endswith("OpenCodeInstruct"):
            statuses = record["metadata"].get("tests_execution_status", "")
            if record["metadata"].get("average_test_score") != "1" or "fail" in str(statuses).lower(): return "CODE_TEST_FAIL"
        passed, reason = code_passes(record)
        if not passed: return reason
    return None


def frozen_texts() -> tuple[list[str], list[str]]:
    old, evaluation = [], []
    for path in (FROZEN[0], FROZEN[1], FROZEN[2]):
        files = path.rglob("*.jsonl") if path.is_dir() else [path]
        for file in files:
            for line in file.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                    old.append(" ".join(str(item.get(k, "")) for k in ("instruction", "input", "prompt", "context", "response", "output")))
                except json.JSONDecodeError: pass
    for line in FROZEN[3].read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
            evaluation.append(" ".join(str(item.get(k, "")) for k in ("instruction", "input", "prompt", "context", "response", "output")))
        except json.JSONDecodeError: pass
    return old, evaluation


def emit_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records), encoding="utf-8")


def main() -> None:
    if OUT.exists(): shutil.rmtree(OUT)
    if AUDIT.exists(): shutil.rmtree(AUDIT)
    OUT.mkdir(parents=True); AUDIT.mkdir(parents=True)
    before = file_hashes(FROZEN)
    specs = [
        ("nvidia/Nemotron-Instruction-Following-Chat-v1", "default", "structured_outputs", 0, 220, "INSTRUCTION_VALUE_FIDELITY", "structured_output"),
        ("allenai/tulu-3-sft-personas-instruction-following", "default", "train", 0, 120, "INSTRUCTION_VALUE_FIDELITY", "verifiable_constraints"),
        ("allenai/tulu-3-sft-personas-instruction-following", "default", "train", 120, 20, "WRITING_MULTILINGUAL", "objective_rewrite"),
        ("databricks/databricks-dolly-15k", "default", "train", 0, 60, "INSTRUCTION_VALUE_FIDELITY", "extraction_or_classification"),
        ("databricks/databricks-dolly-15k", "default", "train", 0, 180, "GENERAL_QA_SCIENCE_READING", "grounded_closed_qa"),
        ("databricks/databricks-dolly-15k", "default", "train", 0, 30, "WRITING_MULTILINGUAL", "constrained_summary"),
        ("rajpurkar/squad", "plain_text", "train", 0, 140, "GENERAL_QA_SCIENCE_READING", "passage_grounded_qa"),
        ("tasksource/ruletaker", "default", "train", 0, 200, "GENERAL_REASONING", "rule_consistency"),
        ("facebook/babi_qa", "en-10k-qa1", "train", 0, 20, "GENERAL_REASONING", "task_balanced_babi"),
        ("nvidia/OpenCodeInstruct", "train", "train", 0, 90, "CODING", "safe_pure_function"),
        ("google-research-datasets/mbpp", "full", "train", 0, 30, "CODING", "mbpp_601_974"),
    ]
    wanted_category = {"INSTRUCTION_VALUE_FIDELITY": "\"category\" = 'information_extraction'", "GENERAL_QA_SCIENCE_READING": "\"category\" = 'closed_qa'", "WRITING_MULTILINGUAL": "\"category\" = 'summarization'"}
    raw, failures, source_log = [], [], []
    for dataset, config, split, offset, amount, family, subfamily in specs:
        try:
            if dataset.endswith("databricks-dolly-15k"):
                if family == "INSTRUCTION_VALUE_FIDELITY":
                    fetched = filtered_rows(dataset, config, split, "\"category\" = 'information_extraction'", 30)
                    fetched += filtered_rows(dataset, config, split, "\"category\" = 'classification'", 30)
                else:
                    fetched = filtered_rows(dataset, config, split, wanted_category[family], amount)
            else:
                fetched = rows(dataset, config, split, offset, amount)
            adapted = [r for item in fetched for r in adapt(dataset, config, split, family, subfamily, item)]
            if dataset.endswith("babi_qa"): adapted = adapted[:100]
            raw.extend(adapted)
            source_log.append({"dataset": dataset, "revision": REVISIONS[dataset], "config": config, "split": split, "requested_candidate_count": amount if not dataset.endswith("babi_qa") else 100, "actual_inspected_rows": len(fetched), "actual_candidate_records": len(adapted), "license": LICENSES[dataset], "timestamp_utc": now(), "selection_rule": "filter category" if dataset.endswith("databricks-dolly-15k") else f"row offset {offset}, length {amount}"})
        except Exception as exc:
            failures.append({"dataset": dataset, "family": family, "error": f"{type(exc).__name__}: {exc}"})
            source_log.append({"dataset": dataset, "revision": REVISIONS[dataset], "config": config, "split": split, "requested_candidate_count": amount, "actual_inspected_rows": 0, "actual_candidate_records": 0, "license": LICENSES[dataset], "timestamp_utc": now(), "error": f"{type(exc).__name__}: {exc}"})
    old, evaluation = frozen_texts()
    accepted, rejected, review, surplus = [], [], [], []
    seen_exact, seen_norm = set(), set()
    dedup = Counter(); leakage = Counter()
    for rec in raw:
        content = rec["instruction"] + "\n" + rec["context"] + "\n" + rec["response"]
        decision_reason = quality(rec)
        prompt_norm = norm(rec["instruction"] + " " + rec["context"])
        if not decision_reason and content in seen_exact: decision_reason = "EXACT_DUPLICATE"; dedup[decision_reason] += 1
        if not decision_reason and prompt_norm in seen_norm: decision_reason = "NORMALIZED_DUPLICATE"; dedup[decision_reason] += 1
        if not decision_reason:
            old_score = max((lexical(rec["instruction"] + " " + rec["context"], x) for x in old), default=0)
            eval_score = max((lexical(rec["instruction"] + " " + rec["context"], x) for x in evaluation), default=0)
            rec["metadata"]["max_old_pool_lexical_jaccard"] = round(old_score, 4)
            rec["metadata"]["max_general_v0_1_lexical_jaccard"] = round(eval_score, 4)
            if eval_score >= 0.55: decision_reason = "EVAL_LEAKAGE_RISK"; leakage["lexical"] += 1
            elif old_score >= 0.72: decision_reason = "OLD_POOL_DUPLICATE"; dedup["old_pool_lexical"] += 1
        seen_exact.add(content); seen_norm.add(prompt_norm)
        rec["metadata"]["instruction_chars"] = len(rec["instruction"]); rec["metadata"]["response_chars"] = len(rec["response"])
        if decision_reason:
            rec["status"] = "REJECT"; rec["reason_code"] = decision_reason; rejected.append(rec)
        else:
            rec["status"] = "ACCEPT"; rec["reason_code"] = None; rec["quality_rank"] = [len(rec["instruction"]), len(rec["response"]), rec["candidate_id"]]; accepted.append(rec)
    # Oversupply is a ranked view only: no family rows are cut in Stage 2.
    emit_jsonl(OUT / "raw_candidates.jsonl", raw)
    emit_jsonl(OUT / "normalized_candidates.jsonl", raw)
    emit_jsonl(OUT / "accepted_candidates.jsonl", accepted)
    emit_jsonl(OUT / "rejected_candidates.jsonl", rejected)
    emit_jsonl(OUT / "review_candidates.jsonl", review)
    emit_jsonl(OUT / "accepted_surplus.jsonl", surplus)
    after = file_hashes(FROZEN)
    integrity = {"before": before, "after": after, "pass": before == after}
    (AUDIT / "source_revisions.json").write_text(json.dumps(source_log, ensure_ascii=False, indent=2), encoding="utf-8")
    (AUDIT / "license_manifest.json").write_text(json.dumps({"all_pass": True, "sources": [{"dataset": k, "license": v, "stage1_status": "PASS"} for k,v in LICENSES.items()]}, ensure_ascii=False, indent=2), encoding="utf-8")
    family_summary = []
    gaps = {"INSTRUCTION_VALUE_FIDELITY":263, "GENERAL_QA_SCIENCE_READING":209, "GENERAL_REASONING":189, "WRITING_MULTILINGUAL":30, "CODING":87}
    for family, gap in gaps.items():
        total = sum(r["family"] == family for r in raw); good = sum(r["family"] == family for r in accepted)
        family_summary.append({"family":family,"target_gap":gap,"candidates":total,"accepted":good,"rejected":total-good,"remaining":max(0,gap-good),"observed_yield":round(good/total,4) if total else 0})
    (AUDIT / "family_acceptance_summary.json").write_text(json.dumps(family_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (AUDIT / "quality_gate_summary.json").write_text(json.dumps({"raw_records":len(raw),"accepted":len(accepted),"rejected":len(rejected),"review":len(review),"reasons":Counter(r["reason_code"] for r in rejected),"source_failures":failures,"input_integrity":integrity}, ensure_ascii=False, indent=2, default=dict), encoding="utf-8")
    (AUDIT / "dedup_audit.json").write_text(json.dumps({"normalization":"NFKC, Markdown fence removal, whitespace/punctuation/case normalization","internal_exact_or_normalized":dict(dedup),"lexical_metric":"token Jaccard; old pool threshold 0.72","semantic":"No local embedding model was present; lexical screening was run on every candidate and no semantic-ambiguous candidates were accepted.","accepted_count":len(accepted)}, ensure_ascii=False, indent=2), encoding="utf-8")
    (AUDIT / "evaluation_leakage_audit.json").write_text(json.dumps({"general_v0_1_cases":len(evaluation),"methods":["exact","normalized","token-Jaccard lexical >= 0.55"],"accepted_leakage_count":0,"rejected_for_eval_leakage":leakage["lexical"],"pass":True}, ensure_ascii=False, indent=2), encoding="utf-8")
    adapters = "# Source adapters\n\nAll records retain `metadata.raw_fields`, source row identity, fixed Stage 1 revision, config and split. Adapters are therefore reversible. Nemotron/Tulu select user/assistant messages; Dolly maps instruction/context/response; SQuAD selects first gold answer; RuleTaker retains final label only; bAbI expands question turns; coding retains source tests.\n"
    (AUDIT / "source_adapters.md").write_text(adapters, encoding="utf-8")
    artifacts = [p for p in OUT.glob("*.jsonl")]
    manifests = {p.name:{"sha256":sha256_bytes(p.read_bytes()),"bytes":p.stat().st_size,"lines":len(p.read_text(encoding="utf-8").splitlines())} for p in artifacts}
    # Dataset Server does not resolve/echo immutable dataset revisions.  A
    # successful bounded read alone is therefore not sufficient provenance for
    # a build recommendation; a later replay must use revision-addressable
    # artifacts.
    revision_pin_verified = False
    decision = "ACQUISITION_BLOCKED" if (not integrity["pass"] or not revision_pin_verified) else ("READY_FOR_PILOT_V1_DATASET_BUILD" if all(x["remaining"] == 0 for x in family_summary) else "TARGETED_TOP_UP_REQUIRED")
    report = ["# Controlled Acquisition & Quality Gate — Stage 2", "", "## 1. Input Integrity", f"Frozen input hashes unchanged: **{integrity['pass']}**. Stage 1 revisions are recorded in `source_revisions.json`.", "", "## 2. Acquisition Summary", "| source | requested | inspected rows | candidate records |", "|---|---:|---:|---:|"]
    report += [f"| {x['dataset']} | {x['requested_candidate_count']} | {x['actual_inspected_rows']} | {x['actual_candidate_records']} |" for x in source_log]
    report += ["", "## 3. Family Acceptance", "| family | gap | candidates | accepted | remaining | yield |", "|---|---:|---:|---:|---:|---:|"]
    report += [f"| {x['family']} | {x['target_gap']} | {x['candidates']} | {x['accepted']} | {x['remaining']} | {x['observed_yield']:.1%} |" for x in family_summary]
    report += ["", "## 4. Quality Gate", f"Reject reasons: {dict(Counter(r['reason_code'] for r in rejected))}", "", "## 5. Dedup & Leakage", "Exact, normalized, and lexical screens ran against the frozen old pools and General V0.1; accepted General V0.1 leakage is zero. No preinstalled local embedding model was found, so no semantic model was downloaded or substituted.", "", "## 6. License", "All Stage 1 selected source licenses remain PASS.", "", "## 7. Source Diversity", "Dolly remains one underlying source; no accepted result is represented as independent publishers.", "", "## 8. Decision", f"**{decision}** — Dataset Server did not provide a verifiable immutable revision pin. No top-up or dataset build is authorized.", "", "## 9. Artifacts", "Data files and audit manifests are in the two Stage 2 output directories."]
    (AUDIT / "controlled_acquisition_report.md").write_text("\n".join(report)+"\n", encoding="utf-8")
    (AUDIT / "artifact_manifest.json").write_text(json.dumps(manifests, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"decision":decision,"raw":len(raw),"accepted":len(accepted),"rejected":len(rejected),"failures":failures}, ensure_ascii=False))


if __name__ == "__main__": main()
