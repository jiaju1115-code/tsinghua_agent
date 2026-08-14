from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(r"D:\python_projects\tsinghua_ai\data_second")
AUDIT = json.loads((ROOT / "public_rebuild_v1" / "audit" / "public_rebuild_v1_all_audited.json").read_text(encoding="utf-8"))
EXCLUDED = {x["id"] for x in json.loads((ROOT / "prompt_v3_test" / "audit" / "v3_inputs.json").read_text(encoding="utf-8"))}
POOL = [x for x in AUDIT if x["id"] not in EXCLUDED]

groups = {
    "research_or_achievement": [x for x in POOL if x.get("content_type") in {"research_news", "achievement_report"}],
    "news": [x for x in POOL if x.get("content_type") == "news_event"],
    "core_affairs": [x for x in POOL if x.get("category") in {"学生事务", "校园生活"}],
    "non_library": [x for x in POOL if x.get("source_domain") != "lib.tsinghua.edu.cn"],
}
out = {}
for group, rows in groups.items():
    out[group] = []
    for x in rows:
        content_path = ROOT / "public_rebuild_v1" / x["source_file"]
        text = content_path.read_text(encoding="utf-8") if content_path.exists() else ""
        out[group].append({
            "id": x["id"], "title": x["title"], "domain": x["source_domain"], "category": x["category"],
            "content_type": x["content_type"], "content_chars": len(text), "content_head": text[:1000],
        })
(ROOT / "prompt_v3_2_blind_test_v1" / "reports" / "candidate_inspection.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: len(v) for k, v in out.items()}, ensure_ascii=False))
