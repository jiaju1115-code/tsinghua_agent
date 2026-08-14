from __future__ import annotations
import csv,hashlib,json
from pathlib import Path
from utils.paths import SOURCE_ROOT,PROJECT_ROOT,DATA_DIR,assert_destination

FIELDS=["id","title","source_url","final_url","domain","department","published_at","updated_at","crawled_at","category_hint","access_level","source_mode","dataset_origin","source_markdown_path","content_length","content_hash"]

def _read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def _origin(path):
    p=path.replace("\\","/")
    if "/01_raw_public/" in "/"+p:return "public"
    if "/01_raw_portal/" in "/"+p:return "portal"
    return "legacy_public"

def _candidate(row,portal=False):
    rel=row.get("markdown_path","").replace("\\","/");path=SOURCE_ROOT/rel
    if not path.exists():raise FileNotFoundError(path)
    origin=_origin(rel);text=path.read_text(encoding="utf-8")
    return {"id":row["id"],"title":row.get("title","").strip(),"source_url":row.get("source_url") or row.get("url","") ,"final_url":row.get("final_url","") or row.get("url","") ,"domain":row.get("domain","") ,"department":row.get("department","") ,"published_at":row.get("published_at","") ,"updated_at":row.get("updated_at","") ,"crawled_at":row.get("crawled_at","") ,"category_hint":row.get("category_hint","") ,"access_level":"campus_authenticated" if portal else "public","source_mode":"authenticated_portal" if portal else "public_web","dataset_origin":origin,"source_markdown_path":rel,"content_length":int(row.get("content_length") or len(text)),"content_hash":row.get("content_hash","")}

def load_candidates():
    pub=[_candidate(r) for r in _read_csv(SOURCE_ROOT/"knowledge"/"index.csv")]
    portal=[_candidate(r,True) for r in _read_csv(SOURCE_ROOT/"knowledge"/"portal_index.csv")]
    kept,duplicates=deduplicate_public(pub)
    return kept+portal,duplicates

def deduplicate_public(pub):
    # Public优先于legacy；只对公开历史层做source/final/hash交叉去重，Portal访问等级不合并。
    ordered=sorted(pub,key=lambda x:0 if x["dataset_origin"]=="public" else 1)
    kept=[];seen=set();duplicates=[]
    for c in ordered:
        keys={f"s:{c['source_url']}",f"f:{c['final_url']}",f"h:{c['content_hash']}"}
        keys.discard("s:");keys.discard("f:");keys.discard("h:")
        if keys & seen:duplicates.append(c);continue
        kept.append(c);seen.update(keys)
    return kept,duplicates

def write_candidate_index(candidates,duplicates):
    csv_path=DATA_DIR/"candidate_index.csv";jsonl=DATA_DIR/"candidate_index.jsonl";assert_destination(csv_path)
    with csv_path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(candidates)
    with jsonl.open("w",encoding="utf-8") as f:
        for row in candidates:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    with (DATA_DIR/"excluded_duplicates.jsonl").open("w",encoding="utf-8") as f:
        for row in duplicates:f.write(json.dumps(row,ensure_ascii=False)+"\n")

def read_candidate_index():
    return _read_csv(DATA_DIR/"candidate_index.csv")

def source_manifest():
    rows=[]
    for p in sorted(x for x in SOURCE_ROOT.rglob("*") if x.is_file()):
        h=hashlib.sha256()
        with p.open("rb") as f:
            for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
        rows.append({"path":p.relative_to(SOURCE_ROOT).as_posix(),"size":p.stat().st_size,"sha256":h.hexdigest()})
    return rows

def write_manifest(name="source_manifest_before.json"):
    path=DATA_DIR/name;assert_destination(path);path.write_text(json.dumps(source_manifest(),ensure_ascii=False,indent=2),encoding="utf-8")
