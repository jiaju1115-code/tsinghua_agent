from __future__ import annotations
import json, hashlib
from pathlib import Path

def _read(path):
    with open(path, encoding="utf-8") as f: return [json.loads(x) for x in f if x.strip()]

def discover(config, limit=None):
    decisions = {x["canonical_source_id"]: x for x in _read(config["eligibility_manifest"])}
    out=[]
    for row in _read(config["source_manifest"]):
        d=decisions.get(row["canonical_source_id"], {})
        if row.get("source_type") != "public" or d.get("status") != "include": continue
        p=Path(row["canonical_file_path"])
        if not p.exists(): continue
        text=p.read_text(encoding="utf-8", errors="replace")
        if len(text.strip()) < 80: continue
        out.append({"source_id":row["canonical_source_id"],"path":str(p),"title":row.get("title",""),"url":row.get("url",""),"category":row.get("category",""),"source_type":"public","content":text,"content_sha256":hashlib.sha256(text.encode()).hexdigest()})
    return out[:limit] if limit else out
