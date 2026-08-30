"""Build an unpublished, opt-in V2 shadow retrieval bundle.

Only high-confidence public official crawl candidates are auto-admitted.  The
frozen V1 bundle is copied logically (never modified), and every decision is
auditable.  Portal-authenticated and undated procedural candidates stay out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
V1_ROOT = ROOT / "data" / "03_knowledge_base" / "v1"
V2_ROOT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2"
OUTPUT = V2_ROOT / "shadow_bundle_v1"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1
from src.trusted_campus_agent_v2.metadata import jsonl


SHADOW_TITLE_ALLOW = re.compile(
    r"(?:规定|办法|细则|制度|条例|指南|流程|手续|申请|须知|常见问题|FAQ|表单|模板|"
    r"学籍|培养工作|学位授予|转专业|转系|奖学金|助学金|资助|住宿|宿舍|就医|挂号|"
    r"疫苗接种|校园交通|校园网|网络运行|信息安全|借阅|开馆时间|入馆|借书证|研讨间|"
    r"签证|Visa|Accommodation|Insurance|交换生|交换项目|就业|档案转递|户口|离校|报到)" , re.I
)
SHADOW_TITLE_REJECT = re.compile(
    r"(?:举行|召开|论坛|讲堂|做客|团队|研究进展|取得.*进展|获奖|开营|交流会|调研|"
    r"签署|活动报道|快讯|故事|致辞|追记|纪念|专访|聚焦20|媒体传真|开通试用|专题书架|党建|荣誉|文章鉴读|发布.*指南)"
)
SHADOW_GENERIC_TITLE = re.compile(r"^(?:服务|用户服务|组织机构|机构设置|科研机构|关于我们|国际合作|学校沿革|清华大学医院|清华大学图书馆|全部表单)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def markdown_body(path: Path) -> str:
    value = path.read_text(encoding="utf-8-sig", errors="replace")
    if value.startswith("---"):
        parts = value.split("---", 2)
        value = parts[2] if len(parts) == 3 else value
    value = re.split(r"\n---\n\n## 来源信息", value, maxsplit=1)[0]
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def chunk_text(text: str, max_chars: int = 800, overlap: int = 120) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + max_chars)
                chunks.append(paragraph[start:end].strip())
                if end == len(paragraph):
                    break
                start = max(start + 1, end - overlap)
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            carry = current[-overlap:].strip() if overlap else ""
            current = f"{carry}\n\n{paragraph}".strip()
            if len(current) > max_chars:
                chunks.append(current[:max_chars].strip())
                current = current[max_chars - overlap :].strip()
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if len(chunk) >= 80]


def decision(row: dict[str, Any], serving_urls: set[str]) -> tuple[bool, list[str]]:
    reasons = []
    if row.get("admission_status") not in {"review_required", "auto_review_candidate"}:
        reasons.append("NOT_IN_REVIEW_QUEUE")
    if row.get("source") in serving_urls:
        reasons.append("DUPLICATE_FROZEN_SOURCE")
    if row.get("access_level") != "public":
        reasons.append("NON_PUBLIC_ACCESS")
    if row.get("authority_level") != "official":
        reasons.append("NOT_OFFICIAL")
    if row.get("source_version") not in {"TRUSTED_CAMPUS_V2_PUBLIC_CRAWL_V1", "TRUSTED_CAMPUS_V2_PORTAL_CRAWL_V1", "TRUSTED_CAMPUS_V2_ATTACHMENT_CRAWL_V1"}:
        reasons.append("NOT_CRAWL_VERIFIED")
    if float(row.get("quality_score") or 0.0) < 0.70:
        reasons.append("QUALITY_BELOW_0_70")
    if row.get("content_type") not in {"policy", "procedure_guide", "faq"}:
        reasons.append("NOT_ACTIONABLE_TYPE")
    title = row.get("title", "")
    if not SHADOW_TITLE_ALLOW.search(title):
        reasons.append("TITLE_NOT_TRANSACTIONAL")
    if SHADOW_TITLE_REJECT.search(title) or SHADOW_GENERIC_TITLE.search(title):
        reasons.append("NEWS_OR_GENERIC_TITLE")
    if "教育基金会" in title:
        reasons.append("OUT_OF_CAMPUS_AFFAIRS_SCOPE")
    if not (row.get("publish_date") or row.get("effective_date") or row.get("expiry_date")):
        reasons.append("NO_TEMPORAL_METADATA")
    content_file = ROOT / row.get("candidate_content_file", "")
    if not content_file.is_file():
        reasons.append("MISSING_CONTENT_FILE")
    return not reasons, reasons


def encode_added(chunks: list[dict[str, Any]], batch_size: int = 16) -> np.ndarray:
    import torch

    dense = build_dense_retriever_v1()
    vectors = []
    for offset in range(0, len(chunks), batch_size):
        texts = [f"{row['title']}\n{row['text']}" for row in chunks[offset : offset + batch_size]]
        tokens = dense.tokenizer(texts, padding=True, truncation=True, max_length=int(dense.config["max_length"]), return_tensors="pt")
        with torch.inference_mode():
            values = dense.model(**tokens).last_hidden_state[:, 0]
            values = torch.nn.functional.normalize(values, p=2, dim=1)
        vectors.append(values.cpu().numpy().astype(np.float32))
    if not vectors:
        return np.empty((0, dense.embeddings.shape[1]), dtype=np.float32)
    return np.concatenate(vectors, axis=0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--build-dense", action="store_true")
    args = parser.parse_args()
    generated = [OUTPUT / "chunks" / "chunks.jsonl", OUTPUT / "metadata_catalog.jsonl", OUTPUT / "audit" / "admission_decisions.jsonl", OUTPUT / "manifest.json"]
    if not args.force and any(path.exists() for path in generated):
        raise SystemExit("refusing to overwrite V2 shadow bundle; pass --force")
    base_chunks = jsonl(V1_ROOT / "chunks" / "chunks.jsonl")
    full_catalog = jsonl(V2_ROOT / "metadata_catalog.jsonl")
    serving = [row for row in full_catalog if row.get("admission_status") == "serving"]
    serving_urls = {row.get("source") for row in serving}
    review_rows = jsonl(V2_ROOT / "crawl_candidate_manifest.jsonl") + jsonl(V2_ROOT / "attachment_candidate_manifest.jsonl")
    added_chunks: list[dict[str, Any]] = []
    shadow_metadata = list(serving)
    decisions = []
    for row in review_rows:
        admitted, reasons = decision(row, serving_urls)
        chunk_count = 0
        if admitted:
            text = markdown_body(ROOT / row["candidate_content_file"])
            parts = chunk_text(text)
            if not parts:
                admitted = False
                reasons = ["NO_VALID_CHUNKS"]
            else:
                shadow = dict(row)
                shadow["admission_status"] = "serving"
                shadow["review_status"] = "auto_verified_shadow_unpublished"
                shadow["shadow_only"] = True
                shadow_metadata.append(shadow)
                for index, part in enumerate(parts, 1):
                    added_chunks.append({
                        "chunk_id": f"{row['source_id']}-C{index:03d}",
                        "canonical_source_id": row["source_id"], "title": row["title"],
                        "url": row["source"], "category": row.get("category", ""), "text": part,
                    })
                chunk_count = len(parts)
                serving_urls.add(row.get("source"))
        decisions.append({"source_id": row.get("source_id"), "source": row.get("source"), "title": row.get("title"), "admitted": admitted, "reasons": reasons, "chunk_count": chunk_count})
    all_chunks = base_chunks + added_chunks
    for path in generated:
        path.parent.mkdir(parents=True, exist_ok=True)
    generated[0].write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_chunks), encoding="utf-8")
    generated[1].write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in shadow_metadata), encoding="utf-8")
    generated[2].write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in decisions), encoding="utf-8")
    dense_status = "not_built"
    embeddings_path = OUTPUT / "index" / "document_embeddings.npy"
    if args.build_dense:
        embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        base_embeddings = np.load(V1_ROOT / "index" / "document_embeddings.npy", allow_pickle=False)
        new_embeddings = encode_added(added_chunks)
        np.save(embeddings_path, np.concatenate([base_embeddings, new_embeddings], axis=0), allow_pickle=False)
        dense_status = "built"
    manifest = {
        "version": "TRUSTED_CAMPUS_V2_SHADOW_BUNDLE_V1", "candidate_only": True,
        "published": False, "frozen_v1_modified": False, "opt_in_only": True,
        "base_chunks": len(base_chunks), "admitted_sources": sum(row["admitted"] for row in decisions),
        "rejected_sources": sum(not row["admitted"] for row in decisions),
        "added_chunks": len(added_chunks), "total_chunks": len(all_chunks), "dense_status": dense_status,
        "artifacts": {"chunks": "chunks/chunks.jsonl", "metadata": "metadata_catalog.jsonl", "embeddings": "index/document_embeddings.npy"},
    }
    generated[3].write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["artifact_sha256"] = {str(path.relative_to(OUTPUT)).replace("\\", "/"): sha256(path) for path in generated[:3]}
    if embeddings_path.is_file():
        manifest["artifact_sha256"][str(embeddings_path.relative_to(OUTPUT)).replace("\\", "/")] = sha256(embeddings_path)
    generated[3].write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
