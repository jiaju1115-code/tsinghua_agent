from __future__ import annotations

import csv, hashlib, heapq, json, re, sys, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests, yaml
import urllib3

ROOT = Path(r"D:\python_projects\tsinghua_ai")
FIRST = ROOT / "data_first"
OUT = ROOT / "data_second" / "public_expansion_v1" / "run_6"
sys.path.insert(0, str(FIRST))

from crawler.parser import detect_page, parse_html
from crawler.prioritizer import priority_score
from crawler.similarity import simhash, similarity
from utils.metadata import category_hint, extract_metadata
from utils.url_utils import ATTACHMENT_EXTENSIONS, SKIP_EXTENSIONS, extension, normalize_url

RAW, CLEAN, REPORTS = OUT/"raw", OUT/"cleaned", OUT/"reports"
for p in (RAW,CLEAN,REPORTS): p.mkdir(parents=True, exist_ok=True)
if any(RAW.glob("*.md")) or any(CLEAN.glob("*.md")):
    raise SystemExit("隔离输出目录已有未完成抓取文件；为避免覆盖，请先清理本轮未完成产物后重跑。")

APPROVED_HOSTS = {
    "www.tsinghua.edu.cn", "its.tsinghua.edu.cn", "www.itc.tsinghua.edu.cn",
    "lib.tsinghua.edu.cn", "xyy.tsinghua.edu.cn", "www.thsports.tsinghua.edu.cn",
    "peace.tsinghua.edu.cn", "yz.tsinghua.edu.cn", "www.tuef.tsinghua.edu.cn",
}
SEEDS = [
    "https://www.tsinghua.edu.cn/", "https://its.tsinghua.edu.cn/",
    "https://www.itc.tsinghua.edu.cn/", "https://lib.tsinghua.edu.cn/",
    "https://www.tsinghua.edu.cn/ysfwzx/", "https://xyy.tsinghua.edu.cn/",
    "https://www.thsports.tsinghua.edu.cn/", "https://peace.tsinghua.edu.cn/",
    "https://www.tsinghua.edu.cn/qhdxzwzbgs/", "https://www.tsinghua.edu.cn/yjsy/bszn.htm",
]
TRACKING={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","spm","from"}
TARGET, HARD_VALID_LIMIT, MAX_ATTEMPTS, MAX_DEPTH = 300, 350, 1800, 4
UA="TsinghuaCampusKnowledgeCollector/1.0 (public academic project; respectful crawler)"

def now(): return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
def norm(u,base=None): return normalize_url(u,base,TRACKING)
def safe(s): return (re.sub(r'[<>:"/\\|?*\x00-\x1f]',"_",s).strip(" ._")[:80] or "未命名")
def tnorm(s): return re.sub(r"[^\w\u4e00-\u9fff]","",s.lower())

def historical():
    urls, hashes, titles, sigs = set(), set(), set(), []
    for idx in [FIRST/"knowledge/index.csv", ROOT/"data_second/data/candidate_index.csv"]:
        if not idx.exists(): continue
        with idx.open(encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r.get("access_level","public") != "public" or r.get("source_mode","public_web") == "portal_browser": continue
                for k in ("source_url","final_url","url"):
                    u=norm(r.get(k,"")) if r.get(k) else None
                    if u: urls.add(u)
                if r.get("content_hash"): hashes.add(r["content_hash"])
                if r.get("title"): titles.add(tnorm(r["title"]))
    for d in [FIRST/"knowledge/01_raw",FIRST/"knowledge/01_raw_public"]:
        if d.exists():
            for p in d.glob("*.md"):
                text=p.read_text(encoding="utf-8",errors="ignore")
                body=text.split("---",2)[-1]
                if len(body)>150: sigs.append(simhash(body))
    return urls,hashes,titles,sigs

HIST_URLS,HIST_HASHES,HIST_TITLES,HIST_SIGS=historical()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session=requests.Session();session.trust_env=False;session.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
seen=set(); queue=[]; counter=0; valid=[]; internal_hashes=set(); internal_titles=set(); internal_sigs=[]
stats={"discovered_urls":0,"attempted":0,"fetch_failed":0,"crawl_invalid":0,"historical_duplicates":0,"internal_duplicates":0,"valid_candidates":0,"auth_skipped":0,"outside_or_new_domain":0}
new_domains=set(); invalid=[]; failures=[]; duplicates=[]

def add(u,depth,parent="",anchor=""):
    global counter
    u=norm(u,parent or None)
    if not u or u in seen: return
    host=(urlsplit(u).hostname or "").lower()
    if not (host=="tsinghua.edu.cn" or host.endswith(".tsinghua.edu.cn")): return
    if host not in APPROVED_HOSTS:
        new_domains.add(host); stats["outside_or_new_domain"]+=1; return
    if extension(u) in ATTACHMENT_EXTENSIONS|SKIP_EXTENSIONS: return
    low=u.lower()
    if any(x in low for x in ("/login","logout","caslogin","authserver","sso","oauth","search.jsp","search.htm","javascript:")): return
    if u in HIST_URLS:
        stats["historical_duplicates"]+=1; duplicates.append({"url":u,"type":"historical_url"}); seen.add(u); return
    seen.add(u);counter+=1;stats["discovered_urls"]+=1
    heapq.heappush(queue,(-priority_score(u,anchor),depth,counter,u,parent))

for s in SEEDS: add(s,0)

last_by_host={}
while queue and len(valid)<TARGET and stats["attempted"]<MAX_ATTEMPTS:
    neg,depth,_,url,parent=heapq.heappop(queue); stats["attempted"]+=1
    host=urlsplit(url).hostname or ""; wait=0.75-(time.monotonic()-last_by_host.get(host,0))
    if wait>0: time.sleep(wait)
    try:
        r=session.get(url,timeout=20,allow_redirects=True,verify=False)
        last_by_host[host]=time.monotonic()
        if r.status_code!=200: raise RuntimeError(f"http_{r.status_code}")
        final=norm(r.url) or r.url; fhost=(urlsplit(final).hostname or "").lower()
        if fhost not in APPROVED_HOSTS: raise RuntimeError("outside_domain_redirect")
        if "html" not in r.headers.get("Content-Type","").lower(): raise RuntimeError("unsupported_content_type")
        if len(r.content)>10*1024*1024: raise RuntimeError("response_too_large")
        # Prefer the server/meta-declared charset.  ``apparent_encoding`` often
        # mistakes UTF-8 Chinese pages for a legacy single-byte encoding and
        # silently produces mojibake.
        raw_bytes = r.content
        # UTF-8 is by far the most common encoding in the approved sites and
        # can be detected losslessly. Only fall back to the declared charset
        # and then GB18030 when strict UTF-8 decoding fails.
        try:
            html = raw_bytes.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            content_type = r.headers.get("Content-Type", "")
            head = raw_bytes[:8192].decode("ascii", errors="ignore")
            charset_match = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9._-]+)", content_type + " " + head, re.I)
            declared = charset_match.group(1) if charset_match else "gb18030"
            codec = "gb18030" if declared.lower() in {"gb2312", "gbk", "gb18030"} else declared
            html = raw_bytes.decode(codec, errors="replace")
    except Exception as e:
        stats["fetch_failed"]+=1;failures.append({"url":url,"reason":str(e)});continue
    reason=detect_page(html,final)
    if reason:
        stats["auth_skipped" if reason=="login_required" else "crawl_invalid"]+=1;invalid.append({"url":url,"reason":reason});continue
    page=parse_html(html,final,TRACKING); meta=extract_metadata(page.soup); title=(meta.get("title") or final).strip()
    # Navigation/list pages may fail knowledge-entry quality checks but remain
    # useful discovery surfaces.  Follow their in-scope links before filtering.
    if depth<MAX_DEPTH:
        for href,anchor in page.links: add(href,depth+1,final,anchor)
    if not page.quality or not page.quality.passed:
        qclass=page.quality.content_quality_class if page.quality else "extraction_failed"
        qreason=page.quality.reason if page.quality else "正文质量闸门无结果"
        stats["crawl_invalid"]+=1
        invalid.append({"url":url,"reason":f"{qclass}:{qreason}","extraction_method":page.extraction_method,"selector_used":page.selector_used})
        continue
    plain=re.sub(r"\s+"," ",page.plain_text).strip()
    qreason=""
    if len(plain)<220:qreason="content_too_short"
    elif re.search(r"页面不存在|系统错误|访问出错|验证码|请登录|统一身份认证",plain[:1000],re.I):qreason="error_or_login_page"
    elif len(set(plain))<35:qreason="low_information_content"
    elif not title or tnorm(title) in {"","首页","index"}:qreason="invalid_title"
    if qreason:
        stats["crawl_invalid"]+=1;invalid.append({"url":url,"reason":qreason});continue
    digest=hashlib.sha256(plain.encode()).hexdigest(); ts=tnorm(title); sig=simhash(plain)
    if norm(final) in HIST_URLS or digest in HIST_HASHES or ts in HIST_TITLES or any(similarity(sig,x)>=.97 for x in HIST_SIGS):
        stats["historical_duplicates"]+=1;duplicates.append({"url":url,"type":"historical_content"});continue
    if digest in internal_hashes or ts in internal_titles or any(similarity(sig,x)>=.97 for x in internal_sigs):
        stats["internal_duplicates"]+=1;duplicates.append({"url":url,"type":"internal_content"});continue
    doc_id=f"PUBEXP{len(valid)+1:06d}"; stamp=now(); filename=f"{doc_id}_{safe(title)}.md"
    front={"id":doc_id,"title":title,"source_url":url,"final_url":final,"domain":fhost,"published_at":meta.get("published_at",""),"updated_at":meta.get("updated_at",""),"crawled_at":stamp,"category_hint":category_hint(title+" "+plain[:4000]),"access_level":"public","source_mode":"public_expansion_v1","content_hash":digest,"extraction_method":page.extraction_method,"selector_used":page.selector_used,"content_quality_class":page.quality.content_quality_class}
    text="---\n"+yaml.safe_dump(front,allow_unicode=True,sort_keys=False).strip()+"\n---\n\n"
    if not page.markdown.lstrip().startswith("# "): text+=f"# {title}\n\n"
    text+=page.markdown.strip()+f"\n\n---\n\n## 来源信息\n\n来源网页：{url}\n\n最终访问地址：{final}\n\n抓取时间：{stamp}\n"
    (RAW/filename).write_text(text,encoding="utf-8"); (CLEAN/filename).write_text(text,encoding="utf-8")
    row={**front,"url":url,"source_domain":fhost,"source_file":f"cleaned/{filename}","crawl_time":stamp,"content_length":len(plain)}
    valid.append(row);internal_hashes.add(digest);internal_titles.add(ts);internal_sigs.append(sig);stats["valid_candidates"]=len(valid)
    if len(valid)%25==0: print(f"[进度] 有效候选 {len(valid)}/{TARGET}，尝试 {stats['attempted']}，队列 {len(queue)}",flush=True)

def write_csv(name,rows,fields):
    with (REPORTS/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
fields=list(valid[0].keys()) if valid else ["id","title","url"]
write_csv("candidates.csv",valid,fields);write_csv("failures.csv",failures,["url","reason"]);write_csv("crawl_invalid.csv",invalid,["url","reason"]);write_csv("duplicates.csv",duplicates,["url","type"])
write_csv("new_domain_candidates.csv",[{"domain":x} for x in sorted(new_domains)],["domain"])
(REPORTS/"crawl_stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(stats,ensure_ascii=False),flush=True)
