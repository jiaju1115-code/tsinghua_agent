from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from crawler.parser import parse_html
from crawler.similarity import simhash,similarity
from utils.metadata import category_hint,extract_metadata
from utils.url_utils import ATTACHMENT_EXTENSIONS,extension,is_allowed,normalize_url
from crawler.runner import now_iso
from portal.logger import PortalLogger
from portal.safety import is_public_candidate,portal_priority,private_reason
from portal.state import PortalState
from portal.writer import PortalWriter

@dataclass
class PortalStats:
    processed:int=0;success:int=0;failed:int=0;skipped:int=0;private:int=0;auth_expired:int=0;discovered:int=0;markdown:int=0;duplicates:int=0;possible_duplicates:int=0

class AuthExpired(RuntimeError):pass

class PortalCrawler:
    def __init__(self,config,root:Path):
        self.c=config;self.root=root;self.state=PortalState(root/"data"/"portal_state.db");self.log=PortalLogger(root/"logs");self.writer=PortalWriter(root);self.stats=PortalStats();self.track=set(config.get("tracking_parameters",[]));self.stop=False
        self.auth_dir=root/"data"/"auth";self.auth_dir.mkdir(parents=True,exist_ok=True);self.storage=self.auth_dir/"storage_state.json"

    def _cdp_endpoint(self):
        for port in self.c.get("portal_cdp_ports",[9222,9223]):
            try:
                r=requests.get(f"http://127.0.0.1:{port}/json/version",timeout=.5)
                if r.status_code==200 and r.json().get("webSocketDebuggerUrl"):return f"http://127.0.0.1:{port}"
            except (requests.RequestException,ValueError):pass
        return None

    def _is_login(self,page):
        url=page.url.lower();title=page.title().lower()
        return any(x in url for x in ("id.tsinghua.edu.cn","/login","/authserver")) or any(x in title for x in ("统一身份认证","用户登录","sign in"))

    def _browser(self,pw):
        endpoint=self._cdp_endpoint()
        if endpoint:
            browser=pw.chromium.connect_over_cdp(endpoint);context=browser.contexts[0];page=context.new_page()
            print("[Portal] 已通过官方 CDP 端口附着现有 Edge 会话。")
            return browser,context,page,True
        browser=pw.chromium.launch(channel="msedge",headless=bool(self.c.get("portal_headless",False)))
        kwargs={}
        if self.storage.exists():kwargs["storage_state"]=str(self.storage)
        context=browser.new_context(**kwargs);page=context.new_page()
        print("[Portal] 当前 Edge 未开放可附着的 CDP 端口，已启动专用可视 Edge。")
        return browser,context,page,False

    def _ensure_login(self,page,context):
        page.goto(self.c["portal_url"],wait_until="domcontentloaded",timeout=self.c["portal_navigation_timeout_ms"])
        if self._is_login(page):
            print("请在打开的浏览器中手动完成清华大学统一身份认证，登录成功并进入信息门户后继续。")
            deadline=time.monotonic()+int(self.c.get("portal_login_timeout_seconds",600))
            while time.monotonic()<deadline:
                time.sleep(2)
                try:
                    if not self._is_login(page) and is_allowed(page.url,self.c["allowed_domain"]):break
                except Exception:pass
            else:raise AuthExpired("manual_login_timeout")
        context.storage_state(path=str(self.storage))

    def _record_private(self,url,title,reason,stamp,row=None):
        if row is None:self.state.add(url,-1000,0,None,title,"deny_rule",stamp)
        self.state.finish(url,"private_skipped",stamp,reason)
        self.log.write("portal_private_skipped.csv",{"url":url,"title":title,"reason":reason,"timestamp":stamp});self.stats.private+=1

    def _discover(self,page,parent,depth,stamp):
        if depth>=int(self.c["max_portal_depth"]):return 0
        try:links=page.locator("a[href]").evaluate_all("els => els.map(a => ({href:a.href, text:(a.innerText||a.title||'').trim()}))")
        except Exception:return 0
        added=0
        for item in links:
            url=normalize_url(item.get("href",""),tracking=self.track);anchor=item.get("text","")[:300]
            if not url or not is_allowed(url,self.c["allowed_domain"]) or extension(url) in ATTACHMENT_EXTENSIONS:continue
            reason=private_reason(url,anchor)
            if reason:
                if self.state.add(url,-1000,depth+1,parent,anchor,"portal_link",stamp):self._record_private(url,anchor,reason,stamp,True)
                continue
            score=portal_priority(url,anchor)
            if score<=0:continue
            if self.state.add(url,score,depth+1,parent,anchor,"portal_link",stamp):added+=1
        return added

    def _process(self,page,row):
        url=row["url"];stamp=now_iso()
        reason=private_reason(url,row.get("anchor_text", ""))
        if reason:self._record_private(url,row.get("anchor_text", ""),reason,stamp,row);return
        try:page.goto(url,wait_until="domcontentloaded",timeout=self.c["portal_navigation_timeout_ms"]);page.wait_for_timeout(800)
        except PlaywrightTimeout:
            self.state.finish(url,"failed",stamp,"navigation_timeout");self.log.write("portal_failed.csv",{"url":url,"error_type":"timeout","error_message":"navigation_timeout","timestamp":stamp});self.stats.failed+=1;return
        if self._is_login(page):
            self.state.finish(url,"auth_expired",stamp,"redirected_to_login");self.log.write("portal_auth_expired.csv",{"url":url,"reason":"redirected_to_login","timestamp":stamp});self.stats.auth_expired+=1;raise AuthExpired("统一身份认证已失效，请重新登录。")
        title=page.title().strip() or row.get("anchor_text") or url;final=normalize_url(page.url,tracking=self.track) or page.url
        html=page.content();text=page.locator("body").inner_text(timeout=5000)
        reason=private_reason(final,row.get("anchor_text", ""),title,text)
        if reason:self._record_private(url,title,reason,stamp,row);return
        discovered=self._discover(page,url,row["depth"],stamp);self.stats.discovered+=discovered
        if row["depth"]==0:
            self.state.finish(url,"skipped",stamp,"navigation_hub");self.log.write("portal_skipped.csv",{"url":url,"title":title,"reason":"navigation_hub","timestamp":stamp});self.stats.skipped+=1;return
        if not is_public_candidate(final,title,text):
            self.state.finish(url,"skipped",stamp,"not_whitelisted_public_info");self.log.write("portal_skipped.csv",{"url":url,"title":title,"reason":"not_whitelisted_public_info","timestamp":stamp});self.stats.skipped+=1;return
        parsed=parse_html(html,final,self.track)
        if not parsed.quality or not parsed.quality.passed:
            self.state.finish(url,"skipped",stamp,"extraction_failed");self.log.write("portal_skipped.csv",{"url":url,"title":title,"reason":(parsed.quality.reason if parsed.quality else "extraction_failed"),"timestamp":stamp});self.stats.skipped+=1;return
        if len(parsed.plain_text)<int(self.c["min_content_chars"]):
            self.state.finish(url,"skipped",stamp,"no_meaningful_content");self.log.write("portal_skipped.csv",{"url":url,"title":title,"reason":"no_meaningful_content","timestamp":stamp});self.stats.skipped+=1;return
        digest=hashlib.sha256(parsed.plain_text.encode()).hexdigest();dup=self.state.find_hash(digest)
        if dup:self.state.finish(url,"duplicate",stamp,"exact_duplicate",dup["id"],digest);self.stats.duplicates+=1;return
        doc_id=self.state.next_id();sig=simhash(parsed.plain_text);possible=None
        for old in self.state.similar():
            score=similarity(sig,old["simhash"])
            if score>=float(self.c.get("possible_duplicate_threshold",.92)) and (not possible or score>possible[1]):possible=(old,score)
        meta=extract_metadata(parsed.soup);cat=category_hint(title+" "+parsed.plain_text[:4000])
        values={"id":doc_id,"title":title,"url":url,"final_url":final,"domain":urlsplit(final).hostname or "","department":meta["department"],"published_at":meta["published_at"],"updated_at":meta["updated_at"],"crawled_at":stamp,"category_hint":cat,"access_level":"campus_authenticated","source_mode":"authenticated_portal","content_length":len(parsed.plain_text),"content_hash":digest,"depth":row["depth"],"parent_url":row.get("parent_url") or "","anchor_text":row.get("anchor_text") or "","crawl_status":"success","extraction_method":parsed.extraction_method,"selector_used":parsed.selector_used,"content_quality_class":parsed.quality.content_quality_class}
        rel=self.writer.write(values,parsed.markdown,parsed.attachments);self.state.document((doc_id,url,digest,sig,title,rel,stamp));self.state.finish(url,"success",stamp,page_id=doc_id,digest=digest)
        self.log.write("portal_success.csv",{"id":doc_id,"url":url,"title":title,"markdown_path":rel,"timestamp":stamp});self.stats.success+=1;self.stats.markdown+=1
        if possible:
            old,score=possible;self.stats.possible_duplicates+=1
            from utils.logger import CrawlLogger
            CrawlLogger(self.root/"logs").csv("possible_duplicates.csv",{"id_1":old["id"],"id_2":doc_id,"url_1":old["url"],"url_2":url,"similarity":f"{score:.4f}","detected_at":stamp})
        print(f"[Portal 成功] {doc_id} {title[:60]}")

    def run(self):
        self.state.recover();self.state.reprioritize(portal_priority);stamp=now_iso();seed=normalize_url(self.c["portal_url"],tracking=self.track);self.state.add(seed,100,0,None,"信息门户","configured_seed",stamp)
        limit=int(self.c["portal_test_max_pages"] if self.c.get("portal_test_mode",True) else self.c["portal_max_pages"])
        try:
            with sync_playwright() as pw:
                browser=context=page=None;attached=False;authenticated=False
                try:
                    browser,context,page,attached=self._browser(pw);self._ensure_login(page,context);authenticated=True
                    while self.stats.processed<limit and not self.stop:
                        row=self.state.claim()
                        if not row:break
                        self.stats.processed+=1;self._process(page,row)
                except KeyboardInterrupt:self.stop=True;print("[Portal] 收到 Ctrl+C，状态已逐项保存。")
                except AuthExpired as exc:print(str(exc))
                finally:
                    if context and not attached and authenticated:
                        try:context.storage_state(path=str(self.storage))
                        except Exception:pass
                    if browser and not attached:
                        try:browser.close()
                        except Exception:pass
        finally:self.state.close()
        print(f"[Portal 汇总] 处理={self.stats.processed} 成功={self.stats.success} 失败={self.stats.failed} 跳过={self.stats.skipped} 私人阻止={self.stats.private} 认证失效={self.stats.auth_expired} Markdown={self.stats.markdown} 发现={self.stats.discovered}")
        return self.stats
