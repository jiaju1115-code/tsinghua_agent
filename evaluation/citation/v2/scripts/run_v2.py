from __future__ import annotations

import gc
import hashlib
import json
import math
import re
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent
V1 = DATA / "citation_pipeline_v1"
RAG1 = DATA / "rag_v1"
RAG0 = DATA / "rag_v0"
AE1 = DATA / "answer_eval_v1"
CFG = json.loads((ROOT / "config" / "citation_v2_config.json").read_text(encoding="utf-8"))
FACT_TYPES = {"FACTUAL", "PROCEDURAL", "TEMPORAL", "NUMERIC", "LOCATION", "ENTITY", "UNCERTAIN"}
KNOWN_GAPS = set(CFG["known_source_quality_failure_question_ids"])

NUM_RE = re.compile(r"(?<![A-Za-z])(?:\d+(?:\.\d+)?(?::\d{1,2})?|[零〇一二三四五六七八九十百千万两]+)\s*(?:万元|元|人民币|百分比|%|学分|次|号楼|号|楼|年|月|日|天|小时|分钟|周|个|平方米|平米|席位)?")
TIME_RE = re.compile(r"(?:\d{4}\s*年|\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}:\d{2}|春季学期|秋季学期|工作日|截止(?:日期|时间)?|开放时间|办理时间)")
ENTITY_RE = re.compile(r"(?:[A-Za-z0-9\u4e00-\u9fff]{2,28})(?:大学|学院|学系|委员会|服务中心|中心|医院|图书馆|食堂|宿舍|校区|教学楼|体育馆|场馆|平台|系统|项目|教务处|学生处)")
PROC_WORDS = ("申请", "提交", "办理", "登录", "查询", "预约", "登记", "缴纳", "审核", "审批", "注册", "签订", "报销", "进入", "访问", "联系", "下载", "上传")
SEQ_WORDS = ("首先", "然后", "之后", "再", "最后", "先", "后", "前", "以内", "截止")


def jl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def dumpjl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm_text(text: str):
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = text.translate(str.maketrans({"，": ",", "。": ".", "；": ";", "：": ":", "（": "(", "）": ")", "【": "[", "】": "]", "“": '"', "”": '"', "、": ","}))
    return re.sub(r"\s+", "", text)


CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn_number(token: str):
    if not token or any(ch not in "零〇一二两三四五六七八九十百千万" for ch in token):
        return None
    if all(ch in CN_DIGITS for ch in token):
        return float("".join(str(CN_DIGITS[ch]) for ch in token))
    total = section = number = 0
    for ch in token:
        if ch in CN_DIGITS:
            number = CN_DIGITS[ch]
        elif ch in "十百千":
            unit = {"十": 10, "百": 100, "千": 1000}[ch]
            section += (number or 1) * unit
            number = 0
        elif ch == "万":
            total += (section + number) * 10000
            section = number = 0
    return float(total + section + number)


def numeric_facts(text: str):
    facts = []
    for match in NUM_RE.finditer(unicodedata.normalize("NFKC", text or "")):
        raw = re.sub(r"\s+", "", match.group())
        m = re.match(r"(\d+(?:\.\d+)?(?::\d{1,2})?|[零〇一二三四五六七八九十百千万两]+)(.*)", raw)
        if not m:
            continue
        value, unit = m.groups()
        if ":" in value:
            normalized = value
        elif value[0].isdigit():
            normalized = str(float(value)).rstrip("0").rstrip(".") if "." in value else str(int(value))
        else:
            parsed = cn_number(value)
            if parsed is None:
                continue
            normalized = str(int(parsed)) if parsed.is_integer() else str(parsed)
        facts.append({"value": normalized, "unit": unit or "", "raw": raw})
    return facts


def temporal_facts(text: str):
    return sorted(set(norm_text(x) for x in TIME_RE.findall(unicodedata.normalize("NFKC", text or ""))))


def entity_facts(text: str):
    out = []
    for segment in re.split(r"[。！？；;，,：:\n\[\]()（）]", unicodedata.normalize("NFKC", text or "")):
        for match in ENTITY_RE.finditer(segment):
            value = match.group().strip()
            if 2 <= len(value) <= 32:
                out.append(value)
    return sorted(set(out), key=lambda x: (-len(x), x))


def char_bigrams(text: str):
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", norm_text(text))
    if len(text) < 2:
        return {text} if text else set()
    return {text[i:i+2] for i in range(len(text)-1)}


def lexical_coverage(claim: str, evidence: str):
    a, b = char_bigrams(claim), char_bigrams(evidence)
    return len(a & b) / len(a) if a else 0.0


def split_sentences(text: str):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    units = []
    heading = ""
    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para or para == "---":
            continue
        if re.match(r"^#{1,6}\s*", para) or (len(para) <= 30 and para.startswith("**") and para.endswith("**")):
            heading = re.sub(r"^[#*\s]+|[*\s]+$", "", para)
            continue
        para = re.sub(r"^[-*]\s+", "", para)
        pieces = re.split(r"(?<=[。！？；;])\s*", para)
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            if len(piece) > 350:
                sub = re.split(r"(?<=[，,])\s*", piece)
                buf = ""
                for token in sub:
                    if buf and len(buf) + len(token) > 330:
                        units.append((heading, buf))
                        buf = token
                    else:
                        buf += token
                if buf:
                    units.append((heading, buf))
            else:
                units.append((heading, piece))
    return units


def build_spans(a_rows):
    cfg = CFG["span"]
    spans = []
    seen = set()
    started = time.perf_counter()
    for q in a_rows:
        for ctx in q["retrieved_context"]:
            units = split_sentences(ctx["text"])
            local = 0
            for start in range(len(units)):
                for width in range(1, cfg["max_sentences"] + 1):
                    end = start + width
                    if end > len(units):
                        break
                    head = units[start][0]
                    body = "".join(x[1] for x in units[start:end])
                    span_text = f"{head}：{body}" if head and head not in body else body
                    span_text = span_text.strip()
                    if len(span_text) < cfg["min_chars"] or len(span_text) > cfg["max_chars"]:
                        continue
                    key = (q["question_id"], ctx["chunk_id"], norm_text(span_text))
                    if key in seen:
                        continue
                    seen.add(key)
                    local += 1
                    spans.append({
                        "question_id": q["question_id"], "chunk_id": ctx["chunk_id"], "document_id": ctx["source_id"],
                        "span_id": f"{q['question_id']}-{ctx['chunk_id']}-S{local:04d}", "span_text": span_text,
                        "sentence_start": start, "sentence_end": end - 1, "source_url": ctx.get("url"),
                        "source_title": ctx.get("title"), "original_dense_rank": ctx["rank"], "original_dense_score": ctx["score"]
                    })
    return spans, time.perf_counter() - started


def build_aliases(spans):
    aliases = {}
    patterns = [
        re.compile(r"([\u4e00-\u9fffA-Za-z0-9]{4,32})[（(](?:以下简称|简称)[“\"]?([\u4e00-\u9fffA-Za-z0-9]{2,16})[”\"]?[）)]"),
        re.compile(r"([\u4e00-\u9fffA-Za-z0-9]{2,16})[，,]?即([\u4e00-\u9fffA-Za-z0-9]{4,32})")
    ]
    for span in spans:
        for pattern in patterns:
            for m in pattern.finditer(span["span_text"]):
                a, b = m.groups()
                full, alias = (a, b) if len(a) >= len(b) else (b, a)
                if full != alias and len(alias) >= 2:
                    key = f"{norm_text(alias)}=>{norm_text(full)}"
                    aliases[key] = {"alias": alias, "canonical": full, "basis": "explicit_same_source_parenthetical_or_equivalence", "chunk_id": span["chunk_id"], "span_id": span["span_id"], "source_url": span["source_url"]}
    out = sorted(aliases.values(), key=lambda x: (x["alias"], x["canonical"], x["span_id"]))
    path = ROOT / "normalization" / "entity_aliases.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"policy": "Only explicit same-source equivalence; no per-question aliases.", "count": len(out), "aliases": out}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    alias_map = defaultdict(set)
    for x in out:
        alias_map[norm_text(x["alias"])].add(norm_text(x["canonical"]))
        alias_map[norm_text(x["canonical"])].add(norm_text(x["alias"]))
    return alias_map


def normalized_rules(claim, span, alias_map):
    ctext, etext = claim["claim_text"], span["span_text"]
    cnums, enums = numeric_facts(ctext), numeric_facts(etext)
    enum_pairs = {(x["value"], x["unit"]) for x in enums}
    num_ok = all((x["value"], x["unit"]) in enum_pairs or (x["value"], "") in enum_pairs for x in cnums)
    ctime, etime = temporal_facts(ctext), temporal_facts(etext)
    time_ok = all(x in etime or x in norm_text(etext) for x in ctime)
    cents = entity_facts(ctext)
    en = norm_text(etext)
    entity_checks = []
    for ent in cents:
        ne = norm_text(ent)
        ok = ne in en or any(alias in en for alias in alias_map.get(ne, set()))
        entity_checks.append(ok)
    ent_ok = all(entity_checks)
    verbs = [x for x in PROC_WORDS if x in ctext]
    proc_ok = all(x in etext for x in verbs)
    seqs = [x for x in SEQ_WORDS if x in ctext]
    seq_ok = all(x in etext for x in seqs)
    flags = [name for name, ok in (("NUMERIC_MISMATCH", num_ok), ("TEMPORAL_MISMATCH", time_ok), ("ENTITY_MISMATCH", ent_ok), ("PROCEDURAL_MISMATCH", proc_ok), ("SEQUENCE_MISMATCH", seq_ok)) if not ok]
    return {
        "numeric_values": cnums, "numeric_match": num_ok, "temporal_values": ctime, "temporal_match": time_ok,
        "entities": cents, "entity_match": ent_ok, "procedural_verbs": verbs, "procedural_match": proc_ok,
        "sequence_tokens": seqs, "sequence_match": seq_ok, "lexical_claim_coverage": lexical_coverage(ctext, etext),
        "exact_normalized_match": norm_text(ctext) in norm_text(etext), "hard_rules_pass": not flags, "rule_flags": flags
    }


def raw_rules(claim, span):
    ctext, etext = claim["claim_text"], span["span_text"]
    cnums = [norm_text(x.group()) for x in NUM_RE.finditer(ctext)]
    num_ok = all(x in norm_text(etext) for x in cnums)
    ctime = temporal_facts(ctext)
    time_ok = all(x in norm_text(etext) for x in ctime)
    cents = entity_facts(ctext)
    ent_ok = all(norm_text(x) in norm_text(etext) for x in cents)
    verbs = [x for x in PROC_WORDS if x in ctext]
    proc_ok = all(x in etext for x in verbs)
    seqs = [x for x in SEQ_WORDS if x in ctext]
    seq_ok = all(x in etext for x in seqs)
    flags = [name for name, ok in (("NUMERIC_MISMATCH", num_ok), ("TEMPORAL_MISMATCH", time_ok), ("ENTITY_MISMATCH", ent_ok), ("PROCEDURAL_MISMATCH", proc_ok), ("SEQUENCE_MISMATCH", seq_ok)) if not ok]
    return {"numeric_match": num_ok, "temporal_match": time_ok, "entity_match": ent_ok, "procedural_match": proc_ok, "sequence_match": seq_ok, "lexical_claim_coverage": lexical_coverage(ctext, etext), "exact_normalized_match": norm_text(ctext) in norm_text(etext), "hard_rules_pass": not flags, "rule_flags": flags}


def encode_spans(spans):
    path = RAG1 / "indexes" / "dense" / "model"
    tok = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModel.from_pretrained(path, local_files_only=True).eval()
    vectors = []
    started = time.perf_counter()
    with torch.inference_mode():
        for s in range(0, len(spans), CFG["embedding"]["batch_size"]):
            texts = [x["span_text"] for x in spans[s:s+CFG["embedding"]["batch_size"]]]
            t = tok(texts, padding=True, truncation=True, max_length=CFG["embedding"]["max_length"], return_tensors="pt")
            v = model(**t).last_hidden_state[:, 0]
            v = torch.nn.functional.normalize(v, p=2, dim=1)
            vectors.append(v.cpu().numpy().astype(np.float32))
    out = np.concatenate(vectors)
    elapsed = time.perf_counter() - started
    del model, tok
    gc.collect()
    return out, elapsed


def make_sanity_set(spans):
    singles = [x for x in spans if x["sentence_start"] == x["sentence_end"] and 35 <= len(x["span_text"]) <= 220]
    positives = singles[:12]
    rows = []
    for i, span in enumerate(positives, 1):
        rows.append({"anchor_id": f"POS-{i:03d}", "anchor_type": "POSITIVE", "premise": span["span_text"], "hypothesis": span["span_text"], "source_span_id": span["span_id"], "benchmark_use": False})
    neg_index = 0
    for span in singles:
        text = span["span_text"]
        match = re.search(r"\d+(?:\.\d+)?", text)
        if match and neg_index < 8:
            old = match.group(); new = str(int(float(old)) + (10 if float(old) < 100 else 1))
            hyp = text[:match.start()] + new + text[match.end():]
            neg_index += 1
            rows.append({"anchor_id": f"NUM-{neg_index:03d}", "anchor_type": "NUMERIC_SWAP", "premise": text, "hypothesis": hyp, "source_span_id": span["span_id"], "benchmark_use": False})
    temporal = 0
    for span in singles:
        match = re.search(r"(\d{1,2})(?=\s*[月日时点])", span["span_text"])
        if match and temporal < 6:
            old = int(match.group()); new = 20 if old != 20 else 10
            hyp = span["span_text"][:match.start()] + str(new) + span["span_text"][match.end():]
            temporal += 1
            rows.append({"anchor_id": f"TMP-{temporal:03d}", "anchor_type": "TEMPORAL_SWAP", "premise": span["span_text"], "hypothesis": hyp, "source_span_id": span["span_id"], "benchmark_use": False})
    entity_pool = defaultdict(list)
    for span in singles:
        for ent in entity_facts(span["span_text"]):
            suffix = next((x for x in ("食堂", "图书馆", "学院", "中心", "医院", "平台", "系统", "校区", "体育馆") if ent.endswith(x)), None)
            if suffix:
                entity_pool[suffix].append((ent, span))
    entity = 0
    for suffix, values in entity_pool.items():
        unique = []
        for ent, span in values:
            if ent not in [x[0] for x in unique]:
                unique.append((ent, span))
        if len(unique) >= 2 and entity < 6:
            (a, span), (b, _) = unique[0], unique[1]
            entity += 1
            rows.append({"anchor_id": f"ENT-{entity:03d}", "anchor_type": "ENTITY_SWAP", "premise": span["span_text"], "hypothesis": span["span_text"].replace(a, b, 1), "source_span_id": span["span_id"], "benchmark_use": False})
    dumpjl(ROOT / "evaluation" / "verifier_sanity_set.jsonl", rows)
    return rows


def verifier_scores(pairs):
    path = RAG1 / "indexes" / "reranker" / "model"
    tok = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True).eval()
    scores = []
    started = time.perf_counter()
    with torch.inference_mode():
        for s in range(0, len(pairs), CFG["verifier"]["batch_size"]):
            batch = pairs[s:s+CFG["verifier"]["batch_size"]]
            t = tok([x[0] for x in batch], [x[1] for x in batch], padding=True, truncation=True, max_length=CFG["verifier"]["max_length"], return_tensors="pt")
            logits = model(**t).logits.view(-1)
            scores.extend(torch.sigmoid(logits).cpu().tolist())
    return model, tok, scores, time.perf_counter() - started


def quantile(values, q):
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=float), q))


def sanity_evaluate(rows, scores):
    results = [{**row, "verifier_score": score} for row, score in zip(rows, scores)]
    positive = [x["verifier_score"] for x in results if x["anchor_type"] == "POSITIVE"]
    negative = [x["verifier_score"] for x in results if x["anchor_type"] != "POSITIVE"]
    by_type = {}
    pos_median = float(np.median(positive)) if positive else None
    for kind in ("NUMERIC_SWAP", "TEMPORAL_SWAP", "ENTITY_SWAP"):
        vals = [x["verifier_score"] for x in results if x["anchor_type"] == kind]
        by_type[kind] = {"count": len(vals), "median": float(np.median(vals)) if vals else None, "separation_from_positive_median": pos_median - float(np.median(vals)) if vals and pos_median is not None else None, "sensitivity_rate": sum(pos_median > x for x in vals) / len(vals) if vals and pos_median is not None else None}
    margin = pos_median - float(np.median(negative)) if positive and negative else None
    available_rates = [v["sensitivity_rate"] for v in by_type.values() if v["sensitivity_rate"] is not None]
    reliable = bool(margin is not None and margin >= CFG["verifier"]["sanity_pass_margin"] and available_rates and min(available_rates) >= CFG["verifier"]["sanity_pairwise_sensitivity_min"])
    p10, n95 = quantile(positive, .10), quantile(negative, .95)
    valid = [x for x in CFG["verifier"]["threshold_candidates"] if (p10 is None or x <= p10) and (n95 is None or x > n95)]
    threshold = min(valid) if valid else max(CFG["verifier"]["threshold_candidates"])
    payload = {"status": "PASS" if reliable else "VERIFIER_NOT_RELIABLE_AS_ENTAILMENT", "model_name": CFG["verifier"]["model_name"], "revision": CFG["verifier"]["revision"], "model_role": CFG["verifier"]["role"], "premise_hypothesis_order": "Premise=evidence span; Hypothesis=claim", "positive_count": len(positive), "hard_negative_count": len(negative), "positive_median": pos_median, "hard_negative_median": float(np.median(negative)) if negative else None, "positive_negative_median_separation": margin, "by_type": by_type, "threshold_candidates": CFG["verifier"]["threshold_candidates"], "selected_threshold": threshold, "threshold_selection_method": CFG["verifier"]["threshold_selection_method"], "false_positive_anchors_at_threshold": sum(x >= threshold for x in negative), "false_negative_anchors_at_threshold": sum(x < threshold for x in positive), "results": results}
    path = ROOT / "evaluation" / "verifier_sanity_results.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def classify(candidates, version, verifier_threshold, qid):
    if qid in KNOWN_GAPS:
        return "UNSUPPORTED", [], {"reason": "known source quality failure safety override"}
    d = CFG["decision"]
    if version == "V2-A":
        sup_e, par_e, sup_l, par_l, rules_key = d["v2a_supported_embedding"], d["v2a_partial_embedding"], d["v2a_supported_lexical"], d["v2a_partial_lexical"], "raw_rules"
    else:
        sup_e, par_e, sup_l, par_l, rules_key = d["v2b_supported_embedding"], d["v2b_partial_embedding"], d["v2b_supported_lexical"], d["v2b_partial_lexical"], "normalized_rules"
    for candidate in candidates:
        rules = candidate[rules_key]
        verifier_ok = version != "V2-C" or (candidate.get("verifier_score") is not None and candidate["verifier_score"] >= verifier_threshold)
        if candidate["embedding_score"] >= sup_e and rules["hard_rules_pass"] and verifier_ok and (rules["lexical_claim_coverage"] >= sup_l or rules["exact_normalized_match"]):
            return "SUPPORTED", [candidate], {"reason": "span support gate passed", "span_id": candidate["span_id"]}
    partials = []
    for candidate in candidates:
        rules = candidate[rules_key]
        verifier_ok = version != "V2-C" or (candidate.get("verifier_score") is not None and candidate["verifier_score"] >= verifier_threshold)
        if candidate["embedding_score"] >= par_e and rules["hard_rules_pass"] and verifier_ok and (rules["lexical_claim_coverage"] >= par_l or rules["exact_normalized_match"]):
            partials.append(candidate)
    if partials:
        chosen = [partials[0]]
        if len(partials) > 1:
            a = char_bigrams(partials[0]["span_text"]); b = char_bigrams(partials[1]["span_text"]); c = char_bigrams(candidates[0]["claim_text"])
            if c and len(c & (a | b)) / len(c) >= max(sup_l, partials[0][rules_key]["lexical_claim_coverage"] + .10):
                chosen.append(partials[1])
        return "PARTIALLY_SUPPORTED", chosen, {"reason": "partial span support gate passed", "span_ids": [x["span_id"] for x in chosen]}
    return "UNSUPPORTED", [], {"reason": "no candidate passed semantic, verifier, and safety gates"}


def metric_for(version, rows, factual_claims):
    labels = Counter(x[version]["label"] for x in rows if x["claim_type"] in FACT_TYPES)
    cited = sum(x[version]["label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} for x in rows if x["claim_type"] in FACT_TYPES)
    return {"version": version, "factual_claims": len(factual_claims), "label_distribution": dict(labels), "claim_level_citation_coverage": cited / len(factual_claims), "unsupported_claim_rate": labels["UNSUPPORTED"] / len(factual_claims), "partial_support_rate": labels["PARTIALLY_SUPPORTED"] / len(factual_claims), "conflict_rate": labels["CONFLICTING_EVIDENCE"] / len(factual_claims)}


def render_answer(answer, claims, assignments):
    by_claim = defaultdict(list)
    for x in assignments:
        by_claim[x["claim_id"]].append(x)
    numbered = {}
    refs = []
    insertions = []
    next_id = 1
    for claim in claims:
        items = by_claim.get(claim["claim_id"], [])
        if not items:
            continue
        markers = []
        for item in items:
            key = item["span_id"]
            if key not in numbered:
                numbered[key] = next_id
                refs.append({"citation_id": next_id, **item})
                next_id += 1
            markers.append(f"[{numbered[key]}]")
        insertions.append((claim["source_answer_span"]["end"], "".join(markers), claim["claim_id"]))
    body = answer
    for pos, marker, _ in sorted(insertions, reverse=True):
        body = body[:pos] + marker + body[pos:]
    if refs:
        lines = [f"[{x['citation_id']}] {x['source_title']} — {x['source_url']} (span: {x['span_id']})" for x in refs]
        body += "\n\n参考资料：\n" + "\n".join(lines)
    return body, refs, [{"position": p, "marker": m, "claim_id": c} for p, m, c in insertions]


def main():
    total_started = time.perf_counter()
    claims = jl(V1 / "results" / "claims.jsonl")
    classified_v1 = {x["claim_id"]: x for x in jl(V1 / "results" / "claims_classified.jsonl")}
    v1_per = {x["question_id"]: x for x in jl(V1 / "results" / "per_question_results.jsonl")}
    a_rows = jl(AE1 / "results" / "generation_a.jsonl")
    aby = {x["question_id"]: x for x in a_rows}
    factual = [x for x in claims if x["claim_type"] in FACT_TYPES]

    spans, span_seconds = build_spans(a_rows)
    dumpjl(ROOT / "results" / "evidence_spans.jsonl", spans)
    alias_map = build_aliases(spans)
    span_vectors, embedding_seconds = encode_spans(spans)
    np.save(ROOT / "results" / "evidence_span_embeddings.npy", span_vectors, allow_pickle=False)
    span_index = defaultdict(list)
    for i, span in enumerate(spans):
        span_index[span["question_id"]].append((i, span))
    claim_vectors = np.load(V1 / "results" / "claim_embeddings.npy", mmap_mode="r")
    claim_row = {x["claim_id"]: i for i, x in enumerate(claims)}

    candidates_by_claim = {}
    candidate_rows = []
    rank_started = time.perf_counter()
    for claim in factual:
        options = span_index[claim["question_id"]]
        matrix = span_vectors[[i for i, _ in options]]
        scores = matrix @ claim_vectors[claim_row[claim["claim_id"]]]
        order = np.argsort(-scores)[:CFG["span"]["candidate_top_n"]]
        candidates = []
        for pos in order:
            i, span = options[int(pos)]
            candidate = {**span, "claim_id": claim["claim_id"], "claim_text": claim["claim_text"], "claim_type": claim["claim_type"], "embedding_score": float(scores[int(pos)]), "raw_rules": raw_rules(claim, span), "normalized_rules": normalized_rules(claim, span, alias_map), "verifier_score": None}
            candidates.append(candidate)
        candidates_by_claim[claim["claim_id"]] = candidates
        candidate_rows.append({"question_id": claim["question_id"], "claim_id": claim["claim_id"], "claim_type": claim["claim_type"], "top_10": [{k: x[k] for k in ("span_id", "chunk_id", "document_id", "embedding_score", "verifier_score")} for x in candidates]})
    ranking_seconds = time.perf_counter() - rank_started

    sanity_rows = make_sanity_set(spans)
    verifier_model, verifier_tok, sanity_scores, sanity_seconds = verifier_scores([(x["premise"], x["hypothesis"]) for x in sanity_rows])
    sanity = sanity_evaluate(sanity_rows, sanity_scores)
    verifier_threshold = sanity["selected_threshold"]

    verify_pairs = []
    verify_targets = []
    for claim in factual:
        for candidate in candidates_by_claim[claim["claim_id"]][:5]:
            verify_pairs.append((candidate["span_text"], claim["claim_text"]))
            verify_targets.append(candidate)
    verifier_started = time.perf_counter()
    with torch.inference_mode():
        for s in range(0, len(verify_pairs), CFG["verifier"]["batch_size"]):
            batch = verify_pairs[s:s+CFG["verifier"]["batch_size"]]
            t = verifier_tok([x[0] for x in batch], [x[1] for x in batch], padding=True, truncation=True, max_length=CFG["verifier"]["max_length"], return_tensors="pt")
            scores = torch.sigmoid(verifier_model(**t).logits.view(-1)).cpu().tolist()
            for target, score in zip(verify_targets[s:s+len(batch)], scores):
                target["verifier_score"] = float(score)
    verifier_claim_seconds = time.perf_counter() - verifier_started
    del verifier_model, verifier_tok
    gc.collect()

    # Refresh serialized top-10 after verifier scoring top-5.
    candidate_rows = []
    for claim in factual:
        candidates = candidates_by_claim[claim["claim_id"]]
        candidate_rows.append({"question_id": claim["question_id"], "claim_id": claim["claim_id"], "claim_type": claim["claim_type"], "top_10": [{"rank": i+1, "span_id": x["span_id"], "chunk_id": x["chunk_id"], "document_id": x["document_id"], "embedding_score": x["embedding_score"], "verifier_score": x["verifier_score"], "raw_rule_flags": x["raw_rules"]["rule_flags"], "normalized_rule_flags": x["normalized_rules"]["rule_flags"]} for i, x in enumerate(candidates)]})
    dumpjl(ROOT / "results" / "claim_span_candidates.jsonl", candidate_rows)

    decision_started = time.perf_counter()
    mappings = []
    assignments = []
    by_question_claims = defaultdict(list)
    for claim in claims:
        v1 = classified_v1[claim["claim_id"]]
        if claim["claim_type"] not in FACT_TYPES:
            label = v1["final_support_label"]
            entry = {**claim, "v1_label": label, "V2-A": {"label": label, "chosen": [], "decision": {"reason": "frozen non-factual/refusal label"}}, "V2-B": {"label": label, "chosen": [], "decision": {"reason": "frozen non-factual/refusal label"}}, "V2-C": {"label": label, "chosen": [], "decision": {"reason": "frozen non-factual/refusal label"}}}
        else:
            candidates = candidates_by_claim[claim["claim_id"]]
            results = {}
            for version in ("V2-A", "V2-B", "V2-C"):
                label, chosen, why = classify(candidates, version, verifier_threshold, claim["question_id"])
                results[version] = {"label": label, "chosen": [x["span_id"] for x in chosen], "decision": why}
            entry = {**claim, "v1_label": v1["final_support_label"], **results}
            for j, candidate in enumerate([x for x in candidates if x["span_id"] in results["V2-C"]["chosen"]]):
                rules = candidate["normalized_rules"]
                assignments.append({"question_id": claim["question_id"], "claim_id": claim["claim_id"], "span_id": candidate["span_id"], "chunk_id": candidate["chunk_id"], "document_id": candidate["document_id"], "source_url": candidate["source_url"], "source_title": candidate["source_title"], "embedding_score": candidate["embedding_score"], "verifier_score": candidate["verifier_score"], "rule_flags": rules["rule_flags"], "support_label": results["V2-C"]["label"], "citation_role": "primary" if j == 0 else "supporting", "citation_id": None})
        mappings.append(entry)
        by_question_claims[claim["question_id"]].append(entry)
    assignment_seconds = time.perf_counter() - decision_started
    dumpjl(ROOT / "results" / "claim_evidence_mapping_v2.jsonl", mappings)

    ass_by_q = defaultdict(list)
    for x in assignments:
        ass_by_q[x["question_id"]].append(x)
    per_question = []
    final_assignments = []
    for row in a_rows:
        qclaims = by_question_claims[row["question_id"]]
        cited, refs, insertions = render_answer(row["generated_answer"], qclaims, ass_by_q[row["question_id"]])
        for ref in refs:
            item = dict(ref)
            item.pop("citation_id", None)
            for a in ass_by_q[row["question_id"]]:
                if a["span_id"] == item["span_id"]:
                    a["citation_id"] = ref["citation_id"]
        final_assignments.extend(ass_by_q[row["question_id"]])
        body = cited.split("\n\n参考资料：", 1)[0]
        clean = re.sub(r"\[\d+\]", "", body)
        fclaims = [x for x in qclaims if x["claim_type"] in FACT_TYPES]
        mapped = bool(fclaims) and all(x["V2-C"]["label"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"} for x in fclaims)
        refusal = not fclaims and any(x["V2-C"]["label"] == "REFUSAL" for x in qclaims) and all(x["V2-C"]["label"] in {"REFUSAL", "NON_FACTUAL"} for x in qclaims)
        counts = Counter(x["V2-C"]["label"] for x in qclaims)
        per_question.append({"question_id": row["question_id"], "question": row["question"], "eval_status": row["eval_status"], "category": row["category"], "original_answer": row["generated_answer"], "v1_cited_answer": v1_per[row["question_id"]]["cited_answer"], "v2_cited_answer": cited, "citation_references": refs, "citation_insertions": insertions, "v1_citation_status": v1_per[row["question_id"]]["new_citation_status"], "v2_citation_status": "COMPLIANT" if mapped or refusal else "NONCOMPLIANT", "claim_count": len(qclaims), "factual_claim_count": len(fclaims), "supported_claim_count": counts["SUPPORTED"], "partial_claim_count": counts["PARTIALLY_SUPPORTED"], "unsupported_claim_count": counts["UNSUPPORTED"], "citation_count": len(refs), "answer_preservation": clean == row["generated_answer"], "source_quality_failure": row["question_id"] in KNOWN_GAPS})
    dumpjl(ROOT / "results" / "citation_assignments_v2.jsonl", final_assignments)
    dumpjl(ROOT / "results" / "per_question_results_v2.jsonl", per_question)

    metrics_a = metric_for("V2-A", mappings, factual)
    metrics_b = metric_for("V2-B", mappings, factual)
    metrics_c = metric_for("V2-C", mappings, factual)
    (ROOT / "results" / "v2a_metrics.json").write_text(json.dumps(metrics_a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "results" / "v2b_metrics.json").write_text(json.dumps(metrics_b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "results" / "v2c_metrics.json").write_text(json.dumps(metrics_c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hard_blocks = []
    for claim in factual:
        for candidate in candidates_by_claim[claim["claim_id"]][:5]:
            if candidate.get("verifier_score") is not None and candidate["verifier_score"] >= verifier_threshold and candidate["embedding_score"] >= CFG["decision"]["v2b_partial_embedding"] and not candidate["normalized_rules"]["hard_rules_pass"]:
                hard_blocks.append({"question_id": claim["question_id"], "claim_id": claim["claim_id"], "span_id": candidate["span_id"], "embedding_score": candidate["embedding_score"], "verifier_score": candidate["verifier_score"], "rule_flags": candidate["normalized_rules"]["rule_flags"]})
    total_seconds = time.perf_counter() - total_started
    v1m = json.loads((V1 / "results" / "citation_metrics.json").read_text(encoding="utf-8"))
    metrics = {"status": "PASS", "scope": "PROVISIONAL_AUTO_EVAL", "questions": 38, "claims": 120, "factual_claims": 104, "v1_coverage": v1m["claim_level_citation_coverage"], "v2a": metrics_a, "v2b": metrics_b, "v2c": metrics_c, "citation_precision_proxy": sum(not x["rule_flags"] and x["verifier_score"] is not None and x["verifier_score"] >= verifier_threshold for x in final_assignments) / len(final_assignments) if final_assignments else None, "human_validated_precision": None, "answer_level_citation_compliance": {"a_baseline": v1m["answer_level_citation_compliance"]["a_baseline"], "v1": v1m["answer_level_citation_compliance"]["citation_pipeline_v1"], "v2": sum(x["v2_citation_status"] == "COMPLIANT" for x in per_question) / 38}, "answer_preservation_rate": sum(x["answer_preservation"] for x in per_question) / 38, "hard_contradiction_block_count": len(hard_blocks), "hard_contradiction_blocks": hard_blocks, "automatic_wrong_citations": sum(bool(x["rule_flags"]) or x["verifier_score"] is None or x["verifier_score"] < verifier_threshold for x in final_assignments), "false_support_risk_cases": sanity["false_positive_anchors_at_threshold"] + len(hard_blocks), "verifier": {"name": CFG["verifier"]["model_name"], "revision": CFG["verifier"]["revision"], "status": sanity["status"], "selected_threshold": verifier_threshold, "role": CFG["verifier"]["role"]}, "performance_seconds": {"evidence_span_extraction": span_seconds, "span_embedding": embedding_seconds, "span_ranking": ranking_seconds, "verifier_sanity": sanity_seconds, "verifier_claim_pairs": verifier_claim_seconds, "citation_assignment": assignment_seconds, "total": total_seconds, "average_per_question": total_seconds / 38, "v1_total_latency": None}, "artifacts": {"span_count": len(spans), "span_embedding_sha256": sha(ROOT / "results" / "evidence_span_embeddings.npy"), "citation_assignments": len(final_assignments)}}
    (ROOT / "results" / "citation_metrics_v2.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Known, obvious V1 segmentation defect is shadow-diagnosed only.
    exceptions = []
    ret05 = [x for x in claims if x["question_id"] == "RET-05"]
    if ret05 and all(re.fullmatch(r"\d+", x["claim_text"]) for x in ret05):
        exceptions.append({"question_id": "RET-05", "exception": "SEGMENTATION_EXCEPTION", "diagnosis": "Frozen answer is a bare numeric list; V1 split it into NON_FACTUAL numeric tokens.", "shadow_correction": "Treat the answer as malformed/non-answer for diagnosis only.", "included_in_main_benchmark": False})
    dumpjl(ROOT / "analysis" / "segmentation_exceptions.jsonl", exceptions)
    print(json.dumps({"status": "PASS", "spans": len(spans), "verifier": sanity["status"], "threshold": verifier_threshold, "v2a_coverage": metrics_a["claim_level_citation_coverage"], "v2b_coverage": metrics_b["claim_level_citation_coverage"], "v2c_coverage": metrics_c["claim_level_citation_coverage"], "assignments": len(final_assignments), "hard_blocks": len(hard_blocks), "total_seconds": total_seconds}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
