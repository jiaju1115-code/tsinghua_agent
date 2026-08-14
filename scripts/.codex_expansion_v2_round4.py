from __future__ import annotations
import hashlib,json,re,subprocess,sys,threading,time
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter,defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from bs4 import BeautifulSoup,UnicodeDammit
ROOT=Path(r"D:\python_projects\tsinghua_ai");OUT=ROOT/"data_second/public_expansion_v2"
sys.path.insert(0,str(ROOT/"data_first"));from crawler.parser import detect_page,parse_html
TRACK={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","spm","from"}
LISTS=[]
for host in ["qzc.tsinghua.edu.cn","www.wyc.tsinghua.edu.cn","www.twc.tsinghua.edu.cn","www.zlc.tsinghua.edu.cn","www.rxc.tsinghua.edu.cn","www.xyc.tsinghua.edu.cn","www.tanweicollege.tsinghua.edu.cn","www.jxc.tsinghua.edu.cn"]:
 for path in ["syfw/bszn.htm","syfw/gzzd.htm","syfw/bgxz.htm"]:LISTS.append(("教务与学籍",f"https://{host}/{path}"))
LISTS += [
 ("国际事务与签证","https://goglobal.tsinghua.edu.cn/tutorial"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/vp/VT.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/vp/VisaProcedures.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/vp/PassportMatters.htm"),
 ("住宿服务","https://www.is.tsinghua.edu.cn/asdfasdf/Accommodationq/On_campus_Living_Frequently_Asked_Questions.htm"),
 ("住宿服务","https://www.is.tsinghua.edu.cn/asdfasdf/Accommodationq/Off_campus_accommodation.htm"),
 ("住宿服务","https://www.is.tsinghua.edu.cn/asdfasdf/Accommodationq/Hotel_accommodation_near_campus.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/sdfgsadf/Social_Insurance.htm"),
 ("交通服务","https://www.is.tsinghua.edu.cn/Campus1/Campus_Bus/A_guide_to_school_shuttle_bus.htm"),
 ("国际事务与签证","https://www.is.tsinghua.edu.cn/info/1217/1426.htm"),
 ("就业与职业发展","https://www.is.tsinghua.edu.cn/asdfasdf/Internships_and_Employment/Policies.htm"),
 ("就业与职业发展","https://www.is.tsinghua.edu.cn/asdfasdf/Internships_and_Employment/Employment_Information.htm"),
 ("就业与职业发展","https://www.is.tsinghua.edu.cn/asdfasdf/Internships_and_Employment/Internship_Information.htm"),
 ("交通服务","https://peace.tsinghua.edu.cn/xyjt/lfclyy.htm"),
 ("交通服务","https://peace.tsinghua.edu.cn/xyjt/xnyytc.htm"),
 ("校园访问","https://peace.tsinghua.edu.cn/xycg.htm"),
 ("科研参与与资源导航","https://ac.tsinghua.edu.cn/fwzn.htm"),
 ("科研参与与资源导航","https://ac.tsinghua.edu.cn/fwzn/gzzd.htm"),
 ("科研参与与资源导航","https://ac.tsinghua.edu.cn/fwzn/cjwt.htm"),
 ("教学与培养","https://www.thsports.tsinghua.edu.cn/jyjx/kcszyss.htm"),
 ("体育与场馆","https://www.thsports.tsinghua.edu.cn/tyss.htm"),
 ("医疗健康","https://www.med.tsinghua.edu.cn/tlff/bj.htm"),
]
ALLOW=r"指南|服务|规章|规定|制度|办法|流程|申请|办理|手册|课程|选课|退课|学籍|成绩|毕业|学位|证明|学生|奖学金|助学|住宿|公寓|就业|职业|实习|签证|护照|居留|保险|交通|停车|车辆|校门|参观|场馆|体育|游泳|医疗|挂号|体检|仪器|预约|收费|测试|guide|service|visa|passport|residence|accommodation|insurance|internship|employment|policy|FAQ"
LOCK=defaultdict(threading.Lock);LAST=defaultdict(float)
def norm(u,b=""):
 try:
  p=urlsplit(urljoin(b,u.strip()));h=(p.hostname or "").lower()
  if p.scheme not in{"http","https"}or not(h=="tsinghua.edu.cn"or h.endswith(".tsinghua.edu.cn")):return""
  q=urlencode(sorted((k,v)for k,v in parse_qsl(p.query,keep_blank_values=True)if k.lower()not in TRACK));return urlunsplit((p.scheme.lower(),h,re.sub(r"/{2,}","/",p.path or"/"),q,""))
 except:return""
def fetch(u,p):
 h=urlsplit(u).hostname or""
 with LOCK[h]:d=.25-(time.monotonic()-LAST[h]);time.sleep(max(0,d));LAST[h]=time.monotonic()
 try:
  z=subprocess.run(["curl.exe","-k","-L","--http1.1","--compressed","--connect-timeout","10","--max-time","35","--retry","1","-A","Mozilla/5.0 (compatible; TsinghuaKnowledgeBot/2.0)","-o",str(p),"-sS","-w","%{http_code}\t%{url_effective}\t%{content_type}",u],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=50);a=z.stdout.strip().split("\t");st=int(a[0])if a and a[0].isdigit()else 0
  return{"ok":z.returncode==0 and 200<=st<400 and p.exists()and p.stat().st_size>200,"http_status":st,"final_url":a[1]if len(a)>1else u,"content_type":a[2]if len(a)>2else"","bytes":p.stat().st_size if p.exists()else 0,"error":z.stderr[:300]}
 except Exception as e:return{"ok":False,"http_status":0,"final_url":u,"content_type":"","bytes":0,"error":str(e)}
def dec(b):return UnicodeDammit(b,is_html=True).unicode_markup or b.decode(errors="replace")
existing=[]
for p in OUT.glob("quality_gate/*quality_gate_results.jsonl"):existing +=[json.loads(x)for x in p.read_text(encoding="utf-8").splitlines()if x.strip()]
seen_urls={norm(x.get("normalized_url")or x.get("url",""))for x in existing};seen_hash={x.get("content_hash")for x in existing if x.get("content_hash")};seen_titles=[re.sub(r"\W+","",x.get("title","")).lower()for x in existing if x.get("title")]
log=[];disc={}
for i,(cat,u)in enumerate(LISTS,1):
 p=OUT/"raw"/f"R4LIST{i:03d}.html";m=fetch(u,p);log.append({"list_id":f"R4LIST{i:03d}","category":cat,"url":u,**m})
 if not m["ok"]:continue
 s=BeautifulSoup(dec(p.read_bytes()),"lxml");v=norm(m["final_url"]);title=s.title.get_text(" ",strip=True)if s.title else v
 if v and v not in seen_urls:disc.setdefault(v,{"url":v,"title":title[:300],"discovery_category":cat,"discovery_source":"round4_confirmed_official_landing","parent_list_url":""})
 for a in s.find_all("a",href=True):
  t=re.sub(r"\s+"," ",a.get_text(" ",strip=True)).strip();v=norm(a["href"],m["final_url"])
  if not v or not t or v in seen_urls or v==norm(m["final_url"])or v.lower().endswith((".pdf",".doc",".docx",".xls",".xlsx",".zip",".jpg",".png")):continue
  if(urlsplit(v).hostname or"")!=(urlsplit(m["final_url"]).hostname or"")or not re.search(ALLOW,t,re.I):continue
  if not re.search(r"/info/\d+/\d+\.s?html?$|/\d{3,}/\d+\.s?html?$|\.s?html?$|/tutorial/[A-Za-z0-9]+$",urlsplit(v).path,re.I):continue
  disc.setdefault(v,{"url":v,"title":t[:300],"discovery_category":cat,"discovery_source":"round4_targeted_list_one_level_follow","parent_list_url":m["final_url"]})
(OUT/"crawl/round4_list_log.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in log),encoding="utf-8")
sel=[];td=0
for v,x in disc.items():
 tk=re.sub(r"\W+","",x["title"]).lower()
 if tk and any(SequenceMatcher(None,tk,z).ratio()>.97 for z in seen_titles):td+=1;continue
 sel.append(x)
sel=sorted(sel,key=lambda x:(x["discovery_category"],x["url"]))[:600];mx=max([int(re.search(r"(\d+)",x.get("id","")).group(1))for x in existing if re.search(r"(\d+)",x.get("id",""))]or[230])
for i,x in enumerate(sel,mx+1):x["id"]=f"PUBV2-{i:04d}"
(OUT/"crawl/round4_discovered_urls.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in sel),encoding="utf-8")
got=[]
with ThreadPoolExecutor(max_workers=4)as ex:
 fut={ex.submit(fetch,x["url"],OUT/"raw"/f"{x['id']}.html"):x for x in sel}
 for j,f in enumerate(as_completed(fut),1):got.append({**fut[f],**f.result(),"crawl_timestamp":datetime.now().isoformat(timespec="seconds")});print(f"round4 fetch {j}/{len(sel)}",flush=True)if j%50==0 else None
got.sort(key=lambda x:x["id"]);qrows=[];internal=0
for x in got:
 row={**x,"normalized_url":norm(x.get("final_url")or x["url"]),"domain":urlsplit(x.get("final_url")or x["url"]).hostname or""}
 if not x["ok"]:row.update(quality_class="content_missing",quality_gate_pass=False,diagnostic_reason=x["error"],extraction_method="request_failed",selector_used="",content_hash="",source_file="");qrows.append(row);continue
 html=dec((OUT/"raw"/f"{x['id']}.html").read_bytes());kind=detect_page(html,row["normalized_url"])
 if kind:row.update(quality_class=kind,quality_gate_pass=False,diagnostic_reason=kind,extraction_method=kind,selector_used="",content_hash="",source_file="");qrows.append(row);continue
 page=parse_html(html,row["normalized_url"],TRACK);q=page.quality;cls=q.content_quality_class;passed=bool(q.passed and cls in{"detail_content","thin_content","template_polluted"});h=hashlib.sha256(re.sub(r"\s+","",page.plain_text).encode()).hexdigest()if page.plain_text else"";tk=re.sub(r"\W+","",x["title"]).lower();dup=""
 if h and h in seen_hash:dup="content_hash_duplicate"
 elif tk and any(SequenceMatcher(None,tk,z).ratio()>.97 for z in seen_titles):dup="title_similarity_duplicate"
 if dup:passed=False;internal+=1
 elif passed:h and seen_hash.add(h);tk and seen_titles.append(tk)
 sf=""
 if page.markdown:cp=OUT/"extracted"/f"{x['id']}.md";cp.write_text(page.markdown,encoding="utf-8");sf=str(cp.relative_to(OUT)).replace("\\","/")
 row.update(quality_class=cls,quality_gate_pass=passed,diagnostic_reason=dup or q.reason,extraction_method=page.extraction_method,selector_used=page.selector_used,content_hash=h,source_file=sf,cleaned_length=len(page.plain_text),template_removed=bool(page.template_removed));qrows.append(row)
(OUT/"quality_gate/round4_quality_gate_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in qrows),encoding="utf-8");eligible=[x for x in qrows if x.get("quality_gate_pass")];(OUT/"quality_gate/round4_audit_candidates.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in eligible),encoding="utf-8")
s={"list_pages_requested":len(LISTS),"list_pages_ok":sum(x["ok"]for x in log),"discovered":len(sel),"title_dedup":td,"fetch_ok":sum(x["ok"]for x in got),"quality_gate_pass":len(eligible),"quality_classes":dict(Counter(x.get("quality_class")for x in qrows)),"internal_dedup":internal,"by_category":dict(Counter(x["discovery_category"]for x in eligible)),"by_domain":dict(Counter(x["domain"]for x in eligible))};(OUT/"crawl/round4_summary.json").write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(s,ensure_ascii=False))
