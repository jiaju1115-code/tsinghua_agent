from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KB_ROOT = ROOT / "data" / "05_trusted_campus_kb_v2_public"
OUTPUT = ROOT / "training" / "qwen3_grounded_lora_v1" / "data"
SYSTEM = (
    "你是清问·TsingAsk 的校园事务回答助手。只能依据用户提供的 evidence 写回答；"
    "语气自然、直接、完整，每个自然段用 [F编号] 标明依据。不得新增条件、日期、金额、部门或网址。"
)


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


AFFAIRS_SIGNALS = ("条件", "申请", "办理", "提交", "应当", "必须", "需要", "可以", "流程", "材料", "规定", "审核", "系统", "截止", "资格", "服务")


def sentences(text: str) -> list[str]:
    text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"^#+[^\n]*\n+", "", text.strip())
    values = []
    for value in re.split(r"(?<=[。！？；])|\n+", re.sub(r"\s+", " ", text)):
        value = value.strip(" -•")
        digits = len(re.findall(r"\d", value))
        if (
            24 <= len(value) <= 180
            and digits <= 10
            and any(signal in value for signal in AFFAIRS_SIGNALS)
            and not any(marker in value for marker in ("□", ">>", "版权所有", "地址：", "电话："))
            and value.count("：") <= 3
        ):
            values.append(value)
    return values


def source_split(source_id: str) -> str:
    return "validation" if int(hashlib.sha256(source_id.encode()).hexdigest()[:8], 16) % 10 == 0 else "train"


def build_row(chunk: dict[str, Any], index: int) -> dict[str, Any] | None:
    facts = sentences(chunk.get("text", ""))[:2]
    if not facts:
        return None
    source_id = chunk["canonical_source_id"]
    fact_map = {f"F{number + 1}": fact for number, fact in enumerate(facts)}
    partial = index % 5 == 0
    title = re.sub(r"\s+", " ", chunk.get("title", "这项校园事务")).strip()
    if partial:
        query = f"我想了解{title}，具体怎么做，截止时间又是什么时候？"
        answer = f"从现有官方资料看，可以先确认这一点：{facts[0]} [F1]"
        if len(facts) > 1:
            answer += f"\n\n此外，办理时还要留意：{facts[1]} [F2]"
        answer += "\n\n不过，目前给出的证据没有包含你问到的具体截止时间，建议按对应官方来源确认当前批次；在确认前我不会替你猜一个日期。 [F1]"
        status = "PARTIAL"
    else:
        query = f"能不能用容易理解的话介绍一下{title}？"
        if len(facts) == 1:
            prefixes = ("可以。官方资料明确说明：", "这件事可以先这样理解：", "关于这个问题，目前能确认的是：")
            answer = f"{prefixes[index % len(prefixes)]}{facts[0]} [F1]"
        else:
            answer = f"先说结论：{facts[0]} [F1]\n\n实际办理时还需要注意，{facts[1]} [F2]"
        status = "SUPPORTED"
    payload = {"query": query, "evidence_status": status, "facts": fact_map}
    return {
        "id": f"Q3G-{hashlib.sha256((source_id + chunk['chunk_id'] + status).encode()).hexdigest()[:16]}",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            {"role": "assistant", "content": answer},
        ],
        "metadata": {
            "task_family": "GROUNDED_NATURAL_CAMPUS_ANSWER",
            "evidence_status": status,
            "source_id": source_id,
            "chunk_id": chunk["chunk_id"],
            "source_url": chunk.get("url", ""),
            "provenance": "TSINGASK_KB_V2_PUBLIC_SERVING",
            "training_target": "style_and_grounding_not_fact_memorization",
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    chunks = jsonl(KB_ROOT / "chunks" / "chunks.jsonl")
    catalog = {row["source_id"]: row for row in jsonl(KB_ROOT / "metadata_catalog.jsonl")}
    rows = []
    source_seen: Counter[str] = Counter()
    for index, chunk in enumerate(chunks):
        source_id = chunk["canonical_source_id"]
        meta = catalog.get(source_id, {})
        if meta.get("admission_status", "serving") != "serving" or meta.get("access_level", "public") != "public":
            continue
        if meta.get("authority_level") not in {"official", "official_internal"}:
            continue
        title = re.sub(r"\s+", " ", chunk.get("title", "")).strip()
        if not (4 <= len(title) <= 60) or any(marker in title for marker in (">>", "名单", "招聘", "新闻")):
            continue
        if meta.get("content_type") not in {"procedure_guide", "policy", "faq", "service_guide"}:
            continue
        if source_seen[source_id] >= 2:
            continue
        row = build_row(chunk, index)
        if row:
            source_seen[source_id] += 1
            rows.append(row)
    train = [row for row in rows if source_split(row["metadata"]["source_id"]) == "train"]
    validation = [row for row in rows if source_split(row["metadata"]["source_id"]) == "validation"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    hashes = {
        "train.jsonl": write_jsonl(OUTPUT / "train.jsonl", train),
        "validation.jsonl": write_jsonl(OUTPUT / "validation.jsonl", validation),
    }
    manifest = {
        "dataset_version": "QWEN3_GROUNDED_NATURAL_SFT_V1",
        "builder": "scripts/build_qwen3_grounded_sft_v1.py",
        "source_bundle": str(KB_ROOT.relative_to(ROOT)),
        "row_count": len(rows),
        "train_count": len(train),
        "validation_count": len(validation),
        "source_split_overlap": sorted({r['metadata']['source_id'] for r in train} & {r['metadata']['source_id'] for r in validation}),
        "status_distribution": dict(Counter(r["metadata"]["evidence_status"] for r in rows)),
        "sha256": hashes,
        "note": "This dataset teaches evidence-conditioned style. It is not an authorization to memorize or replace the live knowledge base.",
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
