from __future__ import annotations
import csv
from pathlib import Path

SCHEMAS={
"portal_success.csv":["id","url","title","markdown_path","timestamp"],
"portal_failed.csv":["url","error_type","error_message","timestamp"],
"portal_skipped.csv":["url","title","reason","timestamp"],
"portal_private_skipped.csv":["url","title","reason","timestamp"],
"portal_auth_expired.csv":["url","reason","timestamp"],
}
class PortalLogger:
    def __init__(self,path:Path):
        self.path=path
        for name,fields in SCHEMAS.items():
            p=path/name
            if not p.exists():
                with p.open("w",newline="",encoding="utf-8-sig") as f:csv.DictWriter(f,fieldnames=fields).writeheader()
    def write(self,name,row):
        # 调用方只传 URL、标题、原因等非认证材料；禁止 Cookie/Token/Header 字段。
        with (self.path/name).open("a",newline="",encoding="utf-8-sig") as f:csv.DictWriter(f,fieldnames=SCHEMAS[name],extrasaction="ignore").writerow(row)

