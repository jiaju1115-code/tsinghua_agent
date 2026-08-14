from __future__ import annotations
import json, re, random, hashlib
from pathlib import Path
from collections import Counter
from datetime import date

ROOT=Path(r"D:\python_projects\tsinghua_ai")
BASE=ROOT/"data_second/public_rebuild_v1"
OUT=ROOT/"data_second/public_expansion_v2"
PROMPT=ROOT/"data_second/prompt_v3_2_blind_test_v1/blind_bundle_v1/prompt/prompt_v3_2.md"
ASOF=date(2026,8,12)

def lines(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def dumpjl(p, rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8")
def normcat(x):
    m={"校园基本信息":"清华基本信息","校园生活":"校园综合服务","国际事务":"国际事务与签证"}
    return m.get(x,x if x in {"清华基本信息","教务与学籍","学生事务","住宿服务","餐饮服务","交通服务","医疗健康","网络与信息化","图书馆服务","体育与场馆","奖助与资助","国际事务与签证","就业与职业发展","校园访问","校园综合服务","科研参与与资源导航","教学与培养","校园机构与部门","校园文化与历史","非目标范围"} else "非目标范围")
def dates(text):
    ys=[]
    for y,m,d in re.findall(r"(20\d{2})[年\-/](\d{1,2})[月\-/](\d{1,2})",text):
        try: ys.append(date(int(y),int(m),int(d)))
        except: pass
    return ys

rows=lines(BASE/"audit/audit_results.jsonl")
out=[]
ordinary=re.compile(r"讲座|论坛|研讨会|座谈会|参访|到访|调研|出席|会议|活动|培训|书展|展览|真人图书馆|党日|社会实践|开幕|举行|举办|获奖|喜报|当选|签署|合作备忘|联学|交流")
resource=re.compile(r"数据库|平台|系统上线|正式订购|开放获取.*政策|OA.*政策|服务|指南|办法|规定|规则|流程|须知|借阅|借还|开馆时间|馆际互借|失物招领|联系方式|联系我们|岗位申请|组织机构|部门职能|科室职能|中心简介|历史沿革|馆长致辞|专题专架|资源|iLibrary")
core_notice=re.compile(r"闭馆|开馆|停用|暂停|权限|试用|离校|预约|座位|荐购|毕业生|系统")
for r in rows:
    text=(BASE/r["source_file"]).read_text(encoding="utf-8",errors="ignore")
    title=r["title"]
    ct=r.get("content_type") or "mixed"
    cat=normcat(r.get("category","非目标范围"))
    ds=dates(title+" "+text[:2500])
    latest=max(ds) if ds else None
    is_expired=bool(latest and latest<ASOF) or r.get("time_status") in {"outdated"}
    is_event=ct in {"news_event","research_news","promotional_content","achievement_report"} or bool(ordinary.search(title))
    is_resource=ct in {"service_entry","procedure_guide","policy","faq","resource_directory","organization_intro"} or bool(resource.search(title))
    action="approve"; reject_type=""; topic="high"; time_status="evergreen"
    reason="正文提供稳定的清华校园服务、机构职责、规则或可利用资源，具有可复用知识价值。"
    if is_event and not (re.search(r"启用|上线|正式订购",title) and resource.search(text[:1200])):
        action="reject"; reject_type="topic_irrelevant"; topic="low"; time_status="expired" if is_expired else "historical_but_valuable"
        reason="核心是普通新闻、活动、人物、成果或合作报道，未形成可复用的校园服务或资源条目。"
        cat="非目标范围"
    elif ct=="current_notice" or core_notice.search(title):
        if is_expired:
            action="reject"; reject_type="expired_event"; topic="high"; time_status="expired"
            reason="主题属于校园核心服务或资源，但通知中的时间窗口在基准日前已经结束。"
        elif latest:
            delta=(latest-ASOF).days
            time_status="active_time_bound"
            action="review" if delta<=60 else "approve"
            reason="主题高度相关且当前仍有效；因有效期临近需人工复核。" if action=="review" else "主题高度相关且当前有效，有明确且超过60天的未来边界。"
        else:
            time_status="unknown"; action="review"; reason="主题高度相关，但正文无法确认当前有效期限，需人工复核。"
    elif is_resource:
        if re.search(r"历史沿革|馆长致辞|大事年表",title):
            topic="medium"; time_status="historical_but_valuable"; cat="校园文化与历史"
            reason="历史页面形成对持续存在的校园机构、设施与资源体系的稳定认识。"
        elif re.search(r"部门职能|科室职能|中心简介|组织机构",title):
            cat="校园机构与部门"; time_status="evergreen"
        elif re.search(r"教学环境|教学资源",title): cat="教学与培养"
        elif re.search(r"网络|信息系统|信息化|用户服务",title): cat="网络与信息化"
        elif re.search(r"数据库|开放获取|OA|科研|iLibrary",title): cat="科研参与与资源导航"
        elif "图书馆" in r.get("source_domain","") or "lib.tsinghua" in r.get("url",""): cat="图书馆服务"
    else:
        action="review"; topic="medium"; time_status="unknown"; reason="页面与校园知识相关，但稳定复用价值或当前有效性边界不够明确。"
    if action=="reject" and reject_type=="topic_irrelevant": cat="非目标范围"
    valid_until=latest.isoformat() if latest and (ct=="current_notice" or core_notice.search(title)) else ""
    status={"approve":"candidate_approved","review":"candidate_review","reject":"candidate_rejected"}[action]
    out.append({
      "id":r["id"],"original_id":r["id"],"title":title,"url":r["url"],"domain":r["source_domain"],"source_group":"public_rebuild_v1_217","source_file":r["source_file"],
      "action":action,"reject_type":reject_type,"category":cat,"content_type":ct,"topic_relevance":topic,"time_status":time_status,"valid_from":"","valid_until":valid_until,
      "reason":reason,"data_status":status,"prompt_version":"v3.2_frozen","model":"Codex","reviewed_at":"2026-08-13","cleaned_content":text
    })
dumpjl(OUT/"audit/public_v3_2_reaudit_217.jsonl",out)

# deterministic production QC sample
rng=random.Random(320217)
selected={x["id"] for x in out if x["action"]=="review"}
approves=[x for x in out if x["action"]=="approve"]
selected.update(x["id"] for x in rng.sample(approves,max(1,round(len(approves)*.20))))
forced={"news_event","current_notice","promotional_content","achievement_report","research_news"}
selected.update(x["id"] for x in approves if x["content_type"] in forced or x["topic_relevance"]=="medium" or x["time_status"]=="active_time_bound")
rejects=[x for x in out if x["action"]=="reject"]
selected.update(x["id"] for x in rng.sample(rejects,max(1,round(len(rejects)*.10))))
sample=[]
for i,x in enumerate([x for x in out if x["id"] in selected],1):
    sample.append({"check_id":f"HC{i:04d}","original_id":x["id"],"title":x["title"],"url":x["url"],"domain":x["domain"],"category":x["category"],"content_type":x["content_type"],"topic_relevance":x["topic_relevance"],"time_status":x["time_status"],"v3_2_action":x["action"],"v3_2_reject_type":x["reject_type"],"v3_2_reason":x["reason"],"cleaned_content":x["cleaned_content"],"human_action":"","human_reject_type":"","human_note":""})
(OUT/"human_check/human_check_rows.json").write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding="utf-8")

cats=["清华基本信息","教务与学籍","学生事务","住宿服务","餐饮服务","交通服务","医疗健康","网络与信息化","图书馆服务","体育与场馆","奖助与资助","国际事务与签证","就业与职业发展","校园访问","校园综合服务","科研参与与资源导航","教学与培养","校园机构与部门","校园文化与历史"]
ac=Counter(x["category"] for x in out if x["action"]=="approve")
prio={c:("P0" if c in {"教务与学籍","学生事务","住宿服务","餐饮服务","交通服务","医疗健康","奖助与资助","就业与职业发展"} else "P1" if c in {"体育与场馆","国际事务与签证","校园访问","校园综合服务","教学与培养","网络与信息化"} else "P2") for c in cats}
gap=[{"category":c,"priority":prio[c],"current_approve":ac[c],"gap_status":"CRITICAL" if ac[c]<5 else "HIGH" if ac[c]<10 else "MODERATE" if ac[c]<20 else "COVERED","suggested_v2_target":40 if prio[c]=="P0" else 25 if prio[c]=="P1" else 15} for c in cats]
(OUT/"planning/current_category_gap_rows.json").write_text(json.dumps(gap,ensure_ascii=False,indent=2),encoding="utf-8")
summary={"reaudit_count":len(out),"actions":Counter(x["action"] for x in out),"approve_categories":ac,"human_check_n":len(sample),"prompt_sha256":hashlib.sha256(PROMPT.read_bytes()).hexdigest()}
(OUT/"planning/reaudit_217_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=dict),encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,default=dict))
