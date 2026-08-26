from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 freeze=json.loads((ROOT/'baseline_reference/e2e_heldout_dataset_freeze.json').read_text(encoding='utf-8'))
 p=ROOT/'data/campus/e2e_50_cases.jsonl'; raw=p.read_bytes(); actual=sha(p); normalized=hashlib.sha256(raw.decode('utf-8-sig',errors='replace').replace('\r\n','\n').replace('\r','\n').encode()).hexdigest(); expected=freeze['dataset_sha256']
 status='PASS_RAW_MATCH' if actual==expected else ('SEMANTIC_MATCH_RAW_HASH_MISMATCH' if normalized==expected else 'FAIL')
 result={'status':status,'expected_sha256':expected,'actual_raw_sha256':actual,'normalized_lf_sha256':normalized,'action':'Raw canonical bytes were not found. Evaluation is permitted only with prominent provenance warning because the historical digest matches normalized LF bytes.' if status=='SEMANTIC_MATCH_RAW_HASH_MISMATCH' else 'Do not execute Campus evaluation until the authoritative frozen asset or its freeze manifest is reconciled.'}
 (ROOT/'results/frozen_integrity_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));sys.exit(status=='FAIL')
if __name__=='__main__':main()
