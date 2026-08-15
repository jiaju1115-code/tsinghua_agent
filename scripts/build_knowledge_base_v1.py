"""Build a fail-closed Canonical Knowledge Base V1 and Dense Retrieval V1 bundle.

This builder only reads historical assets. It refuses to overwrite a V1 target,
never calls network services or LLMs, and produces a separate provenance trail.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "data" / "03_knowledge_base" / "v1"
PUBLIC_ROOT = ROOT / "data" / "02_public_expansion" / "v2"
RESTRICTED_ROOT = ROOT / "data" / "05_restricted_expansion" / "v1"
RAG_V1 = ROOT / "evaluation" / "rag" / "v1"

MODEL_REVISION = "7999e1d3359715c523056ef9478215996d62a620"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
CHUNKING = {"normalization": "NFKC; CRLF->LF; trim horizontal whitespace; collapse >=3 blank lines; remove restricted Auth/Discovery acquisition lines", "max_chars": 800, "overlap_chars": 120, "min_chars": 80, "boundary": "prefer latest paragraph/sentence/newline boundary after 55% of max_chars"}
RETRIEVER = {"retriever_version": "RAG_RETRIEVAL_V1", "retriever_type": "dense_flat_cosine_numpy", "model_name": MODEL_NAME, "model_revision": MODEL_REVISION, "query_instruction": QUERY_INSTRUCTION, "bilingual_expansion": False, "top_k": 5, "max_length": 512, "batch_size": 16, "document_input": "title + newline + chunk_text", "pooling": "CLS last_hidden_state[:,0]", "normalization": "L2", "similarity_metric": "dot product on L2-normalized vectors (cosine)", "tie_breaking": "score descending, then chunk_id ascending"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def is_within_project(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def normalize_document(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for raw in text.split("\n"):
        line = re.sub(r"[\t \u3000]+", " ", raw).strip()
        if re.match(r"^-\s*(Auth|Discovery)\s*:", line, flags=re.I):
            continue
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def pick_break(text: str, start: int, hard_end: int, min_end: int) -> int:
    candidates = []
    for match in re.finditer(r"\n\n|[。！？!?；;]\s*|\n", text[start:hard_end]):
        candidate = start + match.end()
        if candidate >= min_end:
            candidates.append(candidate)
    return candidates[-1] if candidates else hard_end


def chunk_text(text: str) -> list[tuple[int, int, str]]:
    if not text:
        return []
    chunks: list[tuple[int, int, str]] = []
    start, size = 0, len(text)
    while start < size:
        hard_end = min(size, start + CHUNKING["max_chars"])
        end = pick_break(text, start, hard_end, start + int(CHUNKING["max_chars"] * 0.55)) if hard_end < size else size
        piece = text[start:end].strip()
        if piece:
            chunks.append((start, end, piece))
        if end >= size:
            break
        next_start = max(start + 1, end - CHUNKING["overlap_chars"])
        while next_start < end and not text[next_start].isspace():
            next_start += 1
        while next_start < size and text[next_start].isspace():
            next_start += 1
        start = next_start
    if len(chunks) > 1 and len(chunks[-1][2]) < CHUNKING["min_chars"]:
        start0, _, previous = chunks[-2]
        _, end1, final = chunks[-1]
        merged = (previous + "\n\n" + final).strip()
        if len(merged) <= CHUNKING["max_chars"] + CHUNKING["min_chars"]:
            chunks[-2:] = [(start0, end1, merged)]
    return chunks


def git_state() -> dict[str, Any]:
    def call(*args: str) -> str:
        try:
            return subprocess.check_output(args, cwd=ROOT, text=True, encoding="utf-8").strip()
        except Exception as exc:
            return f"UNRESOLVED: {type(exc).__name__}: {exc}"
    return {"commit": call("git", "rev-parse", "HEAD"), "branch": call("git", "branch", "--show-current"), "status_porcelain": call("git", "status", "--short")}


def historical_snapshot() -> dict[str, str]:
    # Only immutable historical inputs and results are listed; the new KB and active
    # project map are deliberately not in this set.
    roots = [
        ROOT / "data" / "01_public_baseline",
        ROOT / "data" / "02_public_expansion" / "v2",
        ROOT / "data" / "04_public_staging",
        ROOT / "data" / "05_restricted_expansion" / "v1",
        ROOT / "data" / "06_human_annotation",
        ROOT / "evaluation" / "rag" / "v0",
        ROOT / "evaluation" / "rag" / "v1",
        ROOT / "evaluation" / "answer_generation",
        ROOT / "evaluation" / "citation",
        ROOT / "evaluation" / "prompt_v3_2_blind_test_v1",
        ROOT / "experiments" / "router_v0_2",
        ROOT / "experiments" / "web_search_v0_followup",
        ROOT / "experiments" / "e2e12_router_v0_2",
        ROOT / "experiments" / "evidence_sufficiency_v0_1",
        ROOT / "experiments" / "evidence_sufficiency_v0_2",
        ROOT / "experiments" / "evidence_sufficiency_v0_3",
        ROOT / "experiments" / "evidence_sufficiency_v0_4",
        ROOT / "prompts",
    ]
    rows: dict[str, str] = {}
    for base in roots:
        if base.is_dir():
            for path in sorted(p for p in base.rglob("*") if p.is_file() and is_within_project(p)):
                rows[relative(path)] = sha256_file(path)
    return rows


def extract_human_conflict_urls() -> dict[str, dict[str, str]]:
    path = PUBLIC_ROOT / "human_check" / "public_v3_2_human_check_disagreements.jsonl"
    conflicts = {}
    if not path.is_file():
        return conflicts
    for row in read_jsonl(path):
        if str(row.get("human_action", "")).strip() in {"review", "reject"} and str(row.get("v3_2_action", "")).strip() == "approve":
            conflicts[str(row.get("url", "")).strip()] = {"human_action": str(row.get("human_action", "")).strip(), "check_id": str(row.get("check_id", ""))}
    return conflicts


def public_decisions() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results = read_jsonl(PUBLIC_ROOT / "audit" / "public_expansion_v2_v3_2_results.jsonl")
    quality = {row["id"]: row for row in read_jsonl(PUBLIC_ROOT / "quality_gate" / "canonical_audit_candidates.jsonl")}
    conflicts = extract_human_conflict_urls()
    included, decisions = [], []
    seen_urls, seen_hashes = set(), set()
    for row in sorted(results, key=lambda item: item["id"]):
        q = quality.get(row["id"])
        original = PUBLIC_ROOT / str(row.get("source_file", ""))
        reasons = []
        unresolved = False
        if row.get("action") != "approve" or row.get("v3_2_action") != "approve" or row.get("data_status") != "candidate_approved":
            reasons.append(f"review_status={row.get('action')}")
            unresolved = row.get("action") == "review"
        if not q or not q.get("ok") or not q.get("quality_gate_pass"):
            reasons.append("quality_gate_not_confirmed")
            unresolved = True
        if row.get("quality_class") != "detail_content" or (q and q.get("quality_class") != "detail_content"):
            reasons.append(f"quality_class={row.get('quality_class')}")
        if row.get("time_status") != "evergreen":
            reasons.append(f"time_status={row.get('time_status')}")
        if str(row.get("url", "")) in conflicts:
            reasons.append(f"human_reference_conflict={conflicts[str(row.get('url'))]['human_action']}")
            unresolved = True
        if not original.is_file() or original.stat().st_size == 0:
            reasons.append("source_file_missing_or_empty")
            unresolved = True
        raw = original.read_bytes() if original.is_file() else b""
        raw_hash = sha256_bytes(raw) if raw else ""
        url = str(row.get("normalized_url") or row.get("url") or "")
        if url in seen_urls:
            reasons.append("duplicate_normalized_url")
            unresolved = True
        if raw_hash and raw_hash in seen_hashes:
            reasons.append("duplicate_raw_source_hash")
            unresolved = True
        status = "include" if not reasons else ("unresolved_excluded" if unresolved else "excluded")
        decision = {"canonical_source_id": f"KBV1-PUB-{row['id']}", "original_source_id": row["id"], "layer": "public", "status": status, "reasons": reasons, "original_file_path": relative(original) if original.is_file() else str(original), "original_file_sha256": raw_hash, "declared_content_hash": row.get("content_hash", ""), "review_status": row.get("action", ""), "time_status": row.get("time_status", ""), "quality_class": row.get("quality_class", ""), "url": row.get("url", "")}
        decisions.append(decision)
        if status == "include":
            seen_urls.add(url)
            seen_hashes.add(raw_hash)
            included.append({"canonical_source_id": decision["canonical_source_id"], "original_source_id": row["id"], "source_type": "public", "title": row.get("title", ""), "url": row.get("url", ""), "normalized_url": url, "domain": row.get("domain", ""), "category": row.get("category", ""), "content_type": row.get("content_type", ""), "time_status": row.get("time_status", ""), "valid_from": row.get("valid_from", ""), "valid_until": row.get("valid_until", ""), "review_status": row.get("action", ""), "inclusion_reason": "V3.2 approve + candidate_approved + canonical quality gate pass + detail_content + evergreen + source body present", "original_file": original, "original_file_sha256": raw_hash, "declared_content_hash": row.get("content_hash", ""), "review_artifact": relative(PUBLIC_ROOT / "audit" / "public_expansion_v2_v3_2_results.jsonl"), "quality_artifact": relative(PUBLIC_ROOT / "quality_gate" / "canonical_audit_candidates.jsonl"), "human_reference": "No conflicting sampled human reference located by normalized URL"})
    return included, decisions


def restricted_decisions() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results = read_jsonl(RESTRICTED_ROOT / "audit" / "restricted_v3_2_results.jsonl")
    safety = {row.get("restricted_id"): row for row in read_jsonl(RESTRICTED_ROOT / "safety_gate" / "private_sensitive_gate_results_consolidated.jsonl") if row.get("restricted_id")}
    included, decisions = [], []
    seen_urls, seen_hashes = set(), set()
    for row in sorted(results, key=lambda item: item["restricted_id"]):
        ident = row["restricted_id"]
        original = RESTRICTED_ROOT / str(row.get("source_file", ""))
        safety_row = safety.get(ident)
        reasons = []
        unresolved = False
        if row.get("action") != "approve" or row.get("v3_2_action") != "approve" or row.get("data_status") != "restricted_candidate_approved":
            reasons.append(f"review_status={row.get('action')}")
            unresolved = row.get("action") == "review"
        if row.get("private_sensitive_status") != "safe_general_content" or not safety_row or safety_row.get("private_sensitive_status") != "safe_general_content":
            reasons.append("safety_gate_not_confirmed_safe_general_content")
            unresolved = True
        if row.get("quality_class") != "detail_content":
            reasons.append(f"quality_class={row.get('quality_class')}")
        if row.get("time_status") != "evergreen":
            reasons.append(f"time_status={row.get('time_status')}")
        if not original.is_file() or original.stat().st_size == 0:
            reasons.append("source_file_missing_or_empty")
            unresolved = True
        raw = original.read_bytes() if original.is_file() else b""
        raw_hash = sha256_bytes(raw) if raw else ""
        url = str(row.get("normalized_url") or row.get("url") or "")
        if url in seen_urls:
            reasons.append("duplicate_normalized_url")
            unresolved = True
        if raw_hash and raw_hash in seen_hashes:
            reasons.append("duplicate_raw_source_hash")
            unresolved = True
        status = "include" if not reasons else ("unresolved_excluded" if unresolved else "excluded")
        decision = {"canonical_source_id": f"KBV1-RES-{ident}", "original_source_id": ident, "layer": "restricted", "status": status, "reasons": reasons, "original_file_path": relative(original) if original.is_file() else str(original), "original_file_sha256": raw_hash, "declared_content_hash": row.get("content_hash", ""), "review_status": row.get("action", ""), "time_status": row.get("time_status", ""), "quality_class": row.get("quality_class", ""), "url": row.get("url", "")}
        decisions.append(decision)
        if status == "include":
            seen_urls.add(url)
            seen_hashes.add(raw_hash)
            included.append({"canonical_source_id": decision["canonical_source_id"], "original_source_id": ident, "source_type": "restricted", "title": row.get("title", ""), "url": row.get("url", ""), "normalized_url": url, "domain": row.get("domain", ""), "category": row.get("category", ""), "content_type": row.get("content_type", ""), "time_status": row.get("time_status", ""), "valid_from": row.get("valid_from", ""), "valid_until": row.get("valid_until", ""), "review_status": row.get("action", ""), "inclusion_reason": "V3.2 approve + restricted_candidate_approved + detail_content + evergreen + safe_general_content in both candidate and consolidated safety gate + source body present", "original_file": original, "original_file_sha256": raw_hash, "declared_content_hash": row.get("content_hash", ""), "review_artifact": relative(RESTRICTED_ROOT / "audit" / "restricted_v3_2_results.jsonl"), "quality_artifact": relative(RESTRICTED_ROOT / "quality_gate" / "restricted_quality_gate_results.jsonl"), "safety_artifact": relative(RESTRICTED_ROOT / "safety_gate" / "private_sensitive_gate_results_consolidated.jsonl"), "human_reference": "No human reference is asserted for restricted inclusion"})
    return included, decisions


def copy_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    manifests = []
    for source in sources:
        destination = KB / "sources" / source["source_type"] / f"{source['canonical_source_id']}.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source["original_file"], destination)
        if sha256_file(destination) != source["original_file_sha256"]:
            raise RuntimeError(f"byte copy hash mismatch: {source['canonical_source_id']}")
        manifests.append({k: v for k, v in source.items() if k not in {"original_file"}} | {"original_file_path": relative(source["original_file"]), "canonical_file_path": relative(destination), "source_sha256": sha256_file(destination), "source_bytes": destination.stat().st_size})
    return sorted(manifests, key=lambda row: row["canonical_source_id"])


def build_chunks(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = []
    normalized_dir = KB / "provenance" / "normalized_source_text"
    for source in sources:
        text = normalize_document((ROOT / source["canonical_file_path"]).read_text(encoding="utf-8"))
        normalized_file = normalized_dir / f"{source['canonical_source_id']}.txt"
        normalized_file.parent.mkdir(parents=True, exist_ok=True)
        normalized_file.write_text(text + "\n", encoding="utf-8", newline="\n")
        for index, (start, end, piece) in enumerate(chunk_text(text), 1):
            suffix = source["original_source_id"].replace("RESV1-", "RESV1-").replace("PUBV2C-", "PUBV2C-")
            chunks.append({"chunk_id": f"KBV1-CHUNK-{suffix}-{index:04d}", "canonical_source_id": source["canonical_source_id"], "original_source_id": source["original_source_id"], "source_type": source["source_type"], "title": source["title"], "url": source["url"], "category": source["category"], "chunk_index": index, "char_start": start, "char_end": end, "text": piece, "chunk_sha256": sha256_bytes(piece.encode("utf-8")), "normalized_source_sha256": sha256_file(normalized_file), "canonical_file_path": source["canonical_file_path"]})
    return chunks


def copy_model() -> Path:
    source = RAG_V1 / "indexes" / "dense" / "model"
    destination = KB / "index" / "model"
    required = ["config.json", "config_sentence_transformers.json", "modules.json", "model.safetensors", "sentence_bert_config.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt", "1_Pooling/config.json"]
    for name in required:
        if not (source / name).is_file():
            raise RuntimeError(f"frozen dense model input missing: {source / name}")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
        if sha256_file(source / name) != sha256_file(target):
            raise RuntimeError(f"model copy hash mismatch: {name}")
    return destination


def encode_documents(chunks: list[dict[str, Any]], model_path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModel.from_pretrained(model_path, local_files_only=True).eval()
    vectors = []
    texts = [f"{row['title']}\n{row['text']}" for row in chunks]
    started = datetime.now(timezone.utc)
    with torch.inference_mode():
        for offset in range(0, len(texts), RETRIEVER["batch_size"]):
            tokens = tokenizer(texts[offset:offset + RETRIEVER["batch_size"]], padding=True, truncation=True, max_length=RETRIEVER["max_length"], return_tensors="pt")
            value = model(**tokens).last_hidden_state[:, 0]
            vectors.append(torch.nn.functional.normalize(value, p=2, dim=1).cpu().numpy().astype(np.float32))
    array = np.concatenate(vectors, axis=0)
    norms = np.linalg.norm(array, axis=1)
    report = {"encoding_started_utc": started.isoformat(), "embedding_rows": int(array.shape[0]), "embedding_dimension": int(array.shape[1]), "l2_norm_min": float(norms.min()), "l2_norm_max": float(norms.max()), "cosine_ready": bool(np.allclose(norms, 1.0, atol=1e-4)), "torch_version": torch.__version__, "device": "cpu"}
    return array, report


def _all_json_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _all_json_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_json_objects(item)


def normalize_query(query: str) -> str:
    value = unicodedata.normalize("NFKC", query).lower().strip()
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)


def build_exclusion_registry() -> dict[str, Any]:
    targets = [
        ROOT / "experiments" / "router_v0_2", ROOT / "experiments" / "web_search_v0_followup", ROOT / "experiments" / "e2e12_router_v0_2",
        ROOT / "evaluation" / "rag" / "v0", ROOT / "evaluation" / "rag" / "v1", ROOT / "evaluation" / "answer_generation", ROOT / "evaluation" / "citation",
        ROOT / "experiments" / "evidence_sufficiency_v0_1", ROOT / "experiments" / "evidence_sufficiency_v0_2", ROOT / "experiments" / "evidence_sufficiency_v0_3", ROOT / "experiments" / "evidence_sufficiency_v0_4",
        ROOT / "evaluation" / "prompt_v3_2_blind_test_v1", PUBLIC_ROOT / "human_check",
    ]
    fields = ("query", "question", "candidate_user_question", "user_question")
    rows = []
    for base in targets:
        if not base.is_dir():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file() and is_within_project(p) and p.suffix.lower() in {".json", ".jsonl"}):
            try:
                if path.suffix.lower() == ".jsonl":
                    values = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
                else:
                    values = [json.loads(path.read_text(encoding="utf-8-sig"))]
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            for item in _all_json_objects(values):
                raw = next((item[key] for key in fields if isinstance(item.get(key), str) and item[key].strip()), None)
                if raw is None or len(raw) > 2000:
                    continue
                source_ids = item.get("source_ids") or item.get("expected_source_id") or item.get("source_id") or item.get("original_id") or ""
                evidence = item.get("frozen_evidence") or item.get("evidence_ids") or item.get("evidence_id") or ""
                evidence_ids = [str(x.get("source_id") or x.get("evidence_id") or "") for x in evidence] if isinstance(evidence, list) else evidence
                pair_value = {"normalized_query": normalize_query(raw), "source_evidence_ids": evidence_ids or source_ids}
                rows.append({"source_dataset": relative(path), "query_id": str(item.get("query_id") or item.get("id") or item.get("sample_id") or item.get("record_id") or item.get("check_id") or ""), "raw_query": raw, "raw_query_sha256": sha256_bytes(raw.encode("utf-8")), "normalized_query": normalize_query(raw), "normalized_query_sha256": sha256_bytes(normalize_query(raw).encode("utf-8")), "source_evidence_ids": evidence_ids or source_ids, "query_evidence_canonical_sha256": sha256_bytes(canonical_json(pair_value)), "template_family": str(item.get("template_family") or item.get("transformation") or item.get("construction_type") or ""), "exclusion_reason": "historical_QA_benchmark_calibration_or_human_check"})
    rows.sort(key=lambda row: (row["source_dataset"], row["query_id"], row["raw_query_sha256"]))
    path = ROOT / "evaluation" / "e2e" / "v1" / "benchmark" / "exclusion_registry.jsonl"
    write_jsonl(path, rows)
    return {"path": relative(path), "records": len(rows), "unique_raw_queries": len({row["raw_query_sha256"] for row in rows}), "unique_normalized_queries": len({row["normalized_query_sha256"] for row in rows}), "source_datasets": len({row["source_dataset"] for row in rows}), "sha256": sha256_file(path)}


def main() -> None:
    if KB.exists():
        raise SystemExit(f"Refusing to overwrite existing Knowledge Base V1: {KB}")
    pre = historical_snapshot()
    public, public_audit = public_decisions()
    restricted, restricted_audit = restricted_decisions()
    sources = sorted(public + restricted, key=lambda row: row["canonical_source_id"])
    if not sources:
        raise SystemExit("No eligible sources; refusing to create an empty V1 runtime corpus")
    KB.mkdir(parents=True)
    for directory in ("sources", "chunks", "index", "manifests", "provenance", "config", "audit"):
        (KB / directory).mkdir(parents=True, exist_ok=True)
    source_manifest = copy_sources(sources)
    write_jsonl(KB / "manifests" / "source_manifest.jsonl", source_manifest)
    write_jsonl(KB / "provenance" / "source_provenance.jsonl", source_manifest)
    decisions = sorted(public_audit + restricted_audit, key=lambda row: row["canonical_source_id"])
    write_jsonl(KB / "audit" / "eligibility_decisions.jsonl", decisions)
    chunks = build_chunks(source_manifest)
    write_jsonl(KB / "chunks" / "chunks.jsonl", chunks)
    chunk_manifest = [{k: v for k, v in row.items() if k != "text"} | {"text_chars": len(row["text"])} for row in chunks]
    write_jsonl(KB / "manifests" / "chunk_manifest.jsonl", chunk_manifest)
    mapping = [{"canonical_source_id": source["canonical_source_id"], "chunk_ids": [chunk["chunk_id"] for chunk in chunks if chunk["canonical_source_id"] == source["canonical_source_id"]]} for source in source_manifest]
    write_jsonl(KB / "manifests" / "source_to_chunk_mapping.jsonl", mapping)
    write_json(KB / "config" / "chunking_v1.json", CHUNKING)
    model_path = copy_model()
    embeddings, index_report = encode_documents(chunks, model_path)
    embedding_path = KB / "index" / "document_embeddings.npy"
    np.save(embedding_path, embeddings, allow_pickle=False)
    row_mapping = [{"embedding_row": index, "chunk_id": row["chunk_id"], "canonical_source_id": row["canonical_source_id"]} for index, row in enumerate(chunks)]
    write_jsonl(KB / "index" / "row_mapping.jsonl", row_mapping)
    index_report |= {"index_type": RETRIEVER["retriever_type"], "similarity_metric": RETRIEVER["similarity_metric"], "source_chunk_count": len(chunks), "embedding_sha256": sha256_file(embedding_path), "row_mapping_sha256": sha256_file(KB / "index" / "row_mapping.jsonl"), "model_weights_sha256": sha256_file(model_path / "model.safetensors")}
    write_json(KB / "index" / "index_manifest.json", index_report)
    retriever_config = RETRIEVER | {"corpus_version": "KNOWLEDGE_BASE_V1", "artifacts": {"chunks_path": "chunks/chunks.jsonl", "embeddings_path": "index/document_embeddings.npy", "model_path": "index/model"}, "artifact_sha256": {"chunks/chunks.jsonl": sha256_file(KB / "chunks" / "chunks.jsonl"), "index/document_embeddings.npy": sha256_file(embedding_path), "index/row_mapping.jsonl": sha256_file(KB / "index" / "row_mapping.jsonl"), "index/model/model.safetensors": sha256_file(model_path / "model.safetensors")}}
    write_json(KB / "config" / "retriever_v1.json", retriever_config)
    excluded = [row for row in decisions if row["status"] != "include"]
    unresolved = [row for row in decisions if row["status"] == "unresolved_excluded"]
    source_manifest_hash = sha256_file(KB / "manifests" / "source_manifest.jsonl")
    provenance_hash = sha256_file(KB / "provenance" / "source_provenance.jsonl")
    freeze = {"knowledge_base_version": "KNOWLEDGE_BASE_V1", "status": "KNOWLEDGE_BASE_V1_FROZEN", "source_count": len(source_manifest), "public_count": sum(row["source_type"] == "public" for row in source_manifest), "restricted_count": sum(row["source_type"] == "restricted" for row in source_manifest), "excluded_count": len(excluded), "unresolved_count": len(unresolved), "runtime_review_reject_unresolved_count": 0, "source_manifest_sha256": source_manifest_hash, "source_provenance_sha256": provenance_hash, "chunks_count": len(chunks), "chunks_sha256": sha256_file(KB / "chunks" / "chunks.jsonl"), "chunk_manifest_sha256": sha256_file(KB / "manifests" / "chunk_manifest.jsonl"), "index_sha256": sha256_file(embedding_path), "index_manifest_sha256": sha256_file(KB / "index" / "index_manifest.json"), "embedding_model": MODEL_NAME, "model_revision": MODEL_REVISION, "model_weights_sha256": sha256_file(model_path / "model.safetensors"), "chunking_config_sha256": sha256_file(KB / "config" / "chunking_v1.json"), "retriever_config_sha256": sha256_file(KB / "config" / "retriever_v1.json"), "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(), "git_state": git_state(), "relevant_code_hashes": {"builder": sha256_file(Path(__file__)), "runtime_adapter": sha256_file(ROOT / "src" / "retrieval_v1" / "adapter.py")}, "historical_inputs_snapshot_count": len(pre)}
    write_json(KB / "audit" / "knowledge_base_v1_freeze.json", freeze)
    (KB / "audit" / "knowledge_base_v1_freeze.json.sha256").write_text(sha256_file(KB / "audit" / "knowledge_base_v1_freeze.json") + "\n", encoding="ascii", newline="\n")
    rag_freeze = {"retrieval_bundle_version": "RAG_RETRIEVAL_V1", "status": "RAG_RETRIEVAL_V1_FROZEN", "knowledge_base_version": "KNOWLEDGE_BASE_V1", "knowledge_base_freeze_sha256": sha256_file(KB / "audit" / "knowledge_base_v1_freeze.json"), "corpus_manifest_sha256": source_manifest_hash, "chunks_sha256": sha256_file(KB / "chunks" / "chunks.jsonl"), "index_sha256": sha256_file(embedding_path), "retriever_config_sha256": sha256_file(KB / "config" / "retriever_v1.json"), "embedding_model": MODEL_NAME, "model_revision": MODEL_REVISION, "top_k": 5, "query_instruction": QUERY_INSTRUCTION, "bilingual_expansion": False, "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(), "git_state": git_state()}
    write_json(KB / "audit" / "rag_retrieval_v1_freeze.json", rag_freeze)
    (KB / "audit" / "rag_retrieval_v1_freeze.json.sha256").write_text(sha256_file(KB / "audit" / "rag_retrieval_v1_freeze.json") + "\n", encoding="ascii", newline="\n")
    exclusion = build_exclusion_registry()
    post = historical_snapshot()
    changed = sorted(set(pre) ^ set(post) | {path for path in pre if path in post and pre[path] != post[path]})
    invariance = {"status": "PASS" if not changed else "FAIL", "scope": "historical frozen inputs/results listed by builder", "files_checked": len(pre), "pre_snapshot_sha256": sha256_bytes(canonical_json(pre)), "post_snapshot_sha256": sha256_bytes(canonical_json(post)), "changed_files": changed, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    write_json(KB / "audit" / "input_invariance_report.json", invariance)
    if changed:
        raise RuntimeError("historical input invariance failed")
    readme = "# Canonical Knowledge Base V1\n\nThis directory is the sole formal runtime corpus for `RAG_RETRIEVAL_V1`. It was built fail-closed from existing approved evidence only. It is immutable: future data or retriever changes require a new V2 directory. Historical staging, RAG V0/V1 experiments, and audit materials remain provenance/legacy assets and are not runtime dependencies.\n"
    (KB / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    print(json.dumps({"status": "KNOWLEDGE_BASE_V1_FROZEN", "sources": len(source_manifest), "chunks": len(chunks), "exclusion_registry": exclusion, "invariance": invariance["status"], "kb": relative(KB)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
