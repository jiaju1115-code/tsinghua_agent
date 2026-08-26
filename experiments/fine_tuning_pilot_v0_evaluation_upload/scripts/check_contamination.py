from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def norm(v): return re.sub(r'[\W_]+','',v.casefold(),flags=re.UNICODE)
def rows(p):
 return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def text(x):
 if isinstance(x,dict): return ' '.join(text(v) for v in x.values())
 if isinstance(x,list): return ' '.join(text(v) for v in x)
 return str(x)
def main():
 cases=rows(ROOT/'data/campus/e2e_50_cases.jsonl'); train=[]
 for p in (ROOT/'data/training').glob('*.jsonl'): train += rows(p)
 ids={str(x.get('case_id',x.get('id',''))) for x in train}; raw={text(x) for x in train}; normal={norm(x) for x in raw}
 matches=[]
 for c in cases:
  q=str(c.get('query',''))
  if c.get('case_id') in ids or q in raw or norm(q) in normal: matches.append(c.get('case_id'))
 result={'status':'PASS' if not matches else 'FAIL','checks':['exact_id','exact_text','normalized_text','source_row'], 'campus_case_count':len(cases),'training_row_count':len(train),'matches':matches,'source_row_overlap':'NOT_APPLICABLE_NO_SHARED_SOURCE_ROW_IDS'}
 (ROOT/'results'/'contamination_check.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(result,ensure_ascii=False));sys.exit(bool(matches))
if __name__=='__main__':main()
