from __future__ import annotations

import hashlib
import mimetypes
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from crawler.discovery import discover
from crawler.fetcher import Fetcher
from crawler.prioritizer import priority_score
from crawler.similarity import simhash, similarity
from crawler.sitemap import sitemap_urls
from crawler.markdown_writer import MarkdownWriter
from crawler.parser import detect_page, parse_html
from crawler.state import CrawlState
from utils.logger import CrawlLogger
from utils.metadata import category_hint, extract_metadata
from utils.url_utils import is_allowed, normalize_url

def now_iso(): return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

@dataclass
class Stats:
    processed:int=0; success:int=0; failed:int=0; skipped:int=0; auth:int=0; duplicates:int=0; discovered:int=0; markdown:int=0

class Crawler:
    def __init__(self, config, root: Path):
        self.config, self.root = config, root
        self.state=CrawlState(root/"data"/"crawl_state.db"); self.logger=CrawlLogger(root/"logs")
        public_dir=root/config.get("public_raw_dir","knowledge/01_raw_public")
        public_dir.mkdir(parents=True,exist_ok=True)
        self.fetcher=Fetcher(config); self.writer=MarkdownWriter(root,public_dir)
        self.stats=Stats(); self.stop=False; self.tracking=set(config.get("tracking_parameters",[]))

    def seed(self):
        seed_path=self.root/self.config.get("seeds_file","seeds.txt")
        do_sitemap=bool(self.config.get("sitemap_enabled")) and self.state.setting("sitemaps_seeded_v11")!="1"
        for line in seed_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#"): continue
            url=normalize_url(line,tracking=self.tracking)
            if url and is_allowed(url,self.config["allowed_domain"]) and self.state.add_url(url,0,None,now_iso(),priority_score(url)): self.stats.discovered+=1
            if url and do_sitemap:
                for sm_url,score in sitemap_urls(self.fetcher,url,self.config["allowed_domain"],self.tracking,int(self.config.get("sitemap_max_urls_per_seed",300))):
                    if self.state.add_url(sm_url,1,url,now_iso(),score): self.stats.discovered+=1
        if do_sitemap:self.state.set_setting("sitemaps_seeded_v11","1")

    def process(self,row):
        url,depth=row["url"],row["depth"]; stamp=now_iso()
        if not self.fetcher.allowed_by_robots(url): return ("skip",url,"robots_disallowed",None)
        got=self.fetcher.fetch(url)
        if not got.response: return ("fail",url,got.error,got.retries)
        r=got.response; final=normalize_url(r.url,tracking=self.tracking) or r.url
        if not is_allowed(final,self.config["allowed_domain"]): return ("skip",url,"outside_domain_redirect",None)
        if r.status_code != 200: return ("fail",url,f"http_{r.status_code}",got.retries)
        ctype=r.headers.get("Content-Type","").lower()
        if "html" not in ctype and "xhtml" not in ctype: return ("skip",url,"unsupported_content_type",None)
        r.encoding=r.apparent_encoding or r.encoding or "utf-8"; html=r.text
        reason=detect_page(html,final)
        if reason: return (("auth" if reason=="login_required" else "skip"),url,reason,final)
        page=parse_html(html,final,self.tracking)
        if not page.quality or not page.quality.passed: return ("skip",url,(page.quality.reason if page.quality else "extraction_failed"),None)
        if len(page.plain_text)<int(self.config["min_content_chars"]): return ("skip",url,"no_meaningful_content",None)
        digest=hashlib.sha256(page.plain_text.encode("utf-8")).hexdigest()
        duplicate=self.state.find_hash(digest)
        if duplicate: return ("duplicate",url,(duplicate["url"],digest),None)
        meta=extract_metadata(page.soup); title=meta["title"] or final
        doc_id=self.state.next_id()
        values={**meta,"id":doc_id,"title":title,"source_url":url,"final_url":final,"domain":urlsplit(final).hostname or "","crawled_at":stamp,"category_hint":category_hint(title+" "+page.plain_text[:4000]),"access_level":"public","source_mode":"public_web","content_hash":digest,"extraction_method":page.extraction_method,"selector_used":page.selector_used,"content_quality_class":page.quality.content_quality_class}
        path,rel=self.writer.write(values,page.markdown,page.attachments,page.images)
        signature=simhash(page.plain_text)
        possible=None
        threshold=float(self.config.get("possible_duplicate_threshold",.92))
        for old in self.state.similar_documents():
            score=similarity(signature,old["simhash"])
            if score>=threshold and (possible is None or score>possible[1]): possible=(old,score)
        self.state.add_document((doc_id,url,final,digest,title,rel,stamp),signature)
        if possible:
            old,score=possible
            self.logger.csv("possible_duplicates.csv",{"id_1":old["id"],"id_2":doc_id,"url_1":old["url"],"url_2":url,"similarity":f"{score:.4f}","detected_at":stamp})
        found=discover(page.links,self.config["allowed_domain"],depth,int(self.config["max_depth"]),self.tracking)
        added=0
        for new,score in found:
            if self.state.add_url(new,depth+1,url,stamp,score): added+=1
        return ("success",url,(doc_id,title,rel,added),None)

    def handle(self,result):
        kind,url,data,extra=result; stamp=now_iso(); self.stats.processed+=1
        if kind=="success":
            doc_id,title,rel,added=data; self.stats.success+=1; self.stats.markdown+=1; self.stats.discovered+=added
            self.state.finish(url,"success",stamp); self.logger.csv("success.csv",{"id":doc_id,"url":url,"title":title,"markdown_path":rel,"timestamp":stamp}); print(f"[成功] {self.stats.processed:03d} {title[:60]}")
        elif kind=="duplicate":
            canonical,digest=data; self.stats.duplicates+=1; self.state.finish(url,"duplicate",stamp); self.logger.csv("duplicates.csv",{"duplicate_url":url,"canonical_url":canonical,"content_hash":digest,"detected_at":stamp}); print(f"[重复] {url}")
        elif kind=="auth":
            self.stats.auth+=1; self.state.finish(url,"auth_required",stamp); self.logger.csv("auth_required.csv",{"url":url,"final_url":extra,"detected_reason":data,"timestamp":stamp}); print(f"[跳过] 需要认证 {url}")
        elif kind=="skip":
            self.stats.skipped+=1; self.state.finish(url,"skipped",stamp,error=data); self.logger.csv("skipped.csv",{"url":url,"reason":data,"timestamp":stamp}); print(f"[跳过] {data} {url}")
        else:
            self.stats.failed+=1; self.state.finish(url,"failed",stamp,error=data,retries=extra or 0); self.logger.csv("failed.csv",{"url":url,"error_type":str(data).split(":",1)[0],"error_message":data,"retry_count":extra or 0,"timestamp":stamp}); print(f"[失败] {data} {url}")

    def run(self):
        self.state.recover(bool(self.config.get("retry_failed_on_start"))); self.state.reprioritize(priority_score); self.seed()
        limit=int(self.config["test_max_pages"] if self.config.get("test_mode",True) else self.config["max_pages"])
        print(f"[INFO] {'测试' if self.config.get('test_mode',True) else '正式'}模式：本次最多处理 {limit} 个页面")
        futures={}
        try:
            with ThreadPoolExecutor(max_workers=int(self.config["concurrency"])) as pool:
                while (self.stats.processed < limit) and not self.stop:
                    while len(futures)<int(self.config["concurrency"]) and self.stats.processed+len(futures)<limit:
                        row=self.state.claim()
                        if not row: break
                        futures[pool.submit(self.process,row)]=row
                    if not futures: break
                    done,_=wait(set(futures),return_when=FIRST_COMPLETED)
                    for future in done:
                        row=futures.pop(future)
                        try: self.handle(future.result())
                        except Exception as exc:
                            stamp=now_iso();message=f"{type(exc).__name__}: {exc}";self.state.finish(row["url"],"failed",stamp,error=message)
                            self.logger.csv("failed.csv",{"url":row["url"],"error_type":"internal_error","error_message":message,"retry_count":0,"timestamp":stamp})
                            print(f"[内部错误] {message}"); self.stats.failed+=1; self.stats.processed+=1
        except KeyboardInterrupt:
            self.stop=True; print("\n[INFO] 收到 Ctrl+C，正在安全保存状态……")
        finally:
            counts=self.state.counts(); self.state.close()
        print("\n============================\n本次运行完成")
        print(f"处理页面：{self.stats.processed}\n成功抓取：{self.stats.success}\n重复页面：{self.stats.duplicates}\n需要认证：{self.stats.auth}\n失败：{self.stats.failed}\n跳过：{self.stats.skipped}\n新发现URL：{self.stats.discovered}\n生成Markdown：{self.stats.markdown}")
        print(f"输出目录：{self.writer.raw_dir}\n============================")
        return self.stats
