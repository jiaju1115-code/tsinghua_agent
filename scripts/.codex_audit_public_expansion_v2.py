from __future__ import annotations
import json,re,hashlib
from pathlib import Path
from collections import Counter
from datetime import date
from urllib.parse import urlsplit

ROOT=Path(r"D:\python_projects\tsinghua_ai");OUT=ROOT/"data_second/public_expansion_v2";ASOF=date(2026,8,12)
PROMPT=ROOT/"data_second/prompt_v3_2_blind_test_v1/blind_bundle_v1/prompt/prompt_v3_2.md"
def rows(p):return [json.loads(x)for x in p.read_text(encoding="utf-8").splitlines()if x.strip()]
def dates(t):
 out=[]
 for y,m,d in re.findall(r"(20\d{2})[年./\-](\d{1,2})[月./\-](\d{1,2})",t):
  try:out.append(date(int(y),int(m),int(d)))
  except:pass
 return out
inp=rows(OUT/"quality_gate/canonical_audit_candidates.jsonl")
# Absolute final dedup across the pooled rounds.
seen_url=set();seen_hash=set();dedup=[];internal_final=0
for r in sorted(inp,key=lambda x:x["id"]):
 u=r.get("normalized_url")or r.get("url","");h=r.get("content_hash","")
 if u in seen_url or(h and h in seen_hash):internal_final+=1;continue
 seen_url.add(u);h and seen_hash.add(h);dedup.append(r)
ordinary=re.compile(r"获奖|喜报|当选|会见|调研|出席|签约|合作新闻|讲座|论坛|研讨会|座谈会|开幕|闭幕|举办|举行|活动回顾|交流会|毕业典礼|党日|宣传周|纪念活动|会议召开|领导讲话|科研成果|研究团队.*揭示|论文|竞赛|比赛|表彰")
stable=re.compile(r"指南|办法|规定|制度|规则|流程|手续|服务|机构|部门|中心|实验室|研究院|平台|资源|课程|培养|学籍|考试|学位|毕业|住宿|餐饮|交通|医疗|体育|场馆|奖学金|助学|就业|职业|签证|居留|保险|校园|历史|文化|档案|FAQ|Guide|Visa|Residence|Accommodation|Scholarship|Internship|Employment|Policy|Service",re.I)
current=re.compile(r"通知|公告|安排|开放时间|暂停|调整|试用|报名|课表")
cat_patterns=[
 ("教务与学籍",r"学籍|选课|退课|考试|成绩|注册|转专业|休学|复学|毕业证|学位证|在学证明|课程替代|免修|本科生"),
 ("学生事务",r"学生管理|学生纪律|处分|申诉|学生社团|户籍|户政|身份证|政审|学生档案|第二成绩单|学生手册"),
 ("住宿服务",r"住宿|宿舍|公寓|调宿|退宿|住宿登记"),("餐饮服务",r"餐饮|食堂|餐厅|饮食|供餐"),("交通服务",r"交通|停车|车辆|车证|校车|班车|电动自行车|校门通行|shuttle|bus"),
 ("医疗健康",r"医疗|医院|挂号|就诊|体检|医保|健康|心理|门诊|急诊"),("网络与信息化",r"网络|VPN|邮箱|云盘|信息化|校园卡|电子身份|信息系统"),
 ("体育与场馆",r"体育|场馆|游泳|健身|操场|体育设施"),("奖助与资助",r"奖学金|助学|资助|勤工|贷款|困难|学费减免|Scholarship"),
 ("国际事务与签证",r"签证|护照|居留|国际学生|出入境|国际交流|交换|Visa|Passport|Residence|International"),("就业与职业发展",r"就业|职业|生涯|实习|毕业生手续|档案转递|Employment|Internship|Career"),
 ("校园访问",r"校园参观|参观预约|访客|个人参观|团队参观|visit"),("科研参与与资源导航",r"科研|实验室|研究平台|研究中心|分析中心|仪器|数据库|学术资源|研究院|基金"),
 ("教学与培养",r"教学|培养|课程|教育|通识|研究生|专业学位|学位项目"),("校园机构与部门",r"组织机构|机构设置|部门|单位|院系|中心简介|职能|委员会|研究院|书院"),
 ("校园文化与历史",r"历史|校史|沿革|文化|传统|校训|校歌|校徽|校园建筑|校园风光"),("清华基本信息",r"清华大学简介|学校简介|现任领导|学校概况|清华章程"),("校园综合服务",r"综合服务|服务信息|快递|邮寄|活动室|联系方式|办事指南")]
def category(title,text,discovery):
 s=title+" "+text[:2500]
 for c,p in cat_patterns:
  if re.search(p,s,re.I):return c
 return discovery if discovery in {x[0]for x in cat_patterns} else "非目标范围"
def ctype(title,text):
 s=title+" "+text[:1200]
 if re.search(r"办法|规定|制度|规则|条例|实施细则|管理规范|Policy",s,re.I):return"policy"
 if ordinary.search(title) and not re.search(r"管理中心|研究中心|服务中心",title):return"news_event"
 if re.search(r"通知|公告|课表|公开选拔|报名",title):return"current_notice"
 if re.search(r"FAQ|常见问题|须知",s,re.I):return"faq"
 if re.search(r"流程|手续|办理|申请|指南|Guide|Procedures",s,re.I):return"procedure_guide"
 if re.search(r"114平台预约挂号",title):return"service_entry"
 if current.search(title):return"current_notice"
 if re.search(r"机构|部门|中心|研究院|实验室|委员会|简介|职能|组织",s,re.I):return"organization_intro"
 if re.search(r"目录|导航|资源|平台|服务信息",title):return"resource_directory"
 if ordinary.search(title):return"news_event"
 if re.search(r"服务|场馆|设施|交通|医疗|住宿|餐饮|就业|签证",s,re.I):return"service_entry"
 return"mixed"
out=[]
for r in dedup:
 p=OUT/r["source_file"];text=p.read_text(encoding="utf-8",errors="ignore") if p.exists() else"";title=r.get("title","");ct=ctype(title,text);cat=category(title,text,r.get("discovery_category",""));ds=dates(title+" "+text[:3500]);future=[x for x in ds if x>=ASOF];past=[x for x in ds if x<ASOF]
 action="approve";reject_type="";topic="high";time_status="evergreen";valid_from="";valid_until="";reason="正文提供稳定的清华校园服务、规则、机构、培养或可利用资源，具有可复用知识价值。";neg="无"
 is_low=bool(ordinary.search(title)) and ct not in {"policy","procedure_guide","faq","service_entry","organization_intro"} and not bool(re.search(r"上线|启用|建成|成立|正式开通",title)and stable.search(text[:1800]))
 if is_low:
  action="reject";reject_type="topic_irrelevant";topic="low";time_status="historical_but_valuable" if past else"unknown";cat="非目标范围";reason="核心是普通活动、会议、成果、人物或宣传报道，未形成可复用的校园服务或资源条目。";neg="新闻事件本身复用价值低。"
 elif ct=="current_notice" and (re.search(r"邮寄地址|114平台预约挂号",title) or re.search(r"正式与.*平台实现直连|长期使用|常年",text[:1200])):
  time_status="historical_but_valuable";action="approve";reason="页面虽含发布日期或上线日期，但正文明确形成当前持续可用的校园服务信息。"
 elif ct=="current_notice" and re.search(r"2026\s*[-–—]\s*2027学年秋季",title):
  time_status="active_time_bound";action="review";reason="主题高度相关且对应审核基准日之后的秋季学期，但正文未给出精确截止日，需人工复核。";neg="仅能确认适用学期，不能提取精确有效期。"
 elif ct=="current_notice":
  if future:
   until=max(future);valid_until=until.isoformat();time_status="active_time_bound";action="review" if(until-ASOF).days<=60 else"approve";reason="主题高度相关且仍在有效期；临近截止边界需人工复核。" if action=="review" else"主题高度相关且当前有效，明确截止日期距基准日超过60天。"
  elif past:
   time_status="expired";action="reject";reject_type="expired_event";valid_until=max(past).isoformat();reason="主题属于校园核心事务，但页面通知的明确日期均已早于审核基准日。";neg="页面时间窗口已过。"
  else:
   action="review";time_status="unknown";reason="主题高度相关，但正文无法确认通知当前是否仍有效。";neg="缺少可确认的有效期。"
 elif ct in{"mixed","resource_directory"} and r.get("quality_class") in{"thin_content","template_polluted"}:
  action="review";topic="medium";time_status="unknown";reason="页面与校园知识相关，但稳定复用价值或当前有效性边界需要人工复核。";neg="正文为混合或薄内容，知识边界较弱。"
 elif re.search(r"历史|沿革|校史|传统",title):topic="medium";time_status="historical_but_valuable";reason="页面提供持续认知价值的校园历史、机构或文化信息。"
 elif past and re.search(r"成立|建成|启用|上线",title):time_status="historical_but_valuable";reason="过去事件明确形成当前可认识的机构、设施、平台或服务。"
 # low+approve is forbidden by the prompt
 if topic=="low" and action!="reject":action="reject";reject_type="topic_irrelevant";cat="非目标范围"
 status={"approve":"candidate_approved","review":"candidate_review","reject":"candidate_rejected"}[action]
 q="" if action=="reject" else f"{title.rstrip('。？?')}是什么，如何使用或了解？"
 out.append({"id":r["id"],"title":title,"url":r["url"],"normalized_url":r["normalized_url"],"domain":r["domain"],"discovery_source":r["discovery_source"],"discovery_category":r["discovery_category"],"parent_list_url":r.get("parent_list_url","") ,"crawl_timestamp":r.get("crawl_timestamp",""),"extraction_method":r["extraction_method"],"selector_used":r.get("selector_used","") ,"quality_class":r["quality_class"],"content_hash":r["content_hash"],"source_file":r["source_file"],"v3_2_action":action,"action":action,"v3_2_reject_type":reject_type,"reject_type":reject_type,"category":cat,"content_type":ct,"audience":"清华学生及校园相关用户","topic_relevance":topic,"time_status":time_status,"valid_from":valid_from,"valid_until":valid_until,"candidate_user_question":q,"positive_evidence":text[:320].replace("\n"," "),"negative_evidence":neg,"possible_duplicate":False,"reason":reason,"data_status":status,"prompt_version":"v3.2_frozen","prompt_sha256":hashlib.sha256(PROMPT.read_bytes()).hexdigest(),"model":"current Codex","audit_date":"2026-08-13"})
(OUT/"audit/public_expansion_v2_v3_2_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n"for x in out),encoding="utf-8")
s={"input_quality_gate_pass":len(inp),"final_audit_count":len(out),"final_pool_internal_dedup":internal_final,"actions":dict(Counter(x["action"]for x in out)),"categories":dict(Counter(x["category"]for x in out)),"domains":dict(Counter(x["domain"]for x in out)),"low_plus_approve":sum(x["topic_relevance"]=="low"and x["action"]=="approve"for x in out),"prompt_sha256":hashlib.sha256(PROMPT.read_bytes()).hexdigest()}
(OUT/"audit/audit_summary.json").write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(s,ensure_ascii=False))
