from __future__ import annotations

import csv
import json
import re
from pathlib import Path
import yaml

INDEX_FIELDS = ["id","title","category_hint","department","published_at","updated_at","source_url","final_url","domain","crawled_at","content_hash","markdown_path"]
ATTACH_FIELDS = ["parent_page_id","parent_page_url","filename","file_url","file_type","discovered_at"]

def safe_title(title: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" ._")
    return value[:70] or "未命名页面"

class MarkdownWriter:
    def __init__(self, project_root: Path, raw_dir: Path):
        self.root, self.raw_dir = project_root, raw_dir
        self.index_csv = project_root / "knowledge" / "index.csv"
        self.index_jsonl = project_root / "knowledge" / "index.jsonl"
        self.attach_csv = project_root / "knowledge" / "attachments.csv"
        for path, fields in ((self.index_csv, INDEX_FIELDS),(self.attach_csv,ATTACH_FIELDS)):
            if not path.exists():
                with path.open("w", newline="", encoding="utf-8-sig") as f: csv.DictWriter(f, fieldnames=fields).writeheader()
        self.index_jsonl.touch(exist_ok=True)

    def write(self, metadata: dict, body: str, attachments, images) -> tuple[Path,str]:
        filename = f"{metadata['id']}_{safe_title(metadata['title'])}.md"
        path = self.raw_dir / filename
        front = {k: metadata.get(k, "") for k in ("id","title","source_url","final_url","domain","department","published_at","updated_at","crawled_at","category_hint","access_level","source_mode","content_hash")}
        text = "---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n"
        if not body.lstrip().startswith("# "): text += f"# {metadata['title']}\n\n"
        text += body.strip() + "\n"
        if attachments:
            text += "\n## 官方附件\n\n" + "\n".join(f"- [{name}]({url})" for name,url,_ in attachments) + "\n"
        if images:
            text += "\n## 相关图片\n\n" + "\n".join(f"- {name or '相关图片'}：{url}" for name,url in images) + "\n"
        text += f"\n---\n\n## 来源信息\n\n来源网页：{metadata['source_url']}\n\n最终访问地址：{metadata['final_url']}\n\n抓取时间：{metadata['crawled_at']}\n"
        path.write_text(text, encoding="utf-8")
        rel = path.relative_to(self.root).as_posix()
        row = {k: metadata.get(k, "") for k in INDEX_FIELDS}; row["markdown_path"] = rel
        with self.index_csv.open("a", newline="", encoding="utf-8-sig") as f: csv.DictWriter(f, fieldnames=INDEX_FIELDS).writerow(row)
        with self.index_jsonl.open("a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if attachments:
            with self.attach_csv.open("a", newline="", encoding="utf-8-sig") as f:
                w=csv.DictWriter(f, fieldnames=ATTACH_FIELDS)
                for name,url,kind in attachments: w.writerow({"parent_page_id":metadata["id"],"parent_page_url":metadata["source_url"],"filename":name,"file_url":url,"file_type":kind,"discovered_at":metadata["crawled_at"]})
        return path, rel
