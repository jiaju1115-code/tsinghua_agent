from __future__ import annotations
import json,re,subprocess,sys,time,hashlib
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter,defaultdict
from difflib import SequenceMatcher
from bs4 import BeautifulSoup,UnicodeDammit
ROOT=Path(r"D:\python_projects\tsinghua_ai");OUT=ROOT/"data_second/public_expansion_v2"
sys.path.insert(0,str(ROOT/"data_first"));from crawler.parser import detect_page,parse_html
TRACK={"utm_source","utm_medium","utm_campaign","utm_term","utm_content","spm","from"}
LISTS=[]
LISTS += [("教务与学籍",f"https://learning.tsinghua.edu.cn/xwgg/tzgg/{i}.htm") for i in range(1,38)] + [("教务与学籍","https://learning.tsinghua.edu.cn/xwgg/tzgg.htm")]
LISTS += [("就业与职业发展",f"https://career.tsinghua.edu.cn/js/tzgg/{i}.htm") for i in range(1,12)] + [("就业与职业发展","https://career.tsinghua.edu.cn/js/tzgg.htm"),("就业与职业发展","https://career.tsinghua.edu.cn/")]
LISTS += [("学生事务","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww.htm"),("学生事务","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xsjlcfbff.htm"),("教务与学籍","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xjglbff.htm")]
LISTS += [("奖助与资助","https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xsjxj_zxj_xfjm_zxdk.htm"),("教学与培养","https://www.tsinghua.edu.cn/yjsy/bszn.htm"),("教学与培养","https://www.tsinghua.edu.cn/yjsy/yjspy/pyyqygd.htm"),("教学与培养","https://www.tsinghua.edu.cn/yjsy/yjspy/kcyjx.htm")]
LISTS += [("国际事务与签证","https://www.is.tsinghua.edu.cn/asdfasdf/vp/VisaProcedures.htm"),("国际事务与签证","https://www.is.tsinghua.edu.cn/IS/Student_Services.htm"),("住宿服务","https://www.tsinghua.edu.cn/xssqglfwzx/fwzn.htm"),("餐饮服务","https://www.tsinghua.edu.cn/ysfwzx/stjs.htm")]
LISTS += [("体育与场馆","https://www.thsports.tsinghua.edu.cn/"),("交通服务","https://peace.tsinghua.edu.cn/bmfw.htm"),("校园访问","https://www.tsinghua.edu.cn/zjqh/xyfg/xycg.htm"),("校园综合服务","https://www.tsinghua.edu.cn/zjqh/syxx/fwxx.htm")]
ALLOW={
"教务与学籍":r"注册|选课|退课|课程|考试|成绩|毕业|离校|教室|自习|学籍|培养|辅修|学位|证明|转专业|休学|复学|教学",
"就业与职业发展":r"就业|职业|手续|档案|招聘安排|政策|流程|咨询|课程|指导|生涯|国际组织实习|港澳台|毕业生",
"学生事务":r"学生|纪律|处分|申诉|社团|学籍|档案|户籍|管理规定|办法|服务|证明|转档",
"奖助与资助":r"奖学金|助学金|资助|勤工|贷款|困难|学费|补偿|代偿|认定",
"教学与培养":r"培养|课程|教学|学位|研究生|博士|硕士|办事|指南|规定|要求|项目|证书",
"国际事务与签证":r"签证|居留|护照|国际学生|住宿登记|体检|保险|出入境|交换|服务|手续|指南",
"住宿服务":r"宿舍|住宿|公寓|调宿|邮寄|生活须知|服务指南|入住|退宿",
"餐饮服务":r"食堂|餐厅|饮食|餐饮|食品|供餐",
"体育与场馆":r"场馆|体育馆|游泳|健身|预约|联系我们|设施|开放",
"交通服务":r"交通|停车|车辆|车证|通行|校门|户籍|身份证|政审|服务",
"校园访问":r"参观|预约|访客|入校|校园开放|校门",
"校园综合服务":r"服务|一卡通|邮寄|快递|购物|报修|失物|交通|餐饮|住宿|医疗"}
BAD=re.compile(r"获奖|喜报|调研|出席|举行|举办|论坛|讲座|座谈|访问交流|签约|合作|活动回顾|党日|年会|新闻|招聘公告|实习招聘|宣讲会",re.I)
def norm(u,b=""):
 try:
  p=urlsplit(urljoin(b,u));h=(p.hostname or "").lower()
  if p.scheme not in {"http","https"} or not(h=="tsinghua.edu.cn" or h.endswith(".tsinghua.edu.cn")):return""
  q=urlencode(sorted((k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in TRACK));return urlunsplit((p.scheme,h,re.sub(r"/{2,}","/",p.path or"/"),q,""))
 except:return""
def fetch(u,p):
 try:
  z=subprocess.run(["curl.exe","-k","-L","--http1.1","--compressed","--connect-timeout","10","--max-time","35","--retry","1","-A","Mozilla/5.0 (compatible; TsinghuaKnowledgeBot/2.0)","-o",str(p),"-sS","-w","%{http_code}\t%{url_effective}\t%{content_type}",u],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=50);a=z.stdout.strip().split("\t");st=int(a[0]) if a and a[0].isdigit()else 0;return{"ok":z.returncode==0 and 200<=st<400 and p.exists()and p.stat().st_size>200,"http_status":st,"final_url":a[1]if len(a)>1else u,"content_type":a[2]if len(a)>2else"","error":z.stderr[:300]}
 except Exception as e:return{"ok":False,"http_status":0,"final_url":u,"content_type":"","error":str(e)}
def dec(b):return UnicodeDammit(b,is_html=True).unicode_markup or b.decode(errors="replace")
old=[]
for p in [OUT/"quality_gate/quality_gate_results.jsonl",OUT/"quality_gate/audit_candidates.jsonl"]:
 if p.exists():old += [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()if x.strip()]
seen_urls={norm(x.get("normalized_url")or x.get("url",''))for x in old};seen_hash={x.get("content_hash")for x in old if x.get("content_hash")};seen_titles=[re.sub(r"\W+","",x.get("title","")).lower()for x in old if x.get("title")]
listlog=[];disc={}
for i,(cat,u)in enumerate(LISTS,1):
 p=OUT/"raw"/f"LIST{i:03d}.html";m=fetch(u,p);listlog.append({"list_id":f"LIST{i:03d}","category":cat,"url":u,**m})
 if not m["ok"]:continue
 s=BeautifulSoup(dec(p.read_bytes()),"lxml")
 for a in s.find_all("a",href=True):
  t=re.sub(r"\s+"," ",a.get_text(" ",strip=True)).strip();v=norm(a["href"],m["final_url"])
  if not v or not t or v in seen_urls or v==norm(m["final_url"]):continue
  if (urlsplit(v).hostname or"")!=(urlsplit(m["final_url"]).hostname or""):continue
  if v.lower().endswith((".pdf",".doc",".docx",".xls",".xlsx",".zip")):continue
  if not re.search(ALLOW[cat],t,re.I) or (BAD.search(t)and not re.search(r"通知|规定|办法|指南|手续|政策|服务",t)):continue
  if not(re.search(r"/info/\d+/\d+\.s?html?$|/\d{3,}/\d+\.s?html?$|detail\.(jsp|htm)|xxid=",v,re.I)):continue
  disc.setdefault(v,{"url":v,"title":t[:300],"discovery_category":cat,"discovery_source":"targeted_list_one_level_follow","parent_list_url":m["final_url"]})
(OUT/"crawl/follow_list_log.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in listlog),encoding="utf-8")
sel=[]
for v,x in disc.items():
 tk=re.sub(r"\W+","",x["title"]).lower()
 if tk and any(SequenceMatcher(None,tk,z).ratio()>.97 for z in seen_titles):continue
 sel.append(x)
sel=sorted(sel,key=lambda x:(x["discovery_category"],x["url"]))[:600]
for i,x in enumerate(sel,106):x["id"]=f"PUBV2-{i:04d}"
(OUT/"crawl/follow_discovered_urls.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in sel),encoding="utf-8")
got=[]
with ThreadPoolExecutor(max_workers=4)as ex:
 fut={ex.submit(fetch,x["url"],OUT/"raw"/f"{x['id']}.html"):x for x in sel}
 for j,f in enumerate(as_completed(fut),1):
  got.append({**fut[f],**f.result()});
  if j%50==0:print(f"follow fetch {j}/{len(sel)}",flush=True)
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
 row.update(quality_class=cls,quality_gate_pass=passed,diagnostic_reason=dup or q.reason,extraction_method=page.extraction_method,selector_used=page.selector_used,content_hash=h,source_file=sf,cleaned_length=len(page.plain_text));qrows.append(row)
(OUT/"quality_gate/follow_quality_gate_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in qrows),encoding="utf-8")
eligible=[x for x in qrows if x.get("quality_gate_pass")]
(OUT/"quality_gate/follow_audit_candidates.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in eligible),encoding="utf-8")
s={"list_pages_requested":len(LISTS),"list_pages_ok":sum(x["ok"]for x in listlog),"follow_discovered":len(sel),"follow_fetch_ok":sum(x["ok"]for x in got),"follow_quality_gate_pass":len(eligible),"quality_classes":dict(Counter(x.get("quality_class")for x in qrows)),"internal_dedup":internal,"by_category":dict(Counter(x["discovery_category"]for x in eligible)),"by_domain":dict(Counter(x["domain"]for x in eligible))}
(OUT/"crawl/follow_summary.json").write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(s,ensure_ascii=False))
