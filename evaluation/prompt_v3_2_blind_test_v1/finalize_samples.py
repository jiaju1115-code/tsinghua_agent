from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(r"D:\python_projects\tsinghua_ai\data_second")
BASE = ROOT / "prompt_v3_2_blind_test_v1"
PUBLIC = ROOT / "public_rebuild_v1"

TARGETED = {
    "PUBEXP000193": ["科研成果/行业科研新闻"],
    "PUBEXP000200": ["科研成果/行业科研新闻"],
    "PUBEXP000279": ["人物/荣誉"],
    "PUBEXP000225": ["人物/荣誉"],
    "PUBEXP000284": ["人物/荣誉"],
    "PUBEXP000259": ["校领导活动"],
    "PUBEXP000159": ["校领导活动"],
    "PUBEXP000229": ["合作签约"],
    "PUBEXP000049": ["合作签约"],
    "PUBEXP000003": ["长期校园服务"],
    "PUBEXP000024": ["长期校园服务"],
    "PUBEXP000042": ["长期校园服务"],
    "PUBEXP000099": ["长期校园服务"],
    "PUBEXP000164": ["科研资源"],
    "PUBEXP000204": ["科研资源"],
    "PUBEXP000172": ["科研资源"],
    "PUBEXP000089": ["校园核心事务"],
    "PUBEXP000029": ["校园核心事务"],
    "PUBEXP000223": ["校园核心事务"],
    "PUBEXP000081": ["活动/新闻边界"],
    "PUBEXP000230": ["活动/新闻边界"],
    "PUBEXP000261": ["活动/新闻边界"],
    "PUBEXP000034": ["medium候选"],
    "PUBEXP000056": ["medium候选"],
    "PUBEXP000149": ["medium候选"],
}

# Randomly selected pages can also contribute to coverage reporting, but were
# never chosen for that purpose.
RANDOM_COVERAGE = {
    "PUBEXP000198": ["科研成果/行业科研新闻"],
    "PUBEXP000174": ["科研资源"],
    "PUBEXP000166": ["科研资源", "活动/新闻边界"],
    "PUBEXP000215": ["校园核心事务"],
    "PUBEXP000063": ["medium候选"],
    "PUBEXP000288": ["活动/新闻边界", "人物/荣誉"],
    "PUBEXP000088": ["校园核心事务", "长期校园服务", "medium候选"],
}


def clean_title(title: str) -> str:
    text = re.sub(r"-清华大学图书馆$", "", str(title or ""))
    text = re.sub(r"\d{4}[年/-]\d{1,2}[月/-]?\d{0,2}日?", "", text)
    text = re.sub(r"第\d+期|第\d+讲", "系列", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text).lower()
    return text


def neutral_category_hint(domain: str) -> str:
    return {
        "lib.tsinghua.edu.cn": "图书馆站点",
        "www.itc.tsinghua.edu.cn": "信息化技术中心站点",
        "peace.tsinghua.edu.cn": "校园安全与秩序站点",
    }.get(domain, "清华公开站点")


def neutral_content_type_hint(title: str) -> str:
    text = str(title or "")
    if re.search(r"通知|公告|报名|试用|征稿", text): return "通知/公告形式"
    if re.search(r"举办|举行|活动|论坛|讲座|出席|调研|合作|签署|获奖|喜报|成果|发表", text): return "活动/新闻形式"
    if re.search(r"简介|概况|职能|机构|历史|沿革|致辞", text): return "机构/概况形式"
    if re.search(r"服务|办法|须知|导引|FAQ|联系|时间|岗位|申请", text): return "服务/规则形式"
    if re.search(r"资源|数据库|平台|政策|专题|专架", text): return "资源/政策形式"
    return "其他公开页面形式"


pool = json.loads((BASE / "manifest" / "blind_candidate_pool.json").read_text(encoding="utf-8"))
pool_by_id = {x["id"]: x for x in pool}
random_rows = json.loads((BASE / "audit" / "random_sample.json").read_text(encoding="utf-8"))
random_ids = {x["id"] for x in random_rows}
if random_ids & set(TARGETED):
    raise RuntimeError(f"random/targeted overlap: {sorted(random_ids & set(TARGETED))}")
missing = set(TARGETED) - set(pool_by_id)
if missing: raise RuntimeError(f"targeted ids not in candidate pool: {sorted(missing)}")
targeted_rows = [pool_by_id[x] for x in TARGETED]

selected = []
for source_group, rows in (("random", random_rows), ("targeted", targeted_rows)):
    for row in rows:
        source_path = PUBLIC / row["source_file"]
        content = source_path.read_text(encoding="utf-8")
        coverage = TARGETED.get(row["id"], RANDOM_COVERAGE.get(row["id"], []))
        selected.append({
            **row,
            "source_group": source_group,
            "coverage_tags": "；".join(coverage),
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "content_chars": len(content),
            "cleaned_content": content,
            "title_key": clean_title(row["title"]),
        })

if len(selected) != 50 or len({x["id"] for x in selected}) != 50:
    raise RuntimeError("final sample count/ID uniqueness failure")
if len({x["normalized_url"] for x in selected}) != 50:
    raise RuntimeError("normalized URL duplicate in final samples")
if len({x["content_sha256"] for x in selected}) != 50:
    duplicates = defaultdict(list)
    for x in selected: duplicates[x["content_sha256"]].append(x["id"])
    raise RuntimeError(f"duplicate content: {[v for v in duplicates.values() if len(v)>1]}")

# Detect title pairs for audit. Hard-fail only on near-identical titles; series
# membership is additionally controlled through the explicit coverage design.
similar_pairs = []
for i, left in enumerate(selected):
    for right in selected[i + 1:]:
        ratio = SequenceMatcher(None, left["title_key"], right["title_key"]).ratio()
        if ratio >= 0.82:
            similar_pairs.append({"left": left["id"], "right": right["id"], "ratio": round(ratio, 4), "left_title": left["title"], "right_title": right["title"]})
if any(x["ratio"] >= 0.94 for x in similar_pairs):
    raise RuntimeError(f"near-identical titles detected: {similar_pairs}")

content_dir = BASE / "samples" / "content"
content_dir.mkdir(parents=True, exist_ok=True)
manifest = []
human = []
for index, row in enumerate(selected, 1):
    blind_id = f"BLINDV1-{index:03d}"
    content_name = f"{blind_id}_{row['id']}.md"
    shutil.copy2(PUBLIC / row["source_file"], content_dir / content_name)
    relative_content_file = f"samples/content/{content_name}"
    manifest.append({
        "blind_id": blind_id, "original_id": row["id"], "title": row["title"], "url": row["url"],
        "normalized_url": row["normalized_url"], "domain": row["domain"], "category_hint": row["category"],
        "content_type_hint": row["content_type"], "source_group": row["source_group"], "coverage_tags": row["coverage_tags"],
        "old_V2_action": row["V2_action"], "content_quality_class": row["content_quality_class"],
        "extraction_method": row["extraction_method"], "content_file": relative_content_file,
        "content_chars": row["content_chars"], "content_sha256": row["content_sha256"],
    })
    human.append({
        "blind_id": blind_id, "original_id": row["id"], "title": row["title"], "url": row["url"], "domain": row["domain"],
        "category_hint": neutral_category_hint(row["domain"]), "content_type_hint": neutral_content_type_hint(row["title"]), "content_file": relative_content_file,
        "cleaned_content": row["cleaned_content"], "source_group": row["source_group"],
        "human_action": "", "human_category": "", "human_reject_type": "", "human_topic_relevance": "",
        "human_time_status": "", "human_valid_until": "", "human_note": "",
    })

coverage_counts = Counter()
for row in selected:
    for tag in filter(None, row["coverage_tags"].split("；")): coverage_counts[tag] += 1
summary = {
    "total": len(selected), "random": sum(x["source_group"] == "random" for x in selected),
    "targeted": sum(x["source_group"] == "targeted" for x in selected),
    "domains": dict(Counter(x["domain"] for x in selected)),
    "categories": dict(Counter(x["category"] for x in selected)),
    "content_types": dict(Counter(x["content_type"] for x in selected)),
    "coverage": dict(coverage_counts), "similar_title_pairs": similar_pairs,
    "normalized_url_unique": len({x["normalized_url"] for x in selected}),
    "content_hash_unique": len({x["content_sha256"] for x in selected}),
    "max_content_chars": max(x["content_chars"] for x in selected),
}
(BASE / "samples" / "blind_test_v1_sample_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
(BASE / "human_label" / "blind_test_v1_human_label.json").write_text(json.dumps(human, ensure_ascii=False, indent=2), encoding="utf-8")
(BASE / "audit" / "final_sample_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
(BASE / "audit" / "title_similarity_audit.json").write_text(json.dumps(similar_pairs, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({**summary, "targeted_ids": list(TARGETED)}, ensure_ascii=False, indent=2))
