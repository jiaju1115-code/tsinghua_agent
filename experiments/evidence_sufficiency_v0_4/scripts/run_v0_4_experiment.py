"""Evidence Sufficiency V0.4: frozen local semantic-support representation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
V03 = PROJECT / "experiments" / "evidence_sufficiency_v0_3"
LABELS = ["EVIDENCE_SUFFICIENT", "EVIDENCE_PARTIAL", "EVIDENCE_INSUFFICIENT"]
ENGINE = "deepseek-r1:7b"
SEED = 20260814
THRESHOLDS = [0.50, 0.55, 0.58, 0.60, 0.65]
FEATURE_NAMES = [
    "core_total", "entailed_count", "partial_count", "not_found_count",
    "contradicted_count", "entailed_ratio", "partial_ratio", "not_found_ratio",
    "attribute_supported_ratio", "min_support_score", "mean_support_score",
    "support_score_std", "mean_directness", "all_core_direct",
]
PROMPT = """你是离线证据蕴含标注器。只基于给出的 Query 与 Evidence spans 工作，不知道也不得猜测任何 gold label。

任务一：把 Query 拆为 1–3 个原子且必要的 CORE_REQUIRED_POINTS。每个点只表达一个不可缺少的判断；语义重复、对象/条件/动作/结果属于同一事实时必须合并。真正并列、需要分别回答的任务才拆分。把有助于完整性、但不影响能否完成用户核心任务的内容放入 OPTIONAL_SUPPORT。

任务二：为每个 CORE_REQUIRED_POINT 选择最相关的证据 span，并判断支持关系：
- ENTAILED：证据直接、完整支持该点及其 requested attribute；
- PARTIAL：证据回答真实的一部分，但缺必要条件、对象、范围、步骤或 requested attribute；
- NOT_FOUND：证据无法实质回答；主题相关、共享关键词或同一文档均不算支持；
- CONTRADICTED：证据与该点所需结论明确冲突。

requested_attribute 必须写出主要提问属性（例如 time、location、condition、process、material、amount、contact、reason、definition、subject）。若没有明显属性，写 subject。不得因为有一个高相关 span 就认为其他点也被支持。

返回严格符合 JSON schema 的对象。每个 support_matrix 条目必须对应一个 point id，并只引用输入中提供的 span id。\n\n"""

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["core_required_points", "requested_attributes", "optional_support", "support_matrix"],
    "properties": {
        "core_required_points": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["required_point_id", "required_point_text", "requested_attribute"],
            "properties": {
                "required_point_id": {"type": "string", "pattern": "^P[1-3]$"},
                "required_point_text": {"type": "string", "minLength": 2, "maxLength": 240},
                "requested_attribute": {"type": "string", "minLength": 2, "maxLength": 48},
            },
        }},
        "requested_attributes": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string", "minLength": 2, "maxLength": 48}},
        "optional_support": {"type": "array", "maxItems": 5, "items": {"type": "string", "minLength": 2, "maxLength": 180}},
        "support_matrix": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["required_point_id", "best_evidence_span_ids", "best_evidence_text", "source_document_id", "support_relation", "support_score", "directness", "attribute_match", "reason"],
            "properties": {
                "required_point_id": {"type": "string", "pattern": "^P[1-3]$"},
                "best_evidence_span_ids": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string", "minLength": 1, "maxLength": 80}},
                "best_evidence_text": {"type": "string", "minLength": 1, "maxLength": 500},
                "source_document_id": {"type": "string", "minLength": 1, "maxLength": 120},
                "support_relation": {"type": "string", "enum": ["ENTAILED", "PARTIAL", "NOT_FOUND", "CONTRADICTED"]},
                "support_score": {"type": "number", "minimum": 0, "maximum": 1},
                "directness": {"type": "number", "minimum": 0, "maximum": 1},
                "attribute_match": {"type": "boolean"},
                "reason": {"type": "string", "minLength": 1, "maxLength": 400},
            },
        }},
    },
}


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text or "")
    text = re.sub(r"!?\([^)]*\)", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def grams(text: str):
    text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text or "").lower()
    return {text[i:i+n] for n in (2, 3) for i in range(max(0, len(text)-n+1))}


def lexical_score(query: str, text: str) -> float:
    a, b = grams(query), grams(text)
    return len(a & b) / max(1, len(a))


def evidence_spans(row):
    spans = []
    evidence = row.get("frozen_evidence", [])
    if isinstance(evidence, str):
        evidence = json.loads(evidence)
    for evidence_index, item in enumerate(evidence):
        doc = str(item.get("source_id") or item.get("evidence_id") or item.get("chunk_id") or f"DOC{evidence_index+1}")
        eid = str(item.get("evidence_id") or item.get("context_id") or item.get("chunk_id") or f"E{evidence_index+1}")
        title = clean(item.get("title", ""))
        text = clean(item.get("text", ""))
        pieces = [piece.strip() for piece in re.split(r"[。！？!?\n；;]", text) if len(piece.strip()) >= 12]
        if not pieces and text:
            pieces = [text]
        for index, piece in enumerate(pieces):
            spans.append({"span_id": f"{eid}::{index+1}", "document_id": doc, "text": (title + " " + piece).strip()[:480]})
    ranked = sorted(spans, key=lambda span: (-lexical_score(row["query"], span["text"]), span["span_id"]))
    return ranked[:8] if ranked else [{"span_id": "NO_EVIDENCE::1", "document_id": "NO_EVIDENCE", "text": "[NO_EVIDENCE]"}]


def v03_points(query: str):
    query = re.sub(r"[？?。]$", "", query.strip())
    parts = [x.strip(" ，,") for x in re.split(r"、|，|,|；|;", query) if len(x.strip()) >= 2]
    return parts or [query]


def prompt_for(row, spans):
    evidence = "\n".join(f"[{s['span_id']}] document={s['document_id']} text={s['text']}" for s in spans)
    return PROMPT + f"Query:\n{row['query']}\n\nEvidence spans:\n{evidence}\n"


def invoke(prompt: str):
    payload = {
        "model": ENGINE, "prompt": prompt, "stream": False, "format": SCHEMA,
        "think": False, "keep_alive": "30m",
        "options": {"temperature": 0, "seed": SEED, "num_predict": 550},
    }
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body, body.get("response", "")


def validate(value, spans):
    if not isinstance(value, dict) or set(value) != {"core_required_points", "requested_attributes", "optional_support", "support_matrix"}:
        return False, "top_level_schema"
    points = value["core_required_points"]
    matrix = value["support_matrix"]
    if not 1 <= len(points) <= 3 or len(matrix) != len(points):
        return False, "point_matrix_count"
    ids = [p.get("required_point_id") for p in points]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"P[1-3]", str(x)) for x in ids):
        return False, "point_ids"
    span_ids = {span["span_id"] for span in spans}
    seen = []
    for item in matrix:
        if item.get("required_point_id") not in ids or item.get("required_point_id") in seen:
            return False, "matrix_point_ids"
        seen.append(item.get("required_point_id"))
        if item.get("support_relation") not in {"ENTAILED", "PARTIAL", "NOT_FOUND", "CONTRADICTED"}:
            return False, "relation"
        if not all(x in span_ids for x in item.get("best_evidence_span_ids", [])):
            return False, "span_reference"
        if not isinstance(item.get("attribute_match"), bool):
            return False, "attribute_match"
        if not all(isinstance(item.get(key), (int, float)) and 0 <= item[key] <= 1 for key in ("support_score", "directness")):
            return False, "scores"
    return True, "ok"


def input_audit():
    freeze = json.loads((V03 / "audit" / "input_freeze.json").read_text(encoding="utf-8"))
    checks = {filename: {"expected": expected, "actual": sha256(Path(filename))} for filename, expected in freeze["inputs"].items()}
    for check in checks.values():
        check["match"] = check["expected"] == check["actual"]
    unified = V03 / "dataset" / "unified_calibration_dataset.json"
    unified_hash = sha256(unified)
    candidate = json.loads((V03 / "audit" / "candidate_freeze.json").read_text(encoding="utf-8"))
    candidate_script = V03 / "scripts" / "run_v0_3_cross_validation.py"
    protocol_ok = candidate["artifacts"]["scripts/run_v0_3_cross_validation.py"]["sha256"] == sha256(candidate_script)
    data = json.loads(unified.read_text(encoding="utf-8"))
    counts = Counter(row["data_kind"] for row in data)
    passed = all(item["match"] for item in checks.values()) and unified_hash == freeze["unified_dataset_sha256"] and protocol_ok and counts["REAL_ADJUDICATED"] == 49 and counts["SYNTHETIC_CONSTRUCTED"] == 98
    return passed, {"status": "PASS" if passed else "INPUT_OR_PROTOCOL_MISMATCH", "v0_3_input_hashes": checks, "unified": {"expected": freeze["unified_dataset_sha256"], "actual": unified_hash, "match": unified_hash == freeze["unified_dataset_sha256"]}, "counts": dict(counts), "protocol": {"v0_3_cv_script_sha256": sha256(candidate_script), "verified_against_v0_3_freeze": protocol_ok, "outer_folds": 5, "real_stratum": "gold_label (as implemented in V0.3)", "synthetic_stratum": "construction_type", "inner_folds": 3, "random_seed": SEED, "dedup_rule": "reuse V0.3 unified Query+Evidence dataset without re-deduplication"}}


def engine_manifest():
    manifest = Path(r"C:\Users\林宇轩\.ollama\models\manifests\registry.ollama.ai\library\deepseek-r1\7b")
    value = json.loads(manifest.read_text(encoding="utf-8"))
    model_layer = next(layer for layer in value["layers"] if layer["mediaType"] == "application/vnd.ollama.image.model")
    return {"engine": ENGINE, "transport": "local_ollama_http_127_0_0_1", "manifest_path": str(manifest), "manifest_sha256": sha256(manifest), "model_blob_digest": model_layer["digest"], "model_bytes": model_layer["size"], "temperature": 0, "seed": SEED, "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(), "schema_sha256": hashlib.sha256(json.dumps(SCHEMA, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(), "offline_only": True, "model_comparison": "not performed"}


def prepare():
    passed, audit = input_audit()
    dump(ROOT / "dataset" / "input_hashes.json", audit)
    if not passed:
        print("INPUT_OR_PROTOCOL_MISMATCH")
        return 2
    config = {"experiment": "Evidence Sufficiency V0.4 Semantic Support Representation", "candidate": "v0.4-a", "seed": SEED, "model": ENGINE, "features": FEATURE_NAMES, "random_forest": {"n_estimators": 96, "max_depth": 7, "min_samples_leaf": 2, "class_weight": "balanced_subsample", "random_state": SEED, "n_jobs": 1}, "threshold_selection": {"method": "3-fold inner CV on each outer-train split", "candidates": THRESHOLDS, "utility": "V0.3 utility function"}, "scope": "support-representation-only; labels excluded from point/span inference"}
    protocol = audit["protocol"]
    dump(ROOT / "config" / "experiment_config.json", config)
    dump(ROOT / "config" / "evaluation_protocol.json", protocol)
    dump(ROOT / "config" / "semantic_engine_manifest.json", engine_manifest())
    dump(ROOT / "schema" / "semantic_support_schema.json", SCHEMA)
    dump(ROOT / "schema" / "required_point_schema.json", {"type": "object", "required": ["core_required_points", "requested_attributes", "optional_support"], "properties": {key: SCHEMA["properties"][key] for key in ("core_required_points", "requested_attributes", "optional_support")}})
    dump(ROOT / "dataset" / "input_manifest.json", {"source": str(V03 / "dataset" / "unified_calibration_dataset.json"), "source_sha256": audit["unified"]["actual"], "rows": 147, "real": 49, "synthetic": 98, "status": "ALL_SEEN_CALIBRATION"})
    print("INPUT_AUDIT_PASS")
    return 0


def freeze():
    paths = [ROOT / "config" / "experiment_config.json", ROOT / "config" / "evaluation_protocol.json", ROOT / "config" / "semantic_engine_manifest.json", ROOT / "schema" / "semantic_support_schema.json", ROOT / "schema" / "required_point_schema.json", Path(__file__)]
    payload = {"candidate": "v0.4-a", "frozen_at_utc": datetime.now(timezone.utc).isoformat(), "rule": "No prompt, model, seed, schema, feature, threshold-selection protocol, or code changes after this freeze.", "artifacts": {str(p.relative_to(ROOT)).replace("\\", "/"): {"sha256": sha256(p), "bytes": p.stat().st_size} for p in paths}}
    dump(ROOT / "audit" / "candidate_freeze.json", payload)
    print("CANDIDATE_FREEZE_PASS")
    return 0


def record_matrix(row, cache):
    key = row["record_id"]
    if key in cache:
        return cache[key]
    spans = evidence_spans(row)
    prompt = prompt_for(row, spans)
    input_hash = hashlib.sha256((prompt + json.dumps(SCHEMA, ensure_ascii=False, sort_keys=True)).encode("utf-8")).hexdigest()
    raw_records = []
    for attempt in range(2):
        body, raw = invoke(prompt)
        raw_records.append({"attempt": attempt + 1, "raw_response": raw, "response_metadata": {key: body.get(key) for key in ("model", "created_at", "total_duration", "eval_count")}})
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = None
        valid, reason = validate(value, spans)
        if valid:
            return {"record_id": key, "sample_id": row["sample_id"], "source_dataset": row["source_dataset"], "data_kind": row["data_kind"], "construction_type": row["construction_type"], "query": row["query"], "input_hash": input_hash, "candidate_spans": spans, "semantic_output": value, "raw_outputs": raw_records, "schema_validation": {"status": "PASS", "reason": "ok"}}
    return {"record_id": key, "sample_id": row["sample_id"], "source_dataset": row["source_dataset"], "data_kind": row["data_kind"], "construction_type": row["construction_type"], "query": row["query"], "input_hash": input_hash, "candidate_spans": spans, "semantic_output": None, "raw_outputs": raw_records, "schema_validation": {"status": "FAIL", "reason": reason}}


def materialize():
    data = json.loads((V03 / "dataset" / "unified_calibration_dataset.json").read_text(encoding="utf-8"))
    matrix_file = ROOT / "dataset" / "semantic_support_matrix.jsonl"
    existing = {}
    if matrix_file.exists():
        for line in matrix_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                existing[item["record_id"]] = item
    all_items = []
    for index, row in enumerate(data, 1):
        item = record_matrix(row, existing)
        all_items.append(item)
        matrix_file.parent.mkdir(parents=True, exist_ok=True)
        matrix_file.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in all_items) + "\n", encoding="utf-8")
        print(f"semantic {index}/{len(data)} {row['record_id']} {item['schema_validation']['status']}", flush=True)
    if any(item["schema_validation"]["status"] != "PASS" for item in all_items):
        print("SEMANTIC_ENGINE_UNAVAILABLE")
        return 3
    required_lines, optional_lines, changes = [], [], []
    for row, item in zip(data, all_items):
        output = item["semantic_output"]
        required_lines.append({"record_id": row["record_id"], "sample_id": row["sample_id"], "query": row["query"], "v0_3_required_points": v03_points(row["query"]), "core_required_points": output["core_required_points"], "requested_attributes": output["requested_attributes"]})
        optional_lines.append({"record_id": row["record_id"], "sample_id": row["sample_id"], "optional_support": output["optional_support"]})
        before, after = v03_points(row["query"]), [p["required_point_text"] for p in output["core_required_points"]]
        if len(after) < len(before): change = "merge"
        elif len(after) > len(before): change = "split"
        elif before == after: change = "unchanged"
        else: change = "rephrase"
        changes.append({"record_id": row["record_id"], "sample_id": row["sample_id"], "v0_3_required_points": before, "v0_4_required_points": after, "change": change, "optional_removed": output["optional_support"], "requested_attribute_added": output["requested_attributes"]})
    for path, rows in [(ROOT / "dataset" / "required_point_representation.jsonl", required_lines), (ROOT / "dataset" / "optional_support.jsonl", optional_lines), (ROOT / "analysis" / "required_point_change_log.jsonl", changes)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")
    return 0


def support_features(item):
    matrix = item["semantic_output"]["support_matrix"]
    total = len(matrix); counts = Counter(x["support_relation"] for x in matrix)
    scores = [float(x["support_score"]) for x in matrix]
    direct = [float(x["directness"]) for x in matrix]
    attrs = [bool(x["attribute_match"]) for x in matrix]
    return np.array([total, counts["ENTAILED"], counts["PARTIAL"], counts["NOT_FOUND"], counts["CONTRADICTED"], counts["ENTAILED"]/total, counts["PARTIAL"]/total, counts["NOT_FOUND"]/total, sum(attrs)/total, min(scores), sum(scores)/total, float(np.std(scores)), sum(direct)/total, int(all(x >= .70 for x in direct))], dtype=float)


def folds(rows, stratum, k=5):
    groups = defaultdict(list)
    for row in rows: groups[stratum(row)].append(row)
    result = [[] for _ in range(k)]
    for group in groups.values():
        group.sort(key=lambda row: hashlib.sha256((row["record_id"] + "||v0.3_cv").encode()).hexdigest())
        for i, row in enumerate(group): result[i % k].append(row)
    return result


def fit(rows, representation):
    config = json.loads((ROOT / "config" / "experiment_config.json").read_text(encoding="utf-8"))["random_forest"]
    x = np.vstack([support_features(representation[r["record_id"]]) for r in rows]); y = np.array([r["label"] for r in rows])
    return RandomForestClassifier(**config).fit(x, y)


def predict(rows, representation, model, threshold):
    x = np.vstack([support_features(representation[r["record_id"]]) for r in rows]); probs = model.predict_proba(x); classes = list(model.classes_); results=[]
    for row, values in zip(rows, probs):
        prob = dict(zip(classes, map(float, values)))
        prediction = "EVIDENCE_SUFFICIENT" if prob.get("EVIDENCE_SUFFICIENT", 0) >= threshold else max(["EVIDENCE_PARTIAL", "EVIDENCE_INSUFFICIENT"], key=lambda label: prob.get(label, 0))
        results.append({"record_id": row["record_id"], "sample_id": row["sample_id"], "source_dataset": row["source_dataset"], "data_kind": row["data_kind"], "construction_type": row["construction_type"], "expected": row["label"], "predicted": prediction, "probabilities": prob, "semantic_support": representation[row["record_id"]]["semantic_output"]})
    return results


def div(a,b): return a/b if b else None
def metrics(rows):
    cm={a:{b:0 for b in LABELS} for a in LABELS}
    for row in rows: cm[row["expected"]][row["predicted"]]+=1
    per={}
    for label in LABELS:
        tp=cm[label][label]; fp=sum(cm[x][label] for x in LABELS if x!=label); fn=sum(cm[label][x] for x in LABELS if x!=label); p=div(tp,tp+fp); r=div(tp,tp+fn); per[label]={"precision":p,"recall":r,"f1":2*p*r/(p+r) if p is not None and r is not None and p+r else 0,"support":sum(cm[label].values())}
    fs=sum(x["expected"]!="EVIDENCE_SUFFICIENT" and x["predicted"]=="EVIDENCE_SUFFICIENT" for x in rows); missed=sum(x["expected"]=="EVIDENCE_SUFFICIENT" and x["predicted"]!="EVIDENCE_SUFFICIENT" for x in rows)
    by={}
    for kind in sorted({r["construction_type"] for r in rows}):
        group=[r for r in rows if r["construction_type"]==kind]; by[kind]={"n":len(group),"correct":sum(r["expected"]==r["predicted"] for r in group),"accuracy":div(sum(r["expected"]==r["predicted"] for r in group),len(group))}
    return {"n":len(rows),"accuracy":{"count":sum(x["expected"]==x["predicted"] for x in rows),"rate":div(sum(x["expected"]==x["predicted"] for x in rows),len(rows))},"macro_f1":sum(per[x]["f1"] for x in LABELS)/3,"sufficient_precision":per["EVIDENCE_SUFFICIENT"]["precision"],"sufficient_recall":per["EVIDENCE_SUFFICIENT"]["recall"],"partial_recall":per["EVIDENCE_PARTIAL"]["recall"],"insufficient_recall":per["EVIDENCE_INSUFFICIENT"]["recall"],"false_sufficient":{"count":fs,"denominator":sum(x["expected"]!="EVIDENCE_SUFFICIENT" for x in rows),"rate":div(fs,sum(x["expected"]!="EVIDENCE_SUFFICIENT" for x in rows))},"missed_sufficient":{"count":missed,"denominator":sum(x["expected"]=="EVIDENCE_SUFFICIENT" for x in rows),"rate":div(missed,sum(x["expected"]=="EVIDENCE_SUFFICIENT" for x in rows))},"confusion_matrix":cm,"per_class":per,"by_construction_type":by}


def utility(m): return .32*(1-(m["false_sufficient"]["rate"] or 0))+.28*(m["sufficient_recall"] or 0)+.16*(m["partial_recall"] or 0)+.12*(m["insufficient_recall"] or 0)+.12*m["macro_f1"]


def nested_cv(rows, representation, stratum):
    outer=folds(rows,stratum); oof=[]; reports=[]
    for i, validation in enumerate(outer):
        train=[r for j, fold in enumerate(outer) if j!=i for r in fold]; inner=folds(train,stratum,3); score={}
        for threshold in THRESHOLDS:
            combined=[]
            for j, inner_val in enumerate(inner):
                inner_train=[r for z, fold in enumerate(inner) if z!=j for r in fold]
                combined.extend(predict(inner_val,representation,fit(inner_train,representation),threshold))
            score[str(threshold)]=utility(metrics(combined))
        threshold=float(max(score,key=score.get)); fold_predictions=predict(validation,representation,fit(train,representation),threshold); oof.extend(fold_predictions); reports.append({"fold":i+1,"train_n":len(train),"validation_n":len(validation),"selected_threshold":threshold,"inner_cv_utility":score,"validation_metrics":metrics(fold_predictions)})
    return oof,{"method":"V0.3 fold construction reused; 5-fold outer CV and 3-fold train-fold-only threshold calibration","folds":reports,"aggregate":metrics(oof)}


def evaluate():
    data=json.loads((V03 / "dataset" / "unified_calibration_dataset.json").read_text(encoding="utf-8")); representation={json.loads(line)["record_id"]:json.loads(line) for line in (ROOT / "dataset" / "semantic_support_matrix.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    real=[r for r in data if r["data_kind"]=="REAL_ADJUDICATED"]; synthetic=[r for r in data if r["data_kind"]=="SYNTHETIC_CONSTRUCTED"]
    rp,rm=nested_cv(real,representation,lambda r:r["label"]); sp,sm=nested_cv(synthetic,representation,lambda r:r["construction_type"])
    for group, pred, strat in [(real,rp,lambda r:r["label"]),(synthetic,sp,lambda r:r["construction_type"])]:
        mapping={row["record_id"]:i+1 for i,fold in enumerate(folds(group,strat)) for row in fold}
        for item in pred:item["fold"]=mapping[item["record_id"]]
    dump(ROOT / "results" / "real_cross_validation_metrics.json", rm); dump(ROOT / "results" / "synthetic_cross_validation_metrics.json", sm)
    for path, rows in [(ROOT / "results" / "real_cross_validation_predictions.jsonl",rp),(ROOT / "results" / "synthetic_cross_validation_predictions.jsonl",sp)]: path.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")
    # Seen regression: final model is fitted once on all seen calibration data; threshold uses frozen 0.58.
    model=fit(data,representation); final_threshold=.58
    legacy=[r for r in data if r["source_dataset"]=="LEGACY_SYNTHETIC_V0_1"]
    historical=legacy
    hp=predict(historical,representation,model,final_threshold); hm=metrics(hp); hm["evaluation_status"]="SEEN_REGRESSION"; dump(ROOT / "results" / "historical_regression_metrics.json", {"legacy_synthetic_v0_1":hm,"note":"Final model fitted on all seen calibration rows; not generalization."}); (ROOT / "results" / "historical_regression_predictions.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in hp)+"\n",encoding="utf-8")
    print(json.dumps({"real":rm["aggregate"],"synthetic":sm["aggregate"],"legacy":hm},ensure_ascii=False))
    return 0


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("mode",choices=["prepare","freeze","materialize","evaluate"]); args=parser.parse_args()
    return {"prepare":prepare,"freeze":freeze,"materialize":materialize,"evaluate":evaluate}[args.mode]()

if __name__ == "__main__": sys.exit(main())
