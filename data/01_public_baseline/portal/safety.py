from __future__ import annotations

import re
from crawler.prioritizer import HIGH

PRIVATE_TERMS=("我的","个人","成绩","gpa","课表","选课结果","考试安排","余额","消费","财务","工资","借阅记录","申请状态","个人中心","账号设置","个人信息","身份证","银行卡","医疗记录","体检结果","我的申请","我的账户","我的借阅")
PUBLIC_TERMS=HIGH+("通知","规章","制度","师生","业务流程","办理材料","服务时间","办理地点")
LOW_VALUE_TERMS=("科研","论文","课题","基金","采购","中标","招聘","讣告","学术","实验室","奖项")
SENSITIVE_VALUE_PATTERNS=(
    re.compile(r"身份证(?:号|号码)?\s*[：:]?\s*\d{15,18}[0-9Xx]"),
    re.compile(r"银行卡(?:号|号码)?\s*[：:]?\s*\d{12,19}"),
    re.compile(r"(?:校园卡余额|账户余额|GPA|平均绩点)\s*[：:]?\s*\d"),
    re.compile(r"(?:我的成绩|我的课表|我的申请|我的审批|我的借阅|我的账户)"),
    re.compile(r"姓名\s*[：:]\s*[^\s]{2,8}.{0,120}学号\s*[：:]\s*\d{6,15}",re.S),
    re.compile(r"(?:手机号名单|联系电话名单|学生名单|人员名单).{0,200}1[3-9]\d{9}",re.S),
    re.compile(r"(?:个人医疗记录|个人体检结果|个人消费记录|个人缴费记录|个人工资|个人住宿房间)"),
)

def private_reason(url: str="", anchor: str="", title: str="", text: str="") -> str|None:
    head=(url+" "+anchor+" "+title).lower()
    if re.search(r"(?:^|[/_.-])(?:my|myhome|personal|usercenter)(?:[/_.-]|$)",url.lower()):return "private_url_pattern"
    for term in PRIVATE_TERMS:
        if term.lower() in head: return f"private_keyword:{term}"
    sample=text[:8000]
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern.search(sample): return f"sensitive_value_pattern:{pattern.pattern[:24]}"
    return None

def portal_priority(url: str, anchor: str="") -> int:
    hay=(url+" "+anchor).lower()
    if private_reason(url,anchor): return -1000
    return 10*sum(term.lower() in hay for term in PUBLIC_TERMS)-20*sum(term.lower() in hay for term in LOW_VALUE_TERMS)

def is_public_candidate(url: str, title: str, text: str) -> bool:
    hay=(url+" "+title+" "+text[:5000]).lower()
    return any(term.lower() in hay for term in PUBLIC_TERMS)
