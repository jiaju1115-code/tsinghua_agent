from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict
from pathlib import Path

TERMS=json.loads((Path(__file__).resolve().parents[1]/"config"/"academic_terms.json").read_text(encoding="utf-8"))
MATH_RE=re.compile(r"[∫∑Σ√∞λμσβθ∂]|\\(?:int|sum|frac|sqrt)|\b(?:lim|dx|dy|var|cov|det|rank)\s*\(?|(?:P|E|Var|Cov|det|rank)\s*\(",re.I)
SIMPLE_RE=re.compile(r"^\s*\d+(?:\.\d+)?\s*[+\-*/]\s*\d+(?:\.\d+)?\s*(?:等于多少|=)?\s*[?？]?\s*$")

@dataclass(frozen=True)
class RouteResult:
    mode: str; academic_score: int; campus_score: int; current_info_score: int; general_web_score: int; triggered_signals: list[str]; router_reason: str
    def to_dict(self): return asdict(self)

def route_v0_1(query: str) -> RouteResult:
    q=query.lower(); signals=[]; academic=campus=current=general=0
    if SIMPLE_RE.match(q): return RouteResult("NO_WEB_NEEDED",0,0,0,0,["stable_arithmetic"],"basic arithmetic needs no external evidence")
    for subject, words in TERMS["subjects"].items():
        hits=[w for w in words if w.lower() in q]
        if hits: academic+=2*len(hits); signals.extend([f"{subject}:{w}" for w in hits])
    # A subject concept plus an exam/problem formulation is academic structure,
    # even when a year token is present (for example, a 2026 exam question).
    if any(":" in signal and not signal.startswith("current:") for signal in signals) and ("考研" in q or ("题" in q and any(x in q for x in ("怎么", "如何", "处理", "证明", "求")))):
        academic+=1; signals.append("academic_problem_formulation")
    tasks=[w for w in TERMS["task_terms"] if w.lower() in q]
    if tasks: academic+=min(3,len(tasks)); signals.extend([f"academic_task:{w}" for w in tasks])
    if MATH_RE.search(q): academic+=3; signals.append("formula_or_symbol_structure")
    campus_hits=[w for w in TERMS["campus_terms"] if w in q]
    if campus_hits: campus+=3*len(campus_hits); signals.extend([f"campus:{w}" for w in campus_hits])
    current_hits=[w for w in TERMS["current_terms"] if w in q]
    if current_hits: current+=len(current_hits); signals.extend([f"current:{w}" for w in current_hits])
    general=2 if current_hits else 1
    if academic>=3 and academic>=campus: mode="ACADEMIC_RETRIEVAL"; reason=f"academic score {academic} from subject/task/structure signals outranks freshness score {current}"
    elif campus>=3: mode="CAMPUS_PUBLIC"; reason=f"campus score {campus} from campus-public signals"
    elif current>=1: mode="GENERAL_WEB"; reason=f"current-information score {current} without stronger academic/campus signals"
    elif len(q)<4: mode="UNCERTAIN"; reason="query is too short for reliable rule routing"
    else: mode="GENERAL_WEB"; reason="non-stable informational query defaults to general web"
    return RouteResult(mode,academic,campus,current,general,signals,reason)
