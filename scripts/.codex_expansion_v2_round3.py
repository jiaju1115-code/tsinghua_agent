from __future__ import annotations
import csv, hashlib, json, re, subprocess, sys, threading, time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from bs4 import BeautifulSoup, UnicodeDammit

ROOT=Path(r"D:\python_projects\tsinghua_ai"); OUT=ROOT/"data_second/public_expansion_v2"
sys.path.insert(0,str(ROOT/"data_first")); from crawler.parser import detect_page,parse_html
TRACK={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","spm","from"}
LISTS=[
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/vp.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/Accommodationq.htm"),
 ("奖助与资助","https://www.is.tsinghua.edu.cn/asdfasdf/Scholarships.htm"),
 ("就业与职业发展","https://www.is.tsinghua.edu.cn/asdfasdf/Internships_and_Employment.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/Forms___Guides.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/Forms___Guides/Guides.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/sdfgsadf/VRP.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/sdfgsadf/Accommodation.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/Guides.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/FAQ.htm"),
 ("交通服务","https://peace.tsinghua.edu.cn/bszn/xyjt.htm"),
 ("校园访问","https://peace.tsinghua.edu.cn/bszn/xycg.htm"),
 ("交通服务","https://peace.tsinghua.edu.cn/zcfg/zcwj.htm"),
 ("学生事务","https://peace.tsinghua.edu.cn/zcfg/xxgzzd.htm"),
 ("学生事务","https://peace.tsinghua.edu.cn/bszn/hzsw.htm"),
 ("体育与场馆","https://www.thsports.tsinghua.edu.cn/tyss.htm"),
 ("体育与场馆","https://www.thsports.tsinghua.edu.cn/jyjx/kcszyss.htm"),
 ("就业与职业发展","https://career.tsinghua.edu.cn/"),
 ("就业与职业发展","https://career.tsinghua.edu.cn/xs/zyfd.htm"),
 ("就业与职业发展","https://career.tsinghua.edu.cn/xy/zyfz.htm"),
 ("教务与学籍","https://www.tsinghua.edu.cn/jwc/dfasdf/ywbl.htm"),
 ("教务与学籍","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xjglbff.htm"),
 ("学生事务","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xsssbff.htm"),
 ("学生事务","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xsstglbff.htm"),
 ("教务与学籍","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xfjss/kswgxwdclbff.htm"),
 ("教学与培养","https://www.tsinghua.edu.cn/yjsy/bszn.htm"),
 ("教学与培养","https://www.tsinghua.edu.cn/yjsy/yjspy/pyyqygd.htm"),
 ("教学与培养","https://www.tsinghua.edu.cn/yjsy/yjspy/jjzzyjl.htm"),
 ("校园综合服务","https://www.wyc.tsinghua.edu.cn/syfw/bszn.htm"),
 ("教务与学籍","https://qzc.tsinghua.edu.cn/syfw/bszn.htm"),
]
ALLOW={
"国际事务与签证":r"visa|passport|residence|permit|accommodation|insurance|international|exchange|guide|FAQ|签证|护照|居留|国际学生|住宿|保险|指南|交换",
"奖助与资助":r"scholarship|financial|fund|奖学金|助学|资助|奖助|贷款|困难|勤工",
"就业与职业发展":r"internship|employment|career|policy|就业|职业|生涯|实习|手续|档案|课程|咨询|教练|毕业生",
"交通服务":r"交通|停车|车辆|车证|电动自行车|通行|校门|预约|班车|shuttle|bus",
"校园访问":r"参观|预约|访客|入校|团队|个人|visit",
"学生事务":r"学生|管理规定|纪律|处分|申诉|社团|户政|户籍|身份证|政审|档案|证明|办法",
"体育与场馆":r"体育|场馆|游泳|健身|设施|课程|协会|预约|馆|场",
"教务与学籍":r"学籍|选课|退课|课程|考试|成绩|毕业|学位|档案|证明|转专业|休学|复学|培养|本科生",
"教学与培养":r"研究生|培养|学位|课程|教学|证明|毕业|档案|基金|资助|奖励|项目|规定|指南",
"校园综合服务":r"指南|服务|活动室|学生|校园卡|报销|证明|办事|使用手册",
}
LOCK=defaultdict(threading.Lock); LAST=defaultdict(float)
def norm(u,b=""):
 try:
  p=urlsplit(urljoin(b,u.strip())); h=(p.hostname or "").lower()
  if p.scheme not in {"http","https"} or not h or not(h=="tsinghua.edu.cn" or h.endswith(".tsinghua.edu.cn")):return ""
  q=urlencode(sorted((k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in TRACK))
  return urlunsplit((p.scheme.lower(),h,re.sub(r"/{2,}","/",p.path or "/"),q,""))
 except:return ""
def fetch(u,p):
 host=urlsplit(u).hostname or ""
 with LOCK[host]:
  d=.25-(time.monotonic()-LAST[host]); time.sleep(max(0,d)); LAST[host]=time.monotonic()
 try:
  z=subprocess.run(["curl.exe","-k","-L","--http1.1","--compressed","--connect-timeout","10","--max-time","35","--retry","1","-A","Mozilla/5.0 (compatible; TsinghuaKnowledgeBot/2.0)","-o",str(p),"-sS","-w","%{http_code}\t%{url_effective}\t%{content_type}",u],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=50)
  a=z.stdout.strip().split("\t"); st=int(a[0]) if a and a[0].isdigit() else 0
  return {"ok":z.returncode==0 and 200<=st<400 and p.exists() and p.stat().st_size>200,"http_status":st,"final_url":a[1] if len(a)>1 else u,"content_type":a[2] if len(a)>2 else "","bytes":p.stat().st_size if p.exists() else 0,"error":z.stderr[:300]}
 except Exception as e:return {"ok":False,"http_status":0,"final_url":u,"content_type":"","bytes":0,"error":str(e)}
def dec(b):return UnicodeDammit(b,is_html=True).unicode_markup or b.decode("utf-8",errors="replace")

existing=[]
for p in OUT.glob("quality_gate/*quality_gate_results.jsonl"):
 existing += [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
seen_urls={norm(x.get("normalized_url") or x.get("url", "")) for x in existing}; seen_hash={x.get("content_hash") for x in existing if x.get("content_hash")}; seen_titles=[re.sub(r"\W+","",x.get("title","")).lower() for x in existing if x.get("title")]
listlog=[]; disc={}
for i,(cat,u) in enumerate(LISTS,1):
 p=OUT/"raw"/f"R3LIST{i:03d}.html"; m=fetch(u,p); listlog.append({"list_id":f"R3LIST{i:03d}","category":cat,"url":u,**m})
 if not m["ok"]:continue
 s=BeautifulSoup(dec(p.read_bytes()),"lxml")
 # Include a high-value landing page itself as a candidate; Prompt can reject it later.
 v=norm(m["final_url"]); title=s.title.get_text(" ",strip=True) if s.title else v
 if v and v not in seen_urls:disc.setdefault(v,{"url":v,"title":title[:300],"discovery_category":cat,"discovery_source":"confirmed_official_category_landing","parent_list_url":""})
 for a in s.find_all("a",href=True):
  t=re.sub(r"\s+"," ",a.get_text(" ",strip=True)).strip(); v=norm(a["href"],m["final_url"])
  if not v or not t or v in seen_urls or v==norm(m["final_url"]):continue
  if (urlsplit(v).hostname or "")!=(urlsplit(m["final_url"]).hostname or ""):continue
  if v.lower().endswith((".pdf",".doc",".docx",".xls",".xlsx",".zip",".jpg",".png")):continue
  if not re.search(ALLOW[cat],t,re.I):continue
  path=urlsplit(v).path
  if not(re.search(r"/info/\d+/\d+\.s?html?$|/\d{3,}/\d+\.s?html?$|\.s?html?$",path,re.I)):continue
  disc.setdefault(v,{"url":v,"title":t[:300],"discovery_category":cat,"discovery_source":"round3_targeted_list_one_level_follow","parent_list_url":m["final_url"]})
(OUT/"crawl/round3_list_log.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in listlog),encoding="utf-8")
sel=[]; title_dupe=0
for v,x in disc.items():
 tk=re.sub(r"\W+","",x["title"]).lower()
 if tk and any(SequenceMatcher(None,tk,z).ratio()>.97 for z in seen_titles):title_dupe+=1;continue
 sel.append(x)
sel=sorted(sel,key=lambda x:(x["discovery_category"],x["url"]))[:600]
max_id=max([int(re.search(r"(\d+)",x.get("id","")).group(1)) for x in existing if re.search(r"(\d+)",x.get("id",""))] or [125])
for i,x in enumerate(sel,max_id+1):x["id"]=f"PUBV2-{i:04d}"
(OUT/"crawl/round3_discovered_urls.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in sel),encoding="utf-8")
got=[]
with ThreadPoolExecutor(max_workers=4) as ex:
 fut={ex.submit(fetch,x["url"],OUT/"raw"/f"{x['id']}.html"):x for x in sel}
 for j,f in enumerate(as_completed(fut),1):
  got.append({**fut[f],**f.result(),"crawl_timestamp":datetime.now().isoformat(timespec="seconds")})
  if j%50==0:print(f"round3 fetch {j}/{len(sel)}",flush=True)
got.sort(key=lambda x:x["id"]); qrows=[]; internal=0
for x in got:
 row={**x,"normalized_url":norm(x.get("final_url") or x["url"]),"domain":urlsplit(x.get("final_url") or x["url"]).hostname or ""}
 if not x["ok"]:row.update(quality_class="content_missing",quality_gate_pass=False,diagnostic_reason=x["error"],extraction_method="request_failed",selector_used="",content_hash="",source_file="");qrows.append(row);continue
 html=dec((OUT/"raw"/f"{x['id']}.html").read_bytes()); kind=detect_page(html,row["normalized_url"])
 if kind:row.update(quality_class=kind,quality_gate_pass=False,diagnostic_reason=kind,extraction_method=kind,selector_used="",content_hash="",source_file="");qrows.append(row);continue
 page=parse_html(html,row["normalized_url"],TRACK); q=page.quality; cls=q.content_quality_class; passed=bool(q.passed and cls in {"detail_content","thin_content","template_polluted"})
 h=hashlib.sha256(re.sub(r"\s+","",page.plain_text).encode()).hexdigest() if page.plain_text else ""; tk=re.sub(r"\W+","",x["title"]).lower(); dup=""
 if h and h in seen_hash:dup="content_hash_duplicate"
 elif tk and any(SequenceMatcher(None,tk,z).ratio()>.97 for z in seen_titles):dup="title_similarity_duplicate"
 if dup:passed=False;internal+=1
 elif passed:h and seen_hash.add(h); tk and seen_titles.append(tk)
 sf=""
 if page.markdown:
  cp=OUT/"extracted"/f"{x['id']}.md"; cp.write_text(page.markdown,encoding="utf-8"); sf=str(cp.relative_to(OUT)).replace("\\","/")
 row.update(quality_class=cls,quality_gate_pass=passed,diagnostic_reason=dup or q.reason,extraction_method=page.extraction_method,selector_used=page.selector_used,content_hash=h,source_file=sf,cleaned_length=len(page.plain_text),template_removed=bool(page.template_removed));qrows.append(row)
(OUT/"quality_gate/round3_quality_gate_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in qrows),encoding="utf-8")
eligible=[x for x in qrows if x.get("quality_gate_pass")]
(OUT/"quality_gate/round3_audit_candidates.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in eligible),encoding="utf-8")
s={"list_pages_requested":len(LISTS),"list_pages_ok":sum(x["ok"] for x in listlog),"discovered":len(sel),"title_dedup":title_dupe,"fetch_ok":sum(x["ok"] for x in got),"quality_gate_pass":len(eligible),"quality_classes":dict(Counter(x.get("quality_class") for x in qrows)),"internal_dedup":internal,"by_category":dict(Counter(x["discovery_category"] for x in eligible)),"by_domain":dict(Counter(x["domain"] for x in eligible))}
(OUT/"crawl/round3_summary.json").write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(s,ensure_ascii=False))
