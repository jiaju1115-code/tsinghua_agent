from __future__ import annotations
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from reviewer.duplicate_analyzer import duplicate_ids

LOW=re.compile(r"标兵|先进工作者|人物|科研办公|课题|基金|学术|活动举行|主题活动|新闻",re.I)
GUIDE=re.compile(r"指南|办事|办理|程序|服务|预约|接种|就诊|规定|制度|通知",re.I)
SHORT=re.compile(r"义诊|活动|讲座|比赛|当日|专家就诊|\d{1,2}月\d{1,2}日",re.I)
SUBS=[("校医院",r"校医院|医院|就诊"),("疫苗",r"疫苗|接种"),("后勤服务",r"后勤|报修|服务指南"),("国际交流",r"国际合作|国际交流"),("签证",r"签证"),("出境",r"出境|申根"),("注册",r"注册"),("信息系统",r"系统|信息网")]

def _sub(text):
    for name,pat in SUBS:
        if re.search(pat,text,re.I):return name
    return "其他"

def review_portal(candidate,markdown):
    text=candidate["title"]+" "+markdown[:8000];low=bool(LOW.search(text));guide=bool(GUIDE.search(text));short=bool(SHORT.search(text))
    action="reject" if low and not guide else "review"
    local="local_reject_candidate" if action=="reject" else ("local_high_value_candidate" if guide and not short else "local_time_sensitive_candidate")
    category=candidate.get("category_hint") if candidate.get("category_hint") in {"校园办事","校园生活","新生入校","规章制度","校园通知","其他"} else "其他"
    ctype="人物宣传" if re.search(r"标兵|先进工作者|人物",text) else ("活动通知" if short else ("办事指南" if re.search(r"办事|办理|程序",text) else ("服务指南" if guide else "其他")))
    fresh="unknown";year=re.search(r"(?<!\d)(20\d{2})(?!\d)",text)
    if year:
        y=int(year.group(1));now=datetime.now(ZoneInfo("Asia/Shanghai")).year;fresh="outdated" if y<now-1 else ("possibly_outdated" if y<now else "current")
    reason="明确属于低价值人物/科研/活动宣传候选，建议人工确认后排除。" if action=="reject" else ("包含校园公共服务或办事信息；Portal原文不外发，进入人工复核。")
    return {"id":candidate["id"],"relevance_score":25 if action=="reject" else 82,"knowledge_value":15 if action=="reject" else 75,"category":category,"subcategory":_sub(text),"content_type":ctype,"authority":"high","freshness":fresh,"time_sensitivity":"high" if short else "medium","contains_actionable_information":guide,"personal_data_risk":"none","possible_duplicate":candidate["id"] in duplicate_ids(),"possible_conflict":False,"recommended_action":action,"reason":reason,"local_classification":local}

