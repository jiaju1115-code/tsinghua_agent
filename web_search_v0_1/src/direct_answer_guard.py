from __future__ import annotations
import re
from difflib import SequenceMatcher

def possible_direct_answer(problem:str,title:str,text:str,url:str="")->bool:
    p=re.sub(r"\s+|\d+(?:\.\d+)?","",problem.lower()); candidate=(title+" "+text+" "+url).lower()
    overlap=SequenceMatcher(None,p,re.sub(r"\s+|\d+(?:\.\d+)?","",candidate)).ratio()
    tokens=re.findall(r"[\u4e00-\u9fff]{2,}|[a-z]{3,}",p)
    token_ratio=sum(x in candidate for x in tokens)/max(len(tokens),1)
    homework=any(x in candidate for x in ("coursehero","chegg","brainly","作业帮","搜题"))
    return homework or (len(p)>=12 and overlap>=.70) or (len(tokens)>=3 and token_ratio>=.75 and "答案" in candidate)
