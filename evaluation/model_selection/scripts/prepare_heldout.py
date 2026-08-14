from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "staging_public_baseline_v1"
MANIFEST = PUBLIC / "public_staging_manifest.jsonl"
OUT_DIR = ROOT / "model_selection" / "heldout"
SEED = 20260813
TARGET_CATEGORIES = [
    "教务与学籍",
    "住宿服务",
    "网络与信息化",
    "医疗健康",
    "图书馆服务",
    "奖助与资助",
    "就业与职业发展",
    "餐饮服务",
    "交通服务",
    "体育与场馆",
]


def main() -> None:
    rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    rng = random.Random(SEED)
    chosen = []
    for category in TARGET_CATEGORIES:
        pool = sorted((r for r in rows if r.get("category") == category), key=lambda r: r["id"])
        if pool:
            chosen.append(rng.choice(pool))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    campus_texts = []
    general_texts = [
        "大学校园中的公共服务通常由多个部门协同提供。清晰的办事指南应说明适用对象、办理条件、材料、流程、时间和联系方式。",
        "图书馆、网络、住宿和医疗等信息具有较强时效性。问答系统在回答时应保留来源，并提示用户核验最新通知。",
        "模型评估应区分语言建模能力、检索质量和最终答案质量，避免使用同一批数据同时训练和评估。",
    ]
    for row in chosen:
        source = PUBLIC / row["content_file"]
        raw = source.read_bytes()
        text = raw.decode("utf-8-sig").strip()
        # The frozen public manifest hashes canonical text: trim and collapse all whitespace.
        actual = hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()
        if actual != row["content_hash"]:
            raise RuntimeError(f"hash mismatch: {row['id']}")
        if not text:
            raise RuntimeError(f"empty held-out source: {row['id']}")
        campus_texts.append(text)
        index.append({
            "source_id": row["id"],
            "category": row["category"],
            "title": row["title"],
            "url": row["url"],
            "content_file": str(source),
            "content_hash": actual,
            "selection_seed": SEED,
            "role": "base_model_benchmark_only__exclude_from_all_training_experiments",
        })

    (OUT_DIR / "heldout_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "campus_heldout.txt").write_text("\n\n<DOC>\n\n".join(campus_texts), encoding="utf-8")
    (OUT_DIR / "general_chinese_heldout.txt").write_text("\n\n".join(general_texts), encoding="utf-8")
    print(json.dumps({"seed": SEED, "heldout_count": len(index), "source_ids": [x["source_id"] for x in index]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
