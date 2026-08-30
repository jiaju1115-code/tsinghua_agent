"""Build metadata and Coverage Matrix for the isolated trusted-campus V2 candidate.

The script reads frozen KB V1 and public staging assets.  It never mutates or
admits records into either source collection.  Staging records remain
``auto_review_candidate`` (legacy ``review_required`` is accepted) and are
excluded from runtime retrieval until the automated trust gate admits them.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2.metadata import (
    REQUIRED_METADATA,
    V1_ROOT,
    authority_level,
    infer_audience,
    infer_department,
    infer_topics,
    jsonl,
    metadata_completeness,
    metadata_from_v1,
    policy_key,
)


DEFAULT_OUTPUT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2"
STAGING_ROOT = ROOT / "data" / "04_public_staging" / "staging_public_baseline_v1"
CRAWL_MANIFEST = DEFAULT_OUTPUT / "crawl_candidate_manifest.jsonl"
ATTACHMENT_MANIFEST = DEFAULT_OUTPUT / "attachment_candidate_manifest.jsonl"
SCENARIOS = ("教务", "学生事务", "校园生活", "科研实践", "国际交流", "就业", "新生", "毕业")
COVERAGE_FLOOR = {"教务": 15, "学生事务": 12, "校园生活": 18, "科研实践": 10, "国际交流": 8, "就业": 8, "新生": 8, "毕业": 8}


def _text_by_source(chunks: list[dict[str, Any]]) -> dict[str, str]:
    values: dict[str, list[str]] = {}
    for row in chunks:
        values.setdefault(row["canonical_source_id"], []).append(row.get("text", ""))
    return {source_id: "\n".join(parts) for source_id, parts in values.items()}


def _candidate_metadata(row: dict[str, Any], content: str) -> dict[str, Any]:
    topics = infer_topics(row.get("category", ""), row.get("title", ""), content)
    return {
        "source_id": row["id"], "title": row.get("title", ""), "source": row.get("url", ""),
        "department": infer_department(row.get("url", ""), row.get("title", "")),
        "publish_date": None, "effective_date": None, "expiry_date": None,
        "audience": infer_audience(row.get("title", ""), content),
        "authority_level": authority_level(row.get("url", "")),
        "topic": topics[0], "topics": topics, "category": row.get("category", ""),
        "content_type": row.get("content_type", ""), "time_status": row.get("time_status", "unknown"),
        "access_level": "public",
        "admission_status": "auto_review_candidate", "review_status": "pending_automated_review",
        "policy_key": policy_key(row.get("title", "")), "source_version": "PUBLIC_STAGING_BASELINE_V1",
        "candidate_content_file": str((STAGING_ROOT / row["content_file"]).relative_to(ROOT)).replace("\\", "/"),
        "candidate_reason": "official staging source; excluded from serving until metadata, freshness and automated trust checks pass",
    }


def build_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    provenance = jsonl(V1_ROOT / "provenance" / "source_provenance.jsonl")
    chunks = jsonl(V1_ROOT / "chunks" / "chunks.jsonl")
    source_text = _text_by_source(chunks)
    serving = [metadata_from_v1(row, source_text.get(row["canonical_source_id"], "")) for row in provenance]
    serving_urls = {row["source"] for row in serving}
    candidates = []
    for row in jsonl(STAGING_ROOT / "public_staging_manifest.jsonl"):
        if row.get("url") in serving_urls:
            continue
        content_path = STAGING_ROOT / row["content_file"]
        content = content_path.read_text(encoding="utf-8-sig") if content_path.is_file() else ""
        candidates.append(_candidate_metadata(row, content))
    seen_urls = {row["source"] for row in serving + candidates}
    seen_hashes = {row.get("content_hash") for row in candidates if row.get("content_hash")}
    for row in jsonl(CRAWL_MANIFEST) + jsonl(ATTACHMENT_MANIFEST):
        if row.get("admission_status") not in {"review_required", "auto_review_candidate"}:
            continue
        if row.get("source") in seen_urls or (row.get("content_hash") and row["content_hash"] in seen_hashes):
            continue
        candidates.append(row)
        seen_urls.add(row.get("source"))
        if row.get("content_hash"):
            seen_hashes.add(row["content_hash"])
    return serving + candidates, serving, candidates


def coverage_matrix(catalog: list[dict[str, Any]], serving: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    chunks = jsonl(V1_ROOT / "chunks" / "chunks.jsonl")
    chunks_per_source = Counter(row["canonical_source_id"] for row in chunks)
    public_serving = [row for row in serving if row.get("access_level") == "public"]
    matrix = []
    for scenario in SCENARIOS:
        live = [row for row in public_serving if scenario in row.get("topics", [])]
        queue = [row for row in candidates if scenario in row.get("topics", [])]
        official = sum(row.get("authority_level") in {"official", "official_internal"} for row in live)
        actionable = sum(row.get("content_type") in {"policy", "procedure_guide", "faq", "mixed"} for row in live)
        dated = sum(bool(row.get("publish_date") or row.get("effective_date") or row.get("expiry_date")) for row in live)
        queue_official = sum(row.get("authority_level") in {"official", "official_internal"} for row in queue)
        queue_dated = sum(bool(row.get("publish_date") or row.get("effective_date") or row.get("expiry_date")) for row in queue)
        queue_actionable = sum(row.get("content_type") in {"policy", "procedure_guide", "faq", "mixed"} for row in queue)
        floor = COVERAGE_FLOOR[scenario]
        volume = min(1.0, len(live) / floor)
        quality = (
            0.40 * volume
            + 0.20 * (official / len(live) if live else 0.0)
            + 0.20 * metadata_completeness(live)
            + 0.15 * (actionable / len(live) if live else 0.0)
            + 0.05 * (dated / len(live) if live else 0.0)
        )
        complete = metadata_completeness(live)
        status = (
            "ROBUST"
            if quality >= 0.78 and len(live) >= floor and complete >= 0.8 and dated / len(live) >= 0.35
            else "PARTIAL" if volume >= 0.5 else "GAP"
        )
        matrix.append({
            "scenario": scenario, "serving_sources": len(live),
            "serving_chunks": sum(chunks_per_source[row["source_id"]] for row in live),
            "review_required_candidates": len(queue), "planning_floor": floor,
            "candidate_official_ratio": round(queue_official / len(queue), 4) if queue else 0.0,
            "candidate_dated_ratio": round(queue_dated / len(queue), 4) if queue else 0.0,
            "candidate_actionable_ratio": round(queue_actionable / len(queue), 4) if queue else 0.0,
            "official_ratio": round(official / len(live), 4) if live else 0.0,
            "metadata_completeness": round(complete, 4),
            "actionable_ratio": round(actionable / len(live), 4) if live else 0.0,
            "dated_ratio": round(dated / len(live), 4) if live else 0.0,
            "coverage_score": round(quality, 4), "status": status,
        })
    return {
        "version": "TRUSTED_CAMPUS_COVERAGE_MATRIX_V2_CANDIDATE",
        "serving_policy": "frozen KB V1 plus explicitly selected unpublished shadow; candidates require automated trust review before admission",
        "required_metadata_fields": list(REQUIRED_METADATA),
        "catalog_sources": len(catalog), "frozen_sources": len(serving),
        "serving_sources": len(public_serving), "restricted_sources": len(serving) - len(public_serving),
        "review_required_candidates": len(candidates), "scenarios": matrix,
        "review_queue_by_source_version": dict(sorted(Counter(row.get("source_version", "unknown") for row in candidates).items())),
        "review_queue_dated": sum(bool(row.get("publish_date") or row.get("effective_date") or row.get("expiry_date")) for row in candidates),
        "review_queue_authenticated": sum(row.get("access_level") != "public" for row in candidates),
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# Trusted Campus V2 Coverage Matrix", "",
        "> Candidate-only artifact. Frozen KB V1 remains unchanged; pending automated-review sources are not served.", "",
        f"- Catalog: {matrix['catalog_sources']} sources",
        f"- Default serving: {matrix['serving_sources']} public frozen/approved sources",
        f"- Restricted inventory (not retrieved by default): {matrix['restricted_sources']} sources",
        f"- Automated review queue: {matrix['review_required_candidates']} official staging candidates", "",
        "| 场景 | 服务来源 | Chunks | 待复核候选 | 候选官方 | 候选有日期 | 候选可行动 | 规划下限 | 服务官方 | Metadata 完整度 | 服务可行动 | 服务有日期 | 分数 | 状态 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in matrix["scenarios"]:
        lines.append(
            f"| {row['scenario']} | {row['serving_sources']} | {row['serving_chunks']} | {row['review_required_candidates']} | "
            f"{row['candidate_official_ratio']:.1%} | {row['candidate_dated_ratio']:.1%} | {row['candidate_actionable_ratio']:.1%} | "
            f"{row['planning_floor']} | {row['official_ratio']:.1%} | {row['metadata_completeness']:.1%} | "
            f"{row['actionable_ratio']:.1%} | {row['dated_ratio']:.1%} | {row['coverage_score']:.3f} | {row['status']} |"
        )
    lines += ["", "## Admission rule", "", "A candidate can enter the unpublished shadow only after automated authority, content quality, audience, temporal validity and duplicate/conflict checks pass. The public production bundle is never modified or promoted by this builder.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true", help="replace only generated V2 candidate artifacts")
    args = parser.parse_args()
    outputs = [args.output_dir / "metadata_catalog.jsonl", args.output_dir / "coverage_matrix.json", args.output_dir / "coverage_matrix.md"]
    if not args.force and any(path.exists() for path in outputs):
        raise SystemExit("refusing to overwrite generated candidate artifacts; pass --force explicitly")
    catalog, serving, candidates = build_catalog()
    matrix = coverage_matrix(catalog, serving, candidates)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs[0].write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in catalog), encoding="utf-8")
    outputs[1].write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outputs[2].write_text(render_markdown(matrix), encoding="utf-8")
    print(json.dumps({"status": "BUILT_CANDIDATE_ONLY", "output_dir": str(args.output_dir), **{key: matrix[key] for key in ("catalog_sources", "serving_sources", "review_required_candidates")}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
