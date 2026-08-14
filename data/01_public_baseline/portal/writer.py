from __future__ import annotations
import csv,json,re
from pathlib import Path
import yaml

FIELDS=["id","title","url","final_url","domain","department","published_at","updated_at","crawled_at","category_hint","access_level","source_mode","markdown_path","content_length","content_hash","depth","parent_url","anchor_text","crawl_status"]
ATTACH=["parent_page_id","parent_page_url","filename","file_url","file_type","access_level","discovered_at"]
def safe(s):return re.sub(r'[<>:"/\\|?*\x00-\x1f]',"_",s).strip(" ._")[:70] or "未命名页面"
class PortalWriter:
    def __init__(self,root:Path):
        self.root=root;self.raw=root/"knowledge"/"01_raw_portal";self.raw.mkdir(parents=True,exist_ok=True)
        self.csv=root/"knowledge"/"portal_index.csv";self.jsonl=root/"knowledge"/"portal_index.jsonl";self.attach=root/"knowledge"/"portal_attachments.csv"
        for p,fields in ((self.csv,FIELDS),(self.attach,ATTACH)):
            if not p.exists():
                with p.open("w",newline="",encoding="utf-8-sig") as f:csv.DictWriter(f,fieldnames=fields).writeheader()
        self.jsonl.touch(exist_ok=True)
    def write(self,m,body,attachments):
        p=self.raw/f"{m['id']}_{safe(m['title'])}.md"; front={"id":m["id"],"title":m["title"],"source_url":m["url"],"final_url":m["final_url"],"domain":m["domain"],"department":m["department"],"published_at":m["published_at"],"updated_at":m["updated_at"],"crawled_at":m["crawled_at"],"category_hint":m["category_hint"],"access_level":"campus_authenticated","source_mode":"authenticated_portal","content_hash":m["content_hash"]}
        text="---\n"+yaml.safe_dump(front,allow_unicode=True,sort_keys=False).strip()+"\n---\n\n# "+m["title"]+"\n\n"+body.strip()+"\n"
        if attachments:text+="\n## 官方附件\n\n"+"\n".join(f"- [{n}]({u})" for n,u,_ in attachments)+"\n"
        text+=f"\n---\n\n## 来源信息\n\n来源网页：{m['url']}\n\n最终访问地址：{m['final_url']}\n\n抓取时间：{m['crawled_at']}\n"
        p.write_text(text,encoding="utf-8"); rel=p.relative_to(self.root).as_posix(); row={k:m.get(k,"") for k in FIELDS};row["markdown_path"]=rel
        with self.csv.open("a",newline="",encoding="utf-8-sig") as f:csv.DictWriter(f,fieldnames=FIELDS).writerow(row)
        with self.jsonl.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
        if attachments:
            with self.attach.open("a",newline="",encoding="utf-8-sig") as f:
                w=csv.DictWriter(f,fieldnames=ATTACH)
                for n,u,t in attachments:w.writerow({"parent_page_id":m["id"],"parent_page_url":m["url"],"filename":n,"file_url":u,"file_type":t,"access_level":"campus_authenticated","discovered_at":m["crawled_at"]})
        return rel
