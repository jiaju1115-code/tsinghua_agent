from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[4]
STAGING = ROOT / "data" / "04_public_staging"
RESTRICTED = ROOT / "data" / "05_restricted_expansion" / "v1"
PUBLIC_V2 = ROOT / "data" / "02_public_expansion" / "v2"

CATEGORIES = [
    "清华基本信息", "教务与学籍", "学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康",
    "网络与信息化", "图书馆服务", "体育与场馆", "奖助与资助", "国际事务与签证", "就业与职业发展",
    "校园访问", "校园综合服务", "科研参与与资源导航", "教学与培养", "校园机构与部门", "校园文化与历史",
]
P0 = {"学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康", "奖助与资助", "就业与职业发展"}
P1 = {"体育与场馆", "校园访问", "校园综合服务", "网络与信息化", "教务与学籍"}
P2 = {"国际事务与签证", "教学与培养", "校园机构与部门", "科研参与与资源导航"}


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")


def norm_url(url: str) -> str:
    try:
        p = urlsplit((url or "").strip())
        host = (p.hostname or "").lower()
        port = f":{p.port}" if p.port and not ((p.scheme == "https" and p.port == 443) or (p.scheme == "http" and p.port == 80)) else ""
        path = re.sub(r"/{2,}", "/", p.path or "/")
        if path != "/":
            path = path.rstrip("/")
        query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")))
        return urlunsplit(((p.scheme or "https").lower(), host + port, path, query, ""))
    except Exception:
        return (url or "").strip()


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def sha(text: str) -> str:
    return hashlib.sha256(norm_text(text).encode("utf-8")).hexdigest()


def title_key(title: str) -> str:
    return re.sub(r"[\W_]+", "", (title or "").lower(), flags=re.UNICODE)


def better(a, b):
    score_a = (a["quality_rank"], len(a["content"]), a["provenance_rank"])
    score_b = (b["quality_rank"], len(b["content"]), b["provenance_rank"])
    return a if score_a >= score_b else b


def main():
    for d in [
        STAGING / "content", RESTRICTED / "planning", RESTRICTED / "crawl", RESTRICTED / "extracted",
        RESTRICTED / "safety_gate", RESTRICTED / "quality_gate", RESTRICTED / "audit",
        RESTRICTED / "candidates", RESTRICTED / "reports", RESTRICTED / "_workbook_previews",
    ]:
        d.mkdir(parents=True, exist_ok=True)

    raw = []
    reaudit_path = PUBLIC_V2 / "audit" / "public_v3_2_reaudit_217.jsonl"
    v2_path = PUBLIC_V2 / "audit" / "public_expansion_v2_v3_2_results.jsonl"

    for r in read_jsonl(reaudit_path):
        if r.get("action") != "approve":
            continue
        content = (r.get("cleaned_content") or "").strip()
        raw.append({
            "original_id": r.get("id", ""), "title": r.get("title", ""), "url": r.get("url", ""),
            "normalized_url": norm_url(r.get("url", "")), "domain": r.get("domain", ""),
            "source_batch": "public_v3_2_reaudit_217", "category": r.get("category", ""),
            "content_type": r.get("content_type", ""), "topic_relevance": r.get("topic_relevance", ""),
            "time_status": r.get("time_status", ""), "content": content, "content_hash": sha(content),
            "v3_2_action": "approve", "qa_status": "pending_human_check", "quality_class": "detail_content",
            "quality_rank": 3, "provenance_rank": 2, "source_reference": str(reaudit_path),
        })

    for r in read_jsonl(v2_path):
        if (r.get("v3_2_action") or r.get("action")) != "approve":
            continue
        source = PUBLIC_V2 / (r.get("source_file") or "")
        content = source.read_text(encoding="utf-8") if source.exists() else ""
        quality = r.get("quality_class") or "detail_content"
        raw.append({
            "original_id": r.get("id", ""), "title": r.get("title", ""), "url": r.get("url", ""),
            "normalized_url": r.get("normalized_url") or norm_url(r.get("url", "")), "domain": r.get("domain", ""),
            "source_batch": "public_expansion_v2", "category": r.get("category", ""),
            "content_type": r.get("content_type", ""), "topic_relevance": r.get("topic_relevance", ""),
            "time_status": r.get("time_status", ""), "content": content, "content_hash": sha(content),
            "v3_2_action": "approve", "qa_status": "pending_human_check", "quality_class": quality,
            "quality_rank": {"detail_content": 4, "thin_content": 2}.get(quality, 3),
            "provenance_rank": 3, "source_reference": str(source),
        })

    kept = []
    dedup_log = []
    for row in raw:
        match_i = None
        reason = ""
        for i, old in enumerate(kept):
            if row["normalized_url"] and row["normalized_url"] == old["normalized_url"]:
                match_i, reason = i, "normalized_url"
                break
            if row["content_hash"] and row["content_hash"] == old["content_hash"]:
                match_i, reason = i, "content_hash"
                break
            ta, tb = title_key(row["title"]), title_key(old["title"])
            if len(ta) >= 8 and len(tb) >= 8 and SequenceMatcher(None, ta, tb).ratio() >= 0.94:
                match_i, reason = i, "title_similarity>=0.94"
                break
        if match_i is None:
            kept.append(row)
        else:
            chosen = better(kept[match_i], row)
            dropped = row if chosen is kept[match_i] else kept[match_i]
            kept[match_i] = chosen
            dedup_log.append({
                "dedup_reason": reason, "kept_original_id": chosen["original_id"],
                "dropped_original_id": dropped["original_id"], "title": chosen["title"],
            })

    manifest = []
    for i, row in enumerate(sorted(kept, key=lambda x: (CATEGORIES.index(x["category"]) if x["category"] in CATEGORIES else 99, x["title"])), 1):
        sid = f"STGPUB-{i:04d}"
        target = STAGING / "content" / f"{sid}.md"
        target.write_text(row["content"].strip() + "\n", encoding="utf-8", newline="\n")
        actual_hash = sha(target.read_text(encoding="utf-8"))
        manifest.append({
            "id": sid, "title": row["title"], "url": row["url"], "domain": row["domain"],
            "source_batch": row["source_batch"], "category": row["category"], "content_type": row["content_type"],
            "topic_relevance": row["topic_relevance"], "time_status": row["time_status"],
            "content_file": str(target.relative_to(STAGING)).replace("\\", "/"), "content_hash": actual_hash,
            "v3_2_action": "approve", "qa_status": row["qa_status"], "normalized_url": row["normalized_url"],
            "original_id": row["original_id"], "quality_class": row["quality_class"],
        })
    write_jsonl(STAGING / "public_staging_manifest.jsonl", manifest)

    counts = Counter(r["category"] for r in manifest)
    gap_rows = []
    for c in CATEGORIES:
        priority = "P0" if c in P0 else "P1" if c in P1 else "P2" if c in P2 else "not_targeted"
        floor = 10 if priority == "P0" else 6 if priority == "P1" else 3 if priority == "P2" else 0
        count = counts[c]
        gap = max(0, floor - count)
        gap_rows.append({
            "category": c, "public_approve_count": count, "restricted_priority": priority,
            "planning_floor": floor, "minimum_gap": gap,
            "gap_status": "明显不足" if priority in {"P0", "P1"} and count < floor else "可定向补充" if priority == "P2" and count < floor else "已有基础",
        })
    (STAGING / "public_staging_gap_analysis.md").write_text(
        "# Public Staging Gap Analysis\n\n"
        f"- Staging approve：{len(manifest)}\n"
        f"- 合并前 approve：{len(raw)}\n"
        f"- 去重移除：{len(dedup_log)}\n"
        "- 状态：candidate baseline，未合并 production。\n\n"
        "| Category | Public approve | Restricted priority | Planning floor | Minimum gap | Status |\n"
        "|---|---:|---|---:|---:|---|\n" +
        "\n".join(f"| {r['category']} | {r['public_approve_count']} | {r['restricted_priority']} | {r['planning_floor']} | {r['minimum_gap']} | {r['gap_status']} |" for r in gap_rows) +
        "\n", encoding="utf-8", newline="\n")

    qg = read_jsonl(PUBLIC_V2 / "quality_gate" / "canonical_quality_gate_results.jsonl")
    seed_ids = {"PUBV2C-0109", "PUBV2C-0110", "PUBV2C-0111", "PUBV2C-0112", "PUBV2C-0120", "PUBV2C-0122", "PUBV2C-0123", "PUBV2C-0124", "PUBV2C-0131", "PUBV2C-0134", "PUBV2C-0135", "PUBV2C-0136"}
    medium_ids = {"PUBV2C-0121"}
    seed_rows = []
    for r in qg:
        if r.get("quality_class") != "login_required":
            continue
        rid = r.get("id")
        if rid in seed_ids:
            rec, prio, value = "yes", "P0", "高：稳定服务、流程、政策或资源入口"
        elif rid in medium_ids:
            rec, prio, value = "conditional", "P0", "中：偏用人单位，但可能包含稳定校园招聘流程"
        else:
            rec, prio, value = "no", "P0", "低：培训/新闻/活动报道或高度时效内容，不为数量抓取"
        seed_rows.append({
            "seed_id": rid, "title": r.get("title", ""), "url": r.get("url", ""),
            "normalized_url": r.get("normalized_url") or norm_url(r.get("url", "")),
            "original_category": r.get("discovery_category") or "就业与职业发展",
            "discovery_source": r.get("discovery_source", ""),
            "previous_failure_reason": r.get("diagnostic_reason") or "login_required",
            "domain": r.get("domain", ""), "priority": prio,
            "recommended_for_authenticated_fetch": rec, "value_judgement": value,
            "parent_url": r.get("parent_list_url", ""),
        })

    plan_rows = [r for r in gap_rows if r["restricted_priority"] in {"P0", "P1", "P2"}]
    (RESTRICTED / "planning" / "_public_manifest_rows.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (RESTRICTED / "planning" / "_gap_rows.json").write_text(json.dumps(gap_rows, ensure_ascii=False), encoding="utf-8")
    (RESTRICTED / "planning" / "_seed_rows.json").write_text(json.dumps(seed_rows, ensure_ascii=False), encoding="utf-8")
    (RESTRICTED / "planning" / "_plan_rows.json").write_text(json.dumps(plan_rows, ensure_ascii=False), encoding="utf-8")
    (RESTRICTED / "planning" / "_dedup_log.json").write_text(json.dumps(dedup_log, ensure_ascii=False), encoding="utf-8")
    (RESTRICTED / "planning" / "restricted_expansion_v1_plan.md").write_text(
        "# Restricted / Authenticated Expansion V1 Plan\n\n"
        f"- Public staging approve：{len(manifest)}\n"
        f"- 旧 login_required seeds：{len(seed_rows)}\n"
        f"- 推荐认证后抓取：{sum(r['recommended_for_authenticated_fetch']=='yes' for r in seed_rows)}\n"
        f"- 条件抓取：{sum(r['recommended_for_authenticated_fetch']=='conditional' for r in seed_rows)}\n"
        "- 认证原则：仅复用现有合法 session；若失效，状态为 `NEED_MANUAL_LOGIN`。\n"
        "- 安全原则：private/sensitive gate 在 Quality Gate 之前；仅 safe_general_content 继续。\n"
        "- 抓取范围：P0/P1 优先，单系统约 50 个 detail 上限，list page 仅一层定向 follow。\n"
        "- 数据状态：仅 restricted candidate，不进入 production。\n",
        encoding="utf-8", newline="\n")
    print(json.dumps({
        "raw_approve": len(raw), "staging_approve": len(manifest), "dedup_removed": len(dedup_log),
        "seeds": len(seed_rows), "recommended": sum(r["recommended_for_authenticated_fetch"] == "yes" for r in seed_rows),
        "category_counts": dict(sorted(counts.items())),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
