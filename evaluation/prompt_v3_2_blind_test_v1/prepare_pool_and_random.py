from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(r"D:\python_projects\tsinghua_ai\data_second")
BASE = ROOT / "prompt_v3_2_blind_test_v1"
RANDOM_SEED = 20260813


def normalize_url(url: str) -> str:
    parts = urlsplit(str(url or "").strip())
    host = (parts.hostname or "").lower()
    port = parts.port
    netloc = host + (f":{port}" if port and not ((parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)) else "")
    path = re.sub(r"/+", "/", parts.path or "/").rstrip("/") or "/"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_")))
    return urlunsplit((parts.scheme.lower(), netloc, path, query, ""))


def load_rows(path: Path):
    if path.suffix == ".jsonl":
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.values()) if isinstance(data, dict) else data


audit = load_rows(ROOT / "public_rebuild_v1" / "audit" / "public_rebuild_v1_all_audited.json")
history_sources = [
    (ROOT / "public_rebuild_v1" / "human_check" / "public_rebuild_v1_human_check.json", "人工标注与Prompt V2/人工比较"),
    (ROOT / "prompt_v3_test" / "audit" / "v3_inputs.json", "Prompt V3设计与回归"),
    (ROOT / "prompt_v3_1_test" / "audit" / "v3_1_results.jsonl", "Prompt V3.1回归"),
    (ROOT / "prompt_v3_2_test" / "audit" / "v3_2_results.jsonl", "Prompt V3.2回归"),
]

history = {}
for path, reason in history_sources:
    for row in load_rows(path):
        ident = str(row.get("id") or row.get("original_id") or "")
        url = str(row.get("url") or "")
        key = ident or normalize_url(url)
        entry = history.setdefault(key, {"id": ident, "title": row.get("title", ""), "url": url, "normalized_url": normalize_url(url), "reasons": []})
        if reason not in entry["reasons"]: entry["reasons"].append(reason)

history_ids = {x["id"] for x in history.values() if x["id"]}
history_urls = {x["url"] for x in history.values() if x["url"]}
history_norms = {x["normalized_url"] for x in history.values() if x["normalized_url"]}
exclusion = []
pool = []
for row in audit:
    normalized = normalize_url(row.get("url", ""))
    matched = str(row.get("id")) in history_ids or str(row.get("url", "")) in history_urls or normalized in history_norms
    if matched:
        reasons = []
        for item in history.values():
            if item["id"] == row.get("id") or item["url"] == row.get("url") or item["normalized_url"] == normalized:
                reasons.extend(item["reasons"])
        exclusion.append({"id": row.get("id", ""), "title": row.get("title", ""), "url": row.get("url", ""), "normalized_url": normalized, "exclusion_reason": "；".join(dict.fromkeys(reasons))})
    else:
        pool.append({
            "id": row.get("id", ""), "title": row.get("title", ""), "url": row.get("url", ""), "normalized_url": normalized,
            "domain": row.get("source_domain", ""), "category": row.get("category", ""), "content_type": row.get("content_type", ""),
            "V2_action": row.get("action", ""), "content_quality_class": row.get("content_quality_class", ""),
            "extraction_method": row.get("extraction_method", ""), "source_file": row.get("source_file", ""),
        })

if len(audit) != 217 or len(exclusion) != 30 or len(pool) != 187:
    raise RuntimeError(f"unexpected pool sizes audit={len(audit)} exclusion={len(exclusion)} pool={len(pool)}")

# Reproducible stratified random sample. The selection algorithm does not read
# title, V2_action, or any later Prompt result. Domain quotas reflect the pool
# structure while ensuring all three available domains are represented.
quotas = {"lib.tsinghua.edu.cn": 21, "www.itc.tsinghua.edu.cn": 3, "peace.tsinghua.edu.cn": 1}
rng = random.Random(RANDOM_SEED)
random_rows = []
for domain, quota in quotas.items():
    candidates = [x for x in pool if x["domain"] == domain]
    rng.shuffle(candidates)
    chosen = []
    category_counts = Counter()
    type_counts = Counter()
    while len(chosen) < quota:
        best_score = None; best = None
        for index, row in enumerate(candidates):
            if row in chosen: continue
            score = (category_counts[row["category"]], type_counts[row["content_type"]], index)
            if best_score is None or score < best_score:
                best_score, best = score, row
        chosen.append(best); category_counts[best["category"]] += 1; type_counts[best["content_type"]] += 1
    random_rows.extend(chosen)

if len(random_rows) != 25 or len({x["id"] for x in random_rows}) != 25:
    raise RuntimeError("random sample failure")

for directory in ("manifest", "samples", "human_label", "reports", "audit"):
    (BASE / directory).mkdir(parents=True, exist_ok=True)
(BASE / "manifest" / "blind_test_exclusion_list.json").write_text(json.dumps(exclusion, ensure_ascii=False, indent=2), encoding="utf-8")
(BASE / "manifest" / "blind_candidate_pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8")
(BASE / "audit" / "random_sample.json").write_text(json.dumps(random_rows, ensure_ascii=False, indent=2), encoding="utf-8")
summary = {
    "qualified": len(audit), "excluded": len(exclusion), "candidate_pool": len(pool), "random_seed": RANDOM_SEED,
    "random_count": len(random_rows), "random_domain_quotas": quotas,
    "random_domains": dict(Counter(x["domain"] for x in random_rows)),
    "random_categories": dict(Counter(x["category"] for x in random_rows)),
    "random_content_types": dict(Counter(x["content_type"] for x in random_rows)),
    "exclusion_ids_sha256": hashlib.sha256("\n".join(sorted(x["id"] for x in exclusion)).encode()).hexdigest(),
}
(BASE / "audit" / "pool_random_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({**summary, "random_ids": [x["id"] for x in random_rows]}, ensure_ascii=False, indent=2))
