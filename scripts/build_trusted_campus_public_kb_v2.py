from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.trusted_campus_agent_v2.metadata import (
    ROOT,
    V1_ROOT,
    infer_audience,
    infer_content_type,
    infer_department,
    infer_topics,
    metadata_from_v1,
    parse_iso_date,
    policy_key,
)


SOURCE_ROOT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2"
DEFAULT_OUTPUT = ROOT / "data" / "05_trusted_campus_kb_v2_public"
SCENARIOS = ("教务", "学生事务", "校园生活", "科研实践", "国际交流", "就业", "新生", "毕业")
ACTION_MARKERS = (
    "申请", "办理", "流程", "步骤", "材料", "条件", "资格", "须知", "指南", "入口", "系统",
    "截止", "时间", "地点", "下载", "证明", "成绩", "选课", "注册", "报到", "离校", "FAQ",
)
NEWS_MARKERS = (
    "新闻网", "新闻", "快讯", "纪实", "回顾", "精彩回顾", "举办", "举行", "召开", "获奖",
    "荣获", "参观", "来访", "调研", "座谈会", "论坛开幕", "人物", "故事", "风采", "一周",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = [(key, val) for key, val in parse_qsl(parts.query) if not key.lower().startswith(("utm_", "from", "scene"))]
    path = re.sub(r"/+", "/", parts.path).rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(query), ""))


def official_public(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host == "tsinghua.edu.cn" or host.endswith(".tsinghua.edu.cn") or host == "mp.weixin.qq.com"


def plain_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    text = re.sub(r"\A---\s*\n[\s\S]*?\n---\s*\n", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def date_rank(row: dict[str, Any]) -> str:
    return str(row.get("effective_date") or row.get("publish_date") or "0000-00-00")


def assess(row: dict[str, Any], text: str, today: date) -> tuple[bool, str]:
    title = str(row.get("title", ""))
    url = str(row.get("source") or row.get("url") or "")
    content_type = str(row.get("content_type") or infer_content_type(title, text))
    if row.get("access_level") == "restricted" or row.get("source_type") == "restricted":
        return False, "restricted_source"
    if not official_public(url):
        return False, "not_verified_tsinghua_source"
    if (urlsplit(url).hostname or "").lower() == "mp.weixin.qq.com" and row.get("authority_level") != "official_social":
        return False, "unverified_wechat_account"
    if len(text) < 220:
        return False, "insufficient_content"
    if any(marker in title for marker in NEWS_MARKERS):
        return False, "news_or_publicity"
    if content_type in {"organization_intro", "news", "event", "profile"}:
        return False, "non_transactional_content_type"
    expiry = parse_iso_date(row.get("expiry_date") or row.get("valid_until"))
    if expiry and expiry < today:
        return False, "expired"
    joined = f"{title}\n{text[:5000]}"
    matched_actions = {marker for marker in ACTION_MARKERS if marker.lower() in joined.lower()}
    actionable = bool(matched_actions)
    if content_type in {"reference", "notice"} and not actionable:
        return False, "not_actionable"
    if content_type == "reference":
        title_actionable = any(marker.lower() in title.lower() for marker in ACTION_MARKERS)
        quality = float(row.get("quality_score", 1.0) or 0.0)
        if not title_actionable and (len(matched_actions) < 3 or quality < 0.8):
            return False, "weak_reference_page"
    years = [int(value) for value in re.findall(r"(?<!\d)(20\d{2})(?!\d)", title)]
    if content_type == "notice" and years and max(years) < today.year - 1:
        return False, "stale_notice"
    if row.get("authority_level") == "unverified":
        return False, "unverified_authority"
    return True, "admitted"


def source_candidates() -> list[tuple[dict[str, Any], str, str]]:
    rows: list[tuple[dict[str, Any], str, str]] = []
    v1_manifest = read_jsonl(V1_ROOT / "manifests" / "source_manifest.jsonl")
    for item in v1_manifest:
        path = ROOT / item.get("canonical_file_path", "")
        if not path.is_file():
            continue
        text = plain_markdown(path)
        meta = metadata_from_v1(item, text)
        meta["content_type"] = item.get("content_type") or infer_content_type(item.get("title", ""), text)
        rows.append((meta, text, "frozen_v1"))
    for manifest_name in ("crawl_candidate_manifest.jsonl", "attachment_candidate_manifest.jsonl"):
        for item in read_jsonl(SOURCE_ROOT / manifest_name):
            path = ROOT / item.get("candidate_content_file", "")
            if not path.is_file():
                continue
            candidate = dict(item)
            if (urlsplit(str(candidate.get("source", ""))).hostname or "").lower() == "mp.weixin.qq.com":
                registry_path = ROOT / "configs" / "trusted_campus_agent_v2" / "official_wechat_accounts.json"
                accounts = json.loads(registry_path.read_text(encoding="utf-8"))["accounts"]
                verified = {account["name"] for account in accounts}
                if candidate.get("wechat_account") in verified:
                    candidate["authority_level"] = "official_social"
                    candidate["department"] = next(account["department"] for account in accounts if account["name"] == candidate["wechat_account"])
            rows.append((candidate, plain_markdown(path), manifest_name.removesuffix(".jsonl")))
    return rows


def chunk_source(source_id: str, meta: dict[str, Any], text: str, size: int = 900, overlap: int = 120) -> list[dict[str, Any]]:
    normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks = []
    start = 0
    index = 1
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            boundary = max(normalized.rfind("\n", start + size // 2, end), normalized.rfind("。", start + size // 2, end))
            if boundary > start:
                end = boundary + 1
        body = normalized[start:end].strip()
        if len(body) >= 80:
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
            chunks.append({
                "chunk_id": f"KBV2-{source_id}-{index:04d}", "canonical_source_id": source_id,
                "chunk_index": index, "char_start": start, "char_end": end,
                "chunk_sha256": digest, "title": meta["title"], "url": meta["source"],
                "category": meta.get("category", meta.get("topic", "")), "source_type": "public", "text": body,
            })
            index += 1
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return chunks


def build_dense_index(chunks: list[dict[str, Any]], output: Path) -> str | None:
    try:
        from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1

        dense = build_dense_retriever_v1()
        texts = [f"{row['title']}\n{row['text']}" for row in chunks]
        vectors = []
        for start in range(0, len(texts), 32):
            batch = texts[start : start + 32]
            tokens = dense.tokenizer(batch, padding=True, truncation=True, max_length=int(dense.config["max_length"]), return_tensors="pt")
            import torch
            with torch.inference_mode():
                values = dense.model(**tokens).last_hidden_state[:, 0]
                values = torch.nn.functional.normalize(values, p=2, dim=1)
            vectors.append(values.cpu().numpy().astype(np.float32))
        matrix = np.concatenate(vectors, axis=0) if vectors else np.empty((0, 512), dtype=np.float32)
        (output / "index").mkdir(parents=True, exist_ok=True)
        np.save(output / "index" / "document_embeddings.npy", matrix, allow_pickle=False)
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"[:500]


def build(output: Path, *, dense: bool) -> dict[str, Any]:
    today = date.today()
    decisions = []
    accepted = []
    seen_content: dict[str, str] = {}
    seen_url: dict[str, str] = {}
    for raw, text, origin in source_candidates():
        row = dict(raw)
        row["source"] = str(row.get("source") or row.get("url") or "")
        row["title"] = str(row.get("title") or "未命名资料")
        row["source_id"] = str(row.get("source_id") or row.get("canonical_source_id"))
        row["access_level"] = row.get("access_level", "public")
        row["authority_level"] = row.get("authority_level", "official")
        row["content_type"] = row.get("content_type") or infer_content_type(row["title"], text)
        row["department"] = row.get("department") or infer_department(row["source"], row["title"])
        row["audience"] = row.get("audience") or infer_audience(row["title"], text)
        row["topics"] = row.get("topics") or infer_topics(row.get("category", ""), row["title"], text)
        row["topic"] = row.get("topic") or row["topics"][0]
        row["policy_key"] = row.get("policy_key") or policy_key(row["title"])
        row["normalized_url"] = normalize_url(row["source"])
        row["content_hash"] = row.get("content_hash") or hashlib.sha256(re.sub(r"\s+", "", text).encode("utf-8")).hexdigest()
        ok, reason = assess(row, text, today)
        if ok and row["content_hash"] in seen_content:
            ok, reason = False, "duplicate_content"
        if ok and row["normalized_url"] in seen_url:
            ok, reason = False, "duplicate_url"
        decisions.append({"source_id": row["source_id"], "title": row["title"], "source": row["source"], "origin": origin, "decision": "SERVING" if ok else "EXCLUDED", "reason": reason})
        if ok:
            seen_content[row["content_hash"]] = row["source_id"]
            seen_url[row["normalized_url"]] = row["source_id"]
            accepted.append((row, text, origin))

    grouped: dict[str, list[tuple[dict[str, Any], str, str]]] = defaultdict(list)
    for item in accepted:
        grouped[item[0]["policy_key"]].append(item)
    final = []
    for key, items in grouped.items():
        dated = [item for item in items if date_rank(item[0]) != "0000-00-00"]
        if len(items) > 1 and len(dated) > 1:
            newest = max(dated, key=lambda item: (date_rank(item[0]), item[0]["source_id"]))
            for item in items:
                if item is not newest and date_rank(item[0]) < date_rank(newest[0]):
                    for decision in reversed(decisions):
                        if decision["source_id"] == item[0]["source_id"] and decision["decision"] == "SERVING":
                            decision.update({"decision": "EXCLUDED", "reason": "superseded_by_newer_version", "superseded_by": newest[0]["source_id"]})
                            break
                else:
                    final.append(item)
        else:
            final.extend(items)

    resolved_output = output.resolve()
    resolved_data = (ROOT / "data").resolve()
    if resolved_output.parent != resolved_data or resolved_output.name != "05_trusted_campus_kb_v2_public":
        raise ValueError("output must be the dedicated data/05_trusted_campus_kb_v2_public directory")
    if output.exists():
        shutil.rmtree(output)
    (output / "chunks").mkdir(parents=True)
    (output / "audit").mkdir(parents=True)
    metadata = []
    chunks = []
    for row, text, origin in sorted(final, key=lambda item: item[0]["source_id"]):
        clean = {key: row.get(key) for key in (
            "source_id", "title", "source", "department", "publish_date", "effective_date", "expiry_date",
            "audience", "authority_level", "topic", "topics", "category", "content_type", "policy_key",
            "content_hash", "normalized_url",
        )}
        clean.update({"access_level": "public", "admission_status": "serving", "review_status": "automated_strict_review", "source_version": "TRUSTED_CAMPUS_PUBLIC_KB_V2", "origin": origin})
        metadata.append(clean)
        chunks.extend(chunk_source(clean["source_id"], clean, text))
    write_jsonl(output / "metadata_catalog.jsonl", metadata)
    write_jsonl(output / "chunks" / "chunks.jsonl", chunks)
    write_jsonl(output / "audit" / "admission_decisions.jsonl", decisions)
    coverage = {}
    for scenario in SCENARIOS:
        source_ids = {row["source_id"] for row in metadata if scenario in row.get("topics", [])}
        by_type = Counter(row["content_type"] for row in metadata if row["source_id"] in source_ids)
        coverage[scenario] = {"source_count": len(source_ids), "chunk_count": sum(row["canonical_source_id"] in source_ids for row in chunks), "content_types": dict(sorted(by_type.items())), "status": "COVERED" if len(source_ids) >= 3 else "GAP"}
    dense_error = build_dense_index(chunks, output) if dense else "skipped_by_flag"
    report = {
        "bundle_version": "TRUSTED_CAMPUS_PUBLIC_KB_V2", "built_at": datetime.now().astimezone().isoformat(),
        "public_only": True, "source_count": len(metadata), "chunk_count": len(chunks),
        "decision_counts": dict(Counter(row["reason"] for row in decisions if row["decision"] == "EXCLUDED")),
        "coverage": coverage, "dense_index": "ready" if dense_error is None else "unavailable", "dense_error": dense_error,
        "wechat_policy": "verified account + transactional content only; news excluded",
    }
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "coverage_matrix.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a clean, public-only TsingAsk V2 serving bundle.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-dense", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve(), dense=not args.no_dense), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
