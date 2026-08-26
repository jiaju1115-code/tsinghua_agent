"""Build an independent, upload-ready fast campus knowledge bundle.

This intentionally reads the frozen V1 corpus but never changes it.  It uses
short, source-grounded entries so a hosted Agent can retrieve an answer with
minimal context.
"""
from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "data" / "03_knowledge_base" / "v1"
OUT = ROOT / "release" / "fast_campus_kb_v1"

KEYWORDS = re.compile(
    r"车辆|宿舍|住宿|邮寄|课程|成绩|在学证明|成绩单|毕业|学位|课程替代|免修|"
    r"社团|图书馆|校医院|食堂|餐厅|在线手续|学生公寓|校园交通"
)

ALIASES = {
    "车辆-清华大学接待服务中心": "校车,校园巴士,校园交通车,内环外环,怎么坐校车,校车时间",
    "宿舍调整申请及办理流程": "换宿舍,调宿舍,申请调寝,宿舍调整,想换寝室",
    "2026.03.18 邮寄地址及邮条": "快递地址,宿舍收快递,邮寄地址,邮条,寄到学校",
    "住宿注意事项": "住校注意什么,宿舍规定,宿舍入住,住宿须知",
    "2023.04.24 清华大学学生公寓住宿管理办法": "学生公寓管理,宿舍管理办法,住宿管理",
    "在校生办理在学证明流程": "在读证明,在学证明,怎么开在读证明,学生证明",
    "毕业生办理成绩单": "成绩单,毕业生成绩单,打印成绩单",
    "毕业生办理毕业证书、学位证书制作件流程": "毕业证制作件,学位证制作件,毕业证复印件",
    "课程替代办理流程及申请表": "课程替代,替代课程,课程替换",
    "求真书院课程免修申请": "课程免修,免修申请,不想上这门课",
    "补办本科毕业（学位）证明": "补毕业证明,补学位证明,毕业证丢了,学位证丢了",
    "毕业证明书办理手续": "毕业证明书,毕业证丢失,补办毕业证",
    "研究生学位证明书办理流程": "研究生学位证明,学位证丢失,补学位证明",
    "清华大学图书馆": "图书馆,清图,借书,自习,图书馆服务",
    "校医院": "校医院,看病,挂号,就诊,体检,医疗",
    "学生食堂": "学生食堂,吃饭,食堂位置,紫荆园,桃李园",
    "教工餐厅": "教工餐厅,教师餐厅,观畴园,清芬园",
    "特色餐厅": "特色餐厅,清青快餐,清青休闲,餐厅位置",
}


def clean(text: str, limit: int = 560) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip("，、；：") + ("…" if len(text) > limit else "")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "references").mkdir(parents=True)
    (OUT / "all_official_public_sources").mkdir(parents=True)
    manifest = [json.loads(line) for line in (SOURCE_ROOT / "manifests" / "source_manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    public_sources = [row for row in manifest if row["source_type"] == "public"]
    selected = [row for row in manifest if KEYWORDS.search(row["title"])]
    selected_ids = {row["canonical_source_id"] for row in selected}
    chunks = [json.loads(line) for line in (SOURCE_ROOT / "chunks" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    by_source = defaultdict(list)
    for item in chunks:
        if item["canonical_source_id"] in selected_ids:
            by_source[item["canonical_source_id"]].append(item)

    faq = ["# FAST_CAMPUS_KB_V1 · 高频 FAQ\n", "本文件由已冻结、人工审查过的官方公开来源离线整理；每条只保留一个可检索答案单元。涉及时间、资格、入口等可能变化的信息，请以文末官方来源为准。\n"]
    cards = ["# FAST_CAMPUS_KB_V1 · Campus Cards\n"]
    source_log = []
    n = 0
    for row in selected:
        source_id, title, url = row["canonical_source_id"], row["title"], row["url"]
        body = (ROOT / row["canonical_file_path"]).read_text(encoding="utf-8")
        aliases = ALIASES.get(title, f"{title}, {row['category']}")
        cards.extend([
            f"## {title}\n",
            f"【一句话】{clean(body, 260)}\n",
            f"【常见问法】{aliases}\n",
            f"【适用范围】{row['category']}；请按页面最新要求办理。\n",
            f"【官方来源】{url}\n",
        ])
        for chunk in by_source[source_id]:
            n += 1
            faq.extend([
                f"## FAQ {n:03d}｜{title}\n",
                f"【标准问题】{title}有哪些关键信息？\n",
                f"【常见问法】{aliases}\n",
                f"【直接答案】{clean(chunk['text'])}\n",
                f"【来源】{url}\n",
            ])
        dest = OUT / "references" / f"{source_id}_{re.sub(r'[\\/:*?\"<>|]', '_', title)[:60]}.md"
        shutil.copyfile(ROOT / row["canonical_file_path"], dest)
        source_log.append({"source_id": source_id, "title": title, "url": url, "category": row["category"], "copied_to": str(dest.relative_to(OUT))})

    all_public_log = []
    for row in public_sources:
        title = re.sub(r'[\\/:*?\"<>|]', '_', row["title"])[:60]
        dest = OUT / "all_official_public_sources" / f"{row['canonical_source_id']}_{title}.md"
        shutil.copyfile(ROOT / row["canonical_file_path"], dest)
        all_public_log.append({"source_id": row["canonical_source_id"], "title": row["title"], "url": row["url"], "category": row["category"], "copied_to": str(dest.relative_to(OUT))})

    (OUT / "FAST_FAQ_V1.md").write_text("\n".join(faq), encoding="utf-8")
    (OUT / "CAMPUS_CARDS_V1.md").write_text("\n".join(cards), encoding="utf-8")
    (OUT / "REFERENCE_DOCS_MANIFEST.json").write_text(json.dumps(source_log, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "ALL_OFFICIAL_PUBLIC_SOURCES_MANIFEST.json").write_text(json.dumps(all_public_log, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        f"# FAST_CAMPUS_KB_V1\n\n独立的清园通极速知识库上传包。\n\n- 高频 FAQ：{n} 条（从官方来源短 chunk 离线重组）\n- Campus Cards：{len(selected)} 条\n- 精选 Reference Docs：{len(selected)} 份\n- 全量官方公开来源：{len(public_sources)} 份（不含 3 份 restricted 来源）\n- 来源：项目冻结的 `data/03_knowledge_base/v1`，本包没有回写旧资产。\n\n建议上传 `FAST_FAQ_V1.md`、`CAMPUS_CARDS_V1.md`、`references/` 与 `all_official_public_sources/`。使用按需知识检索、短上下文与 Top-K 3。\n",
        encoding="utf-8",
    )
    print(json.dumps({"faq": n, "cards": len(selected), "references": len(selected), "all_public_sources": len(public_sources), "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
