from __future__ import annotations
import json
SYSTEM='Return JSON only. Decide document_decision HIGH, MEDIUM, or NONE. Generate 0-N candidates. Use only exact evidence spans from the Markdown; never add outside facts. Do not reveal reasoning.'
def prompt(doc):
    return [{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps({"title":doc["title"],"source_id":doc["source_id"],"markdown":doc["content"]},ensure_ascii=False)}]
def parse_response(data):
    if "choices" in data: text=data["choices"][0]["message"]["content"]
    elif "output" in data: text=data["output"]
    else: text=data
    if isinstance(text,dict): return text
    return json.loads(str(text).strip().removeprefix("```json").removesuffix("```").strip())
