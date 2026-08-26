from factory import OUT, NAMES
import json
if __name__=='__main__':
    n=bad=0
    for p in OUT.glob('*.jsonl'):
        for line in p.read_text(encoding='utf-8').splitlines():
            n+=1
            try:
                x=json.loads(line); bad += not all(x.get(k) for k in ('case_id','query','answer','evidence_spans'))
            except Exception: bad+=1
    print({'checked':n,'invalid':bad})
