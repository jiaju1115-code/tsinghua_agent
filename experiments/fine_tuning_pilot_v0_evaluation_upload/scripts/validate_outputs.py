from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 errors=[]
 for name in ('base','pilot_v0'):
  p=ROOT/'results'/name/'campus_per_case.jsonl'
  if not p.exists(): errors.append(f'missing {p}')
  elif sum(1 for x in p.read_text(encoding='utf-8').splitlines() if x.strip())!=50: errors.append(f'{name} does not have 50 cases')
 result={'status':'PASS' if not errors else 'FAIL','errors':errors};(ROOT/'results/validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));sys.exit(bool(errors))
if __name__=='__main__':main()
