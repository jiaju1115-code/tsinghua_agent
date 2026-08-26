from __future__ import annotations
import re
ALLOWED={"SUPPORTED","PARTIAL","NOT_SUPPORTED","PARAPHRASE","GROUNDED_ANSWER"}
def validate(doc, result, held_out=()):
    reasons=[]
    if not isinstance(result,dict) or result.get("document_decision") not in {"HIGH","MEDIUM","NONE"}: reasons.append("INVALID_DOCUMENT_DECISION")
    candidates=result.get("candidates",[]) if isinstance(result,dict) else []
    if not isinstance(candidates,list): reasons.append("INVALID_CANDIDATES") ; candidates=[]
    for c in candidates:
        if c.get("sample_type") not in ALLOWED: reasons.append("INVALID_SAMPLE_TYPE"); continue
        evidence=c.get("evidence_spans",[]); answer=c.get("answer","")
        if not c.get("query") or not c.get("required_points") or not answer: reasons.append("EMPTY_REQUIRED_FIELD")
        for span in evidence:
            if not span or span not in doc["content"]: reasons.append("EVIDENCE_NOT_IN_SOURCE")
        if c.get("sample_type")=="PARTIAL" and (len(c.get("required_points",[]))<2 or not c.get("supported_required_points") or not c.get("unsupported_required_points")): reasons.append("PARTIAL_POLICY_VIOLATION")
        if any(h and (h in c.get("query","") or h in answer) for h in held_out): reasons.append("HELD_OUT_LEAKAGE_BLOCKED")
    return (not reasons, reasons)
