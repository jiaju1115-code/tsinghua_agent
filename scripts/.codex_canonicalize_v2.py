from __future__ import annotations
import csv,hashlib,json,re,subprocess,sys,threading,time
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter,defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from bs4 import UnicodeDammit
ROOT=Path(r"D:\python_projects\tsinghua_ai");OUT=ROOT/"data_second/public_expansion_v2"
sys.path.insert(0,str(ROOT/"data_first"));from crawler.parser import detect_page,parse_html
RAWD=OUT/"raw/canonical";EXTD=OUT/"extracted/canonical";RAWD.mkdir(parents=True,exist_ok=True);EXTD.mkdir(parents=True,exist_ok=True)
TRACK={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","spm","from"};LOCK=defaultdict(threading.Lock);LAST=defaultdict(float)
def norm(u,b=""):
 try:
  p=urlsplit(urljoin(b,u.strip()));h=(p.hostname or"").lower()
  if p.scheme not in{"http","https"}or not(h=="tsinghua.edu.cn"or h.endswith(".tsinghua.edu.cn")):return""
  q=urlencode(sorted((k,v)for k,v in parse_qsl(p.query,keep_blank_values=True)if k.lower()not in TRACK));return urlunsplit((p.scheme.lower(),h,re.sub(r"/{2,}","/",p.path or"/"),q,""))
 except:return""
def dec(b):return UnicodeDammit(b,is_html=True).unicode_markup or b.decode(errors="replace")
def fetch(u,p):
 if p.exists() and p.stat().st_size>200:
  return{"ok":True,"http_status":200,"final_url":u,"content_type":"text/html","bytes":p.stat().st_size,"error":"","reused_raw":True}
 h=urlsplit(u).hostname or""
 with LOCK[h]:d=.25-(time.monotonic()-LAST[h]);time.sleep(max(0,d));LAST[h]=time.monotonic()
 try:
  z=subprocess.run(["curl.exe","-k","-L","--http1.1","--compressed","--connect-timeout","10","--max-time","40","--retry","1","-A","Mozilla/5.0 (compatible; TsinghuaKnowledgeBot/2.0)","-o",str(p),"-sS","-w","%{http_code}\t%{url_effective}\t%{content_type}",u],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=55);a=z.stdout.strip().split("\t");st=int(a[0])if a and a[0].isdigit()else 0
  return{"ok":z.returncode==0 and 200<=st<400 and p.exists()and p.stat().st_size>200,"http_status":st,"final_url":a[1]if len(a)>1else u,"content_type":a[2]if len(a)>2else"","bytes":p.stat().st_size if p.exists()else 0,"error":z.stderr[:300]}
 except Exception as e:return{"ok":False,"http_status":0,"final_url":u,"content_type":"","bytes":0,"error":str(e)}
def jl(p):return[json.loads(x)for x in p.read_text(encoding="utf-8").splitlines()if x.strip()]
def history():
 urls=set();titles=[];hashes=set()
 for base in[ROOT/"data_first",ROOT/"data_second"]:
  for p in base.rglob("*"):
   if not p.is_file()or OUT in p.parents or p.stat().st_size>8_000_000:continue
   try:
    if p.suffix==".jsonl":
     for line in p.open(encoding="utf-8",errors="ignore"):
      try:r=json.loads(line)
      except:continue
      for k in("url","source_url","final_url","normalized_url"):
       u=norm(str(r.get(k,"")));u and urls.add(u)
      t=re.sub(r"\W+","",str(r.get("title",""))).lower();t and titles.append(t)
      h=r.get("content_hash");h and hashes.add(h)
    elif p.suffix==".csv":
     for r in csv.DictReader(p.open(encoding="utf-8-sig",errors="ignore")):
      u=norm(r.get("url","")or r.get("source_url","")or"");u and urls.add(u)
   except:pass
 return urls,titles,hashes
files=["discovered_urls.jsonl","follow_discovered_urls.jsonl","round3_discovered_urls.jsonl","round4_discovered_urls.jsonl","round5_discovered_urls.jsonl"]
allr=[]
for f in files:
 p=OUT/"crawl"/f
 if p.exists():
  for r in jl(p):r["round_source_file"]=f;allr.append(r)
hist_urls,hist_titles,hist_hashes=history();disc={}
for r in allr:
 u=norm(r.get("url",""));
 if u and u not in disc:disc[u]={**r,"url":u,"normalized_url":u}
hist_url_dupe=hist_title_dupe=0;selected=[]
for u,r in disc.items():
 if u in hist_urls:hist_url_dupe+=1;continue
 tk=re.sub(r"\W+","",r.get("title","")).lower();cands=[z for z in hist_titles if abs(len(z)-len(tk))<=3 and z[:4]==tk[:4]] if len(tk)>=4 else[]
 if tk and any(SequenceMatcher(None,tk,z).ratio()>.96 for z in cands):hist_title_dupe+=1;continue
 selected.append(r)
selected.sort(key=lambda x:(x.get("discovery_category",""),x["url"]))
for i,r in enumerate(selected,1):r["id"]=f"PUBV2C-{i:04d}";r["canonical_raw_file"]=f"raw/canonical/{r['id']}.html"
(OUT/"crawl/canonical_discovered_urls.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in selected),encoding="utf-8")
got=[]
with ThreadPoolExecutor(max_workers=5)as ex:
 fut={ex.submit(fetch,r["url"],RAWD/f"{r['id']}.html"):r for r in selected}
 for j,f in enumerate(as_completed(fut),1):got.append({**fut[f],**f.result(),"crawl_timestamp":datetime.now().isoformat(timespec="seconds")});print(f"canonical fetch {j}/{len(selected)}",flush=True)if j%50==0 else None
got.sort(key=lambda x:x["id"]);qrows=[];seen_hash=set(hist_hashes);seen_titles=[];internal=0
for r in got:
 row={**r,"normalized_url":norm(r.get("final_url")or r["url"]),"domain":urlsplit(r.get("final_url")or r["url"]).hostname or""}
 if not r["ok"]:row.update(quality_class="content_missing",quality_gate_pass=False,diagnostic_reason=r["error"],extraction_method="request_failed",selector_used="",content_hash="",source_file="");qrows.append(row);continue
 html=dec((RAWD/f"{r['id']}.html").read_bytes());kind=detect_page(html,row["normalized_url"])
 if kind:row.update(quality_class=kind,quality_gate_pass=False,diagnostic_reason=kind,extraction_method=kind,selector_used="",content_hash="",source_file="");qrows.append(row);continue
 page=parse_html(html,row["normalized_url"],TRACK);q=page.quality;cls=q.content_quality_class;passed=bool(q.passed and cls in{"detail_content","thin_content","template_polluted"});title=r.get("title","").strip();h=hashlib.sha256(re.sub(r"\s+","",page.markdown).encode()).hexdigest()if page.markdown else"";tk=re.sub(r"\W+","",title).lower();dup=""
 if h and h in seen_hash:dup="content_hash_duplicate"
 elif tk and any(SequenceMatcher(None,tk,z).ratio()>.97 for z in seen_titles):dup="title_similarity_duplicate"
 if dup:passed=False;internal+=1
 elif passed:h and seen_hash.add(h);tk and seen_titles.append(tk)
 sf=""
 if page.markdown:cp=EXTD/f"{r['id']}.md";cp.write_text(page.markdown,encoding="utf-8");sf=f"extracted/canonical/{r['id']}.md"
 row.update(title=title,quality_class=cls,quality_gate_pass=passed,diagnostic_reason=dup or q.reason,extraction_method=page.extraction_method,selector_used=page.selector_used,content_hash=h,source_file=sf,cleaned_length=len(page.plain_text),template_removed=bool(page.template_removed));qrows.append(row)
(OUT/"crawl/canonical_fetch_log.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in got),encoding="utf-8")
(OUT/"quality_gate/canonical_quality_gate_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in qrows),encoding="utf-8");eligible=[x for x in qrows if x.get("quality_gate_pass")];(OUT/"quality_gate/canonical_audit_candidates.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in eligible),encoding="utf-8")
s={"round_discovery_rows":len(allr),"unique_discovered_urls":len(disc),"historical_url_dedup":hist_url_dupe,"historical_title_similarity_dedup":hist_title_dupe,"canonical_selected":len(selected),"fetch_ok":sum(x["ok"]for x in got),"quality_gate_pass":len(eligible),"quality_classes":dict(Counter(x.get("quality_class")for x in qrows)),"internal_dedup":internal,"by_category":dict(Counter(x["discovery_category"]for x in eligible)),"by_domain":dict(Counter(x["domain"]for x in eligible))}
(OUT/"crawl/canonical_summary.json").write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(s,ensure_ascii=False))
