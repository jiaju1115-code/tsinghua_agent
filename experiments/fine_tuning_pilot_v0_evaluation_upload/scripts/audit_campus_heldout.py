from __future__ import annotations
import hashlib,json,os,re
from datetime import datetime,timezone
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[3]; ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'audit'; OUT.mkdir(exist_ok=True)
TERMS=('heldout','held_out','held-out','e2e_50','heldout_50','8194d0','958887','50-case manifest','e2e evaluation v1','evaluation freeze manifest')
TEXT={'.json','.jsonl','.md','.py','.txt','.yaml','.yml','.manifest'}
def digest(b):return hashlib.sha256(b).hexdigest()
def normlf(b):return digest(b.decode('utf-8-sig',errors='replace').replace('\r\n','\n').replace('\r','\n').encode())
def semantic(b):
 try:
  rows=[json.loads(x) for x in b.decode('utf-8-sig').splitlines() if x.strip()]
  return digest(('\n'.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')) for x in rows)).encode())
 except Exception:return None
def jsonl_meta(p,b):
 try:
  rows=[json.loads(x) for x in b.decode('utf-8-sig').splitlines() if x.strip()]; ids=[str(x.get('case_id',x.get('id',''))) for x in rows]
  return len(rows),ids,ids[0] if ids else None,ids[-1] if ids else None
 except Exception:return None,[],None,None
def content_match(p):
 if p.suffix.lower() not in TEXT or p.stat().st_size>10_000_000:return False
 try:return any(t in p.read_text(encoding='utf-8',errors='ignore').casefold() for t in TERMS)
 except OSError:return False
def main():
 candidates=[]; refs=[]
 for p in PROJECT.rglob('*'):
  if not p.is_file() or any(x in p.parts for x in ('.git','models','node_modules','vendor','__pycache__')):continue
  low=str(p.relative_to(PROJECT)).replace('\\','/').casefold()
  hit=any(t in low for t in TERMS) or content_match(p)
  if not hit:continue
  try:b=p.read_bytes()
  except OSError:continue
  n,ids,first,last=jsonl_meta(p,b)
  candidates.append({'absolute_project_path':str(p),'relative_path':str(p.relative_to(PROJECT)).replace('\\','/'),'file_size':len(b),'line_count':b.count(b'\n')+(1 if b and not b.endswith(b'\n') else 0),'case_count':n,'sha256_raw_bytes':digest(b),'sha256_normalized_lf':normlf(b),'sha256_semantic_content':semantic(b),'ids':ids,'first_id':first,'last_id':last,'mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),'referenced_by':[],'freeze_status_claimed':None})
 by_name={Path(c['relative_path']).name:c for c in candidates}; by_hash={c['sha256_raw_bytes']:c for c in candidates}
 # One bounded pass over likely reports/manifests; do not perform an O(candidates × project) scan.
 for p in PROJECT.rglob('*'):
  if not p.is_file() or p.suffix.lower() not in TEXT or p.stat().st_size>3_000_000:continue
  rel=str(p.relative_to(PROJECT)).replace('\\','/')
  if not any(x in rel.casefold() for x in ('evaluation/','experiments/','reports/','docs/')):continue
  try:s=p.read_text(encoding='utf-8',errors='ignore')
  except OSError:continue
  for name,c in by_name.items():
   if name in s and rel != c['relative_path']:c['referenced_by'].append(rel)
  for h,c in by_hash.items():
   if h in s and rel != c['relative_path']:c['referenced_by'].append(rel)
 for c in candidates:
  c['referenced_by']=sorted(set(c['referenced_by']))
  if 'dataset_freeze' in c['relative_path'] or 'freeze' in c['relative_path']:c['freeze_status_claimed']='DECLARED_IN_SOURCE'
 (OUT/'campus_heldout_50_forensic_inventory.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'candidates':candidates},ensure_ascii=False,indent=2),encoding='utf-8')
 historical='8194d0272a29fce8b5f97fea65c4efb47f96b0dc93b04f4a3da1865fa588582f'; matches=[c for c in candidates if c['sha256_raw_bytes']==historical]
 proof='evaluation/e2e_heldout/v1/audit/dataset_freeze.json lines 6-7 and 96: dataset_path is evaluation/e2e_heldout/v1/cases/e2e_50_cases.jsonl and dataset_sha256 is historical hash.'
 current=next((c for c in candidates if c['relative_path']=='evaluation/e2e_heldout/v1/cases/e2e_50_cases.jsonl'),None)
 prov={'historical_hash':historical,'historical_hash_target':'cases/e2e_50_cases.jsonl (as explicitly declared by the historical freeze manifest)','historical_path':'evaluation/e2e_heldout/v1/cases/e2e_50_cases.jsonl','hashing_method':'SHA-256 raw-byte method is implied by the manifest field and artifact map; no historical script documenting normalization/canonicalization was found.','evidence_source':proof,'current_matching_file':[x['relative_path'] for x in matches],'match_status':'CANONICAL_MATCH_FOUND' if matches else 'NO_PROJECT_FILE_WITH_HISTORICAL_RAW_HASH','current_candidate':current}
 (OUT/'campus_hash_provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
