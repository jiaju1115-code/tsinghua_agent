from __future__ import annotations
import csv, hashlib, json, re, subprocess, sys, threading, time
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter,defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from bs4 import BeautifulSoup, UnicodeDammit

ROOT=Path(r"D:\python_projects\tsinghua_ai"); OUT=ROOT/"data_second/public_expansion_v2"
sys.path.insert(0,str(ROOT/"data_first")); from crawler.parser import detect_page,parse_html
for p in [OUT/"crawl",OUT/"raw",OUT/"extracted",OUT/"quality_gate"]:p.mkdir(parents=True,exist_ok=True)
TRACK={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","spm","from"}
SEEDS=[
("教务与学籍","https://www.tsinghua.edu.cn/jwc/index.htm"),("教务与学籍","https://learning.tsinghua.edu.cn/xwgg/tzgg.htm"),("教务与学籍","https://www.tsinghua.edu.cn/info/1092/1115.htm"),("教学与培养","https://www.tsinghua.edu.cn/yjsy/"),
("学生事务","https://www.tsinghua.edu.cn/xsb/"),("学生事务","https://www.tsinghua.edu.cn/xsb/lxwm.htm"),("学生事务","https://student.tsinghua.edu.cn/navigate"),("学生事务","https://dag.tsinghua.edu.cn/ywzn/xszd.htm"),
("住宿服务","https://www.tsinghua.edu.cn/xssqglfwzx/"),("住宿服务","https://www.is.tsinghua.edu.cn/"),
("餐饮服务","https://www.tsinghua.edu.cn/ysfwzx/"),("交通服务","https://www.tsinghua.edu.cn/zjqh/syxx/xyjt.htm"),("交通服务","https://www.tsinghua.edu.cn/jdfwzx/jdfw/cl.htm"),("交通服务","https://peace.tsinghua.edu.cn/"),
("医疗健康","https://www.med.tsinghua.edu.cn/info/1407/4477.htm"),("医疗健康","https://www.med.tsinghua.edu.cn/"),
("体育与场馆","https://www.thsports.tsinghua.edu.cn/"),("体育与场馆","https://www.thsports.tsinghua.edu.cn/info/1001/1782.htm"),("体育与场馆","https://www.sports.tsinghua.edu.cn/venue"),
("奖助与资助","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xsjxj_zxj_xfjm_zxdk.htm"),("奖助与资助","https://www.tsinghua.edu.cn/info/1093/102837.htm"),("奖助与资助","https://www.tsinghua.edu.cn/info/1093/82882.htm"),("奖助与资助","https://www.tsinghua.edu.cn/info/1093/82884.htm"),("奖助与资助","https://www.tsinghua.edu.cn/yjsy/zztx.htm"),
("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/vp/VisaProcedures.htm"),("国际事务与签证","https://www.is.tsinghua.edu.cn/"),
("就业与职业发展","https://career.tsinghua.edu.cn/"),("就业与职业发展","https://career.cic.tsinghua.edu.cn/xsglxt/f/jyxt/anony/izpxxPage"),
("校园访问","https://www.tsinghua.edu.cn/zjqh/xyfg/xycg.htm"),("校园综合服务","https://student.tsinghua.edu.cn/navigate"),("校园机构与部门","https://www.tsinghua.edu.cn/xxgk/zzjg.htm"),
]
KW={
"教务与学籍":r"学籍|选课|考试|成绩|注册|休学|复学|转专业|毕业|学位|课程|教务|培养方案|辅修|重修|缓考|证明",
"学生事务":r"学生事务|档案|户籍|身份证|政审|离校|迎新|校园卡|学生服务|纪律处分|申诉|证明|转档",
"住宿服务":r"宿舍|公寓|住宿|社区|入住|退宿|调宿|公共空间|楼宇|物业",
"餐饮服务":r"食堂|餐饮|饮食|餐厅|供餐|食品安全|清真|就餐",
"交通服务":r"校车|交通|停车|车证|车辆|通行|校门|入校|班车|自行车|电动车",
"医疗健康":r"校医院|医院|挂号|就诊|体检|医保|医疗|门诊|急诊|健康|心理|疫苗|报销",
"体育与场馆":r"体育馆|游泳馆|场馆|体育设施|预约|操场|健身|冰雪|气膜馆|西湖游泳池",
"奖助与资助":r"奖学金|助学金|资助|勤工助学|助学贷款|困难补助|学费减免|奖助|补偿代偿",
"国际事务与签证":r"国际学生|签证|居留许可|出入境|交换|港澳台|外事|留学|境外|国际交流",
"就业与职业发展":r"就业|职业发展|招聘|实习|生涯|毕业生|档案转递|就业手续|三方协议|派遣|签约",
"校园访问":r"校园参观|预约参观|入校参观|访客|校门|开放日",
"校园综合服务":r"服务大厅|综合服务|应用导航|快递|邮寄|购物|一卡通|报修|失物招领",
"教学与培养":r"教学|培养|课程|学习发展|教室|实验教学|辅修|通识",
"校园机构与部门":r"部门职责|机构设置|组织机构|中心简介|职能|联系我们"}
NEWS=re.compile(r"获奖|喜报|调研|出席|举行|举办|论坛|讲座|座谈|访问|签约|合作|活动回顾|党日|年会|新闻",re.I)
DETAIL=re.compile(r"/info/\d+/\d+\.s?html?$|/\d{3,}/\d+\.s?html?$|/content/|/article/|/detail/",re.I)
LOCK=defaultdict(threading.Lock); LAST=defaultdict(float)
def norm(u,b=""):
 try:
  p=urlsplit(urljoin(b,u.strip())); host=(p.hostname or "").lower()
  if p.scheme not in {"http","https"} or not host or not (host=="tsinghua.edu.cn" or host.endswith(".tsinghua.edu.cn")):return ""
  q=urlencode(sorted((k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in TRACK))
  return urlunsplit((p.scheme.lower(),host,re.sub(r"/{2,}","/",p.path or "/"),q,""))
 except:return ""
def fetch(url,path):
 host=urlsplit(url).hostname or ""
 with LOCK[host]:
  d=.25-(time.monotonic()-LAST[host]); time.sleep(max(0,d)); LAST[host]=time.monotonic()
 cmd=["curl.exe","-k","-L","--http1.1","--compressed","--connect-timeout","12","--max-time","45","--retry","1","-A","Mozilla/5.0 (compatible; TsinghuaKnowledgeBot/2.0)","-o",str(path),"-sS","-w","%{http_code}\t%{url_effective}\t%{content_type}",url]
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=60); z=p.stdout.strip().split("\t"); st=int(z[0]) if z and z[0].isdigit() else 0
  return {"ok":p.returncode==0 and 200<=st<400 and path.exists() and path.stat().st_size>200,"http_status":st,"final_url":z[1] if len(z)>1 else url,"content_type":z[2] if len(z)>2 else "","bytes":path.stat().st_size if path.exists() else 0,"error":p.stderr[:500]}
 except Exception as e:return {"ok":False,"http_status":0,"final_url":url,"content_type":"","bytes":0,"error":str(e)}
def decode(b):return UnicodeDammit(b,is_html=True).unicode_markup or b.decode("utf-8",errors="replace")
def history():
 urls=set(); titles=[]; hashes=set()
 for base in [ROOT/"data_first",ROOT/"data_second"]:
  for p in base.rglob("*"):
   if not p.is_file() or OUT in p.parents or p.stat().st_size>8_000_000:continue
   try:
    if p.suffix==".jsonl":
     for line in p.open(encoding="utf-8",errors="ignore"):
      try:r=json.loads(line)
      except:continue
      for k in ("url","source_url","final_url","normalized_url"):
       u=norm(str(r.get(k,""))); u and urls.add(u)
      t=str(r.get("title","")); t and titles.append(re.sub(r"\W+","",t).lower())
      h=r.get("content_hash"); h and hashes.add(h)
    elif p.suffix==".csv":
     for r in csv.DictReader(p.open(encoding="utf-8-sig",errors="ignore")):
      u=norm(r.get("url","") or r.get("source_url","") or ""); u and urls.add(u)
   except:pass
 return urls,titles,hashes

hist_urls,hist_titles,hist_hashes=history(); seedlog=[]; discovered={}
for i,(cat,url) in enumerate(SEEDS,1):
 p=OUT/"raw"/f"SEED{i:03d}.html"; meta=fetch(url,p); seedlog.append({"seed_id":f"SEED{i:03d}","category":cat,"url":url,**meta})
 if not meta["ok"]:continue
 html=decode(p.read_bytes()); soup=BeautifulSoup(html,"lxml"); host=urlsplit(meta["final_url"]).hostname
 # seed detail itself
 u=norm(meta["final_url"]); discovered.setdefault(u,{"url":u,"title":soup.title.get_text(" ",strip=True) if soup.title else u,"discovery_category":cat,"discovery_source":"confirmed_official_seed","parent_list_url":""})
 for a in soup.find_all("a",href=True):
  t=re.sub(r"\s+"," ",a.get_text(" ",strip=True)).strip(); v=norm(a["href"],meta["final_url"])
  if not v or (urlsplit(v).hostname or "")!=host or not t or v.lower().endswith((".pdf",".doc",".docx",".xls",".xlsx",".zip")):continue
  if not re.search(KW[cat],t,re.I):continue
  if NEWS.search(t) and not re.search(r"通知|规定|办法|指南|服务|手续|流程|安排|政策",t):continue
  if not DETAIL.search(v) and not re.search(r"\.s?html?$",urlsplit(v).path,re.I):continue
  discovered.setdefault(v,{"url":v,"title":t[:300],"discovery_category":cat,"discovery_source":"seed_page_targeted_link","parent_list_url":meta["final_url"]})
(OUT/"crawl/seed_fetch_log.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in seedlog),encoding="utf-8")
dupe_hist=0; selected=[]
for u,x in discovered.items():
 if u in hist_urls:dupe_hist+=1;continue
 tk=re.sub(r"\W+","",x["title"]).lower()
 if tk and any(SequenceMatcher(None,tk,h).ratio()>.96 for h in hist_titles[-1500:]):dupe_hist+=1;continue
 selected.append(x)
selected.sort(key=lambda x:(x["discovery_category"],x["url"])); selected=selected[:650]
for i,x in enumerate(selected,1):x["id"]=f"PUBV2-{i:04d}"
(OUT/"crawl/discovered_urls.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in selected),encoding="utf-8")

fetched=[]
with ThreadPoolExecutor(max_workers=4) as ex:
 fut={ex.submit(fetch,x["url"],OUT/"raw"/f"{x['id']}.html"):x for x in selected}
 for j,f in enumerate(as_completed(fut),1):
  x=fut[f]; fetched.append({**x,**f.result(),"crawl_timestamp":datetime.now().isoformat(timespec="seconds")})
  if j%50==0:print(f"fetch {j}/{len(selected)}",flush=True)
fetched.sort(key=lambda x:x["id"]); (OUT/"crawl/fetch_log.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in fetched),encoding="utf-8")

qrows=[]; seen_hash=set(hist_hashes); seen_titles=[]; internal_dupe=0
for x in fetched:
 row={**x,"normalized_url":norm(x.get("final_url") or x["url"]),"domain":urlsplit(x.get("final_url") or x["url"]).hostname or ""}
 if not x["ok"]:row.update(quality_class="content_missing",quality_gate_pass=False,diagnostic_reason=x["error"],extraction_method="request_failed",selector_used="",content_hash="",source_file="");qrows.append(row);continue
 html=decode((OUT/"raw"/f"{x['id']}.html").read_bytes()); kind=detect_page(html,row["normalized_url"])
 if kind:row.update(quality_class=kind,quality_gate_pass=False,diagnostic_reason=kind,extraction_method=kind,selector_used="",content_hash="",source_file="");qrows.append(row);continue
 page=parse_html(html,row["normalized_url"],TRACK); q=page.quality; cls=q.content_quality_class; passed=bool(q.passed and cls in {"detail_content","thin_content","template_polluted"})
 h=hashlib.sha256(re.sub(r"\s+","",page.plain_text).encode()).hexdigest() if page.plain_text else ""; tk=re.sub(r"\W+","",x["title"]).lower(); dup=""
 if h and h in seen_hash:dup="content_hash_duplicate"
 elif tk and any(SequenceMatcher(None,tk,z).ratio()>.97 for z in seen_titles):dup="title_similarity_duplicate"
 if dup:passed=False;internal_dupe+=1
 elif passed:
  h and seen_hash.add(h); tk and seen_titles.append(tk)
 sf=""
 if page.markdown:
  cp=OUT/"extracted"/f"{x['id']}.md"; cp.write_text(page.markdown,encoding="utf-8");sf=str(cp.relative_to(OUT)).replace("\\","/")
 row.update(quality_class=cls,quality_gate_pass=passed,diagnostic_reason=dup or q.reason,extraction_method=page.extraction_method,selector_used=page.selector_used,content_hash=h,source_file=sf,cleaned_length=len(page.plain_text),template_removed=bool(page.template_removed))
 qrows.append(row)
(OUT/"quality_gate/quality_gate_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in qrows),encoding="utf-8")
eligible=[x for x in qrows if x.get("quality_gate_pass")]
(OUT/"quality_gate/audit_candidates.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in eligible),encoding="utf-8")
summary={"seed_count":len(SEEDS),"seed_fetch_ok":sum(x["ok"] for x in seedlog),"discovered_unique_before_history":len(discovered),"historical_dedup":dupe_hist,"selected_urls":len(selected),"fetch_ok":sum(x["ok"] for x in fetched),"quality_gate_pass":len(eligible),"quality_classes":dict(Counter(x.get("quality_class") for x in qrows)),"internal_dedup":internal_dupe,"by_category":dict(Counter(x["discovery_category"] for x in eligible)),"by_domain":dict(Counter(x["domain"] for x in eligible))}
(OUT/"crawl/crawl_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(summary,ensure_ascii=False))
