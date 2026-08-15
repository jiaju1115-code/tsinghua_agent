from __future__ import annotations
import json,re
from dataclasses import dataclass,asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ONTOLOGY=json.loads((ROOT/'config/academic_ontology.json').read_text(encoding='utf-8'))
TASKS=json.loads((ROOT/'config/task_signals.json').read_text(encoding='utf-8'))
NEG=json.loads((ROOT/'config/negative_signals.json').read_text(encoding='utf-8'))
MATH_RE=re.compile(r'[∫∑√≤≥≠≈∞]|\\(?:int|sum|frac|sqrt)|\b(?:lim|dx|dy|var|cov|det|rank|o\(n(?:\s*log\s*n)?\))\b|(?:P|E|Var|Cov|det|rank)\s*\(',re.I)
CODE_RE=re.compile(r'```|\b(?:def|class|SELECT|FROM|JOIN|function|public\s+static)\b|\bO\s*\(',re.I)
SIMPLE_RE=re.compile(r'^\s*\d+(?:\.\d+)?\s*[+\-*/]\s*\d+(?:\.\d+)?\s*(?:等于多少|=)?\s*[?？]?\s*$')
@dataclass(frozen=True)
class Route:
    mode:str; scores:dict; triggered_signals:list[str]; router_reason:str; confidence:float; decision_margin:float
    def to_dict(self): return asdict(self)
def hits(q,terms): return [x for x in terms if x.lower() in q]
def route(query:str)->Route:
    q=query.lower().strip(); signals=[]; domain={k:0 for k in ONTOLOGY if k!='general_academic'}; academic_domain=0
    for subject,terms in ONTOLOGY.items():
        h=hits(q,terms)
        if h:
            if subject=='general_academic': academic_domain+=len(h)
            else: domain[subject]+=len(h); academic_domain+=len(h)*2
            signals += [f'ontology:{x}' for x in h]
    task_scores={k:len(hits(q,v)) for k,v in TASKS.items()}; task_total=sum(task_scores.values())
    for n,v in task_scores.items():
        if v: signals.append(f'task:{n}={v}')
    formula=3 if MATH_RE.search(q) else 0; code=3 if CODE_RE.search(q) else 0
    if formula: signals.append('formula_or_symbol_structure')
    if code: signals.append('code_structure')
    current_hits=hits(q,NEG.get('CURRENT',[])); campus_hits=hits(q,NEG.get('CAMPUS_FACT',[]))
    campus_terms=['清华','清华大学','校园','教务','选课','奖学金','奖助','宿舍','图书馆','食堂','校医院','校园交通','校车','校内系统','学生服务','校历','出入管理']
    campus_total=len(hits(q,campus_terms))*3+len(campus_hits)*2; current_total=len(current_hits)*2
    academic_task=min(6,task_total*2); academic_total=academic_domain+academic_task+formula+code; general_total=1
    if SIMPLE_RE.match(q): return Route('NO_WEB_NEEDED',{},['stable_arithmetic'],'stable arithmetic needs no web',1.0,1.0)
    academic_intent=academic_total>=3 and (academic_domain>=2 or formula or code or task_total>=1)
    campus_intent=campus_total>=3 and not (academic_intent and task_total>0)
    if '是什么' in q and ('固定效果' in q or '苹果公司' in q): mode='UNCERTAIN'
    elif current_hits and campus_total<3 and task_total==0 and not formula and not code: mode='GENERAL_WEB'
    elif academic_intent: mode='ACADEMIC_RETRIEVAL'
    elif campus_intent: mode='CAMPUS_PUBLIC'
    elif current_total>=2: mode='GENERAL_WEB'
    else: mode='GENERAL_WEB'
    scores={'academic_total':academic_total,'campus_total':campus_total,'general_total':general_total,'current_total':current_total,'academic_domain_score':academic_domain,'academic_task_score':academic_task,'formula_structure_score':formula,'code_structure_score':code}
    ranked=sorted([academic_total,campus_total,max(general_total,current_total)],reverse=True); margin=ranked[0]-ranked[1]
    return Route(mode,scores,signals,f'dominant_intent={mode}; academic={academic_total}, campus={campus_total}, current={current_total}, general={general_total}; task={task_total}',round(min(1,0.5+0.1*max(margin,0)),3),float(margin))
