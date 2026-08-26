from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
    ids=set(); bad=[]
    for name in ('train.jsonl','validation.jsonl'):
        for i,line in enumerate((ROOT/'data'/name).read_text(encoding='utf-8').splitlines(),1):
            try:
                x=json.loads(line); ms=x['messages']; assert len(ms)==2 and ms[0]['role']=='user' and ms[1]['role']=='assistant'; assert ms[0]['content'] and ms[1]['content']; cid=x['metadata']['original_id']; assert cid not in ids; ids.add(cid)
            except Exception as e: bad.append(f'{name}:{i}:{e}')
    out={'checked':len(ids),'invalid':len(bad),'errors':bad}; print(json.dumps(out,ensure_ascii=False)); return 1 if bad else 0
if __name__=='__main__': raise SystemExit(main())
