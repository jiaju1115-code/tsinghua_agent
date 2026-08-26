import hashlib, re
def normalize(s):
    return re.sub(r"\s+", "", str(s)).lower()
def deduplicate(rows):
    seen=set(); kept=[]; removed=[]
    for row in rows:
        key=hashlib.sha256((normalize(row.get("query"))+"|"+normalize(row.get("answer"))).encode()).hexdigest()
        if key in seen: removed.append(row); continue
        seen.add(key); row["dedup_key"]=key; kept.append(row)
    return kept, removed
