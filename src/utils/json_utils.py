import json,re

def parse_json_object(text:str)->dict:
    cleaned=text.strip()
    if cleaned.startswith("```"):
        cleaned=re.sub(r"^```(?:json)?\s*|\s*```$","",cleaned,flags=re.I|re.S)
    try:value=json.loads(cleaned)
    except json.JSONDecodeError:
        start,end=cleaned.find("{"),cleaned.rfind("}")
        if start<0 or end<=start:raise
        value=json.loads(cleaned[start:end+1])
    if not isinstance(value,dict):raise ValueError("模型输出必须是JSON对象")
    return value

