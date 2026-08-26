from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return {x['case_id']:x for x in (json.loads(z) for z in p.read_text(encoding='utf-8').splitlines() if z.strip())}
def main():
 b=read(ROOT/'results/base/general_per_case.jsonl');p=read(ROOT/'results/pilot_v0/general_per_case.jsonl');paired=[];families=defaultdict(list)
 for cid in sorted(b):
  x,y=b[cid],p[cid];row={'case_id':cid,'family':x['family'],'base_raw_output':x['raw_output'],'pilot_v0_raw_output':y['raw_output'],'base_score':x['score'],'pilot_v0_score':y['score']};paired.append(row);families[x['family']].append(row)
 def summary(rows):
  bc=sum(x['base_score'] for x in rows);pc=sum(x['pilot_v0_score'] for x in rows);return {'N':len(rows),'base_correct':bc,'pilot_correct':pc,'base_accuracy':bc/len(rows),'pilot_accuracy':pc/len(rows),'delta':(pc-bc)/len(rows),'improvements':[x['case_id'] for x in rows if x['base_score']==0 and x['pilot_v0_score']==1],'regressions':[x['case_id'] for x in rows if x['base_score']==1 and x['pilot_v0_score']==0]}
 out={'overall':summary(paired),'families':{k:summary(v) for k,v in families.items()}}
 d=ROOT/'results/comparison';d.mkdir(parents=True,exist_ok=True);(d/'general_comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');(d/'general_paired_per_case.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in paired),encoding='utf-8')
if __name__=='__main__':main()
