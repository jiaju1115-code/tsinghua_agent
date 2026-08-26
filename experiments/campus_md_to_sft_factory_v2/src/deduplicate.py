from factory import OUT
import json
if __name__=='__main__':
    seen=set(); dup=0
    for p in OUT.glob('*.jsonl'):
        for line in p.read_text(encoding='utf-8').splitlines():
            x=json.loads(line); k=(x.get('query','').strip(),tuple(x.get('evidence_spans',[])))
            if k in seen: dup+=1
            seen.add(k)
    print({'unique':len(seen),'duplicates':dup})
