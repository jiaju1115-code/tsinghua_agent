from __future__ import annotations
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
ROOT=Path(__file__).resolve().parents[1]
SOURCE=REPO/'experiments/router_v0_2/evaluation/router_blind_shadow_set.json'
PROTECTED=[
 REPO/'experiments/router_v0_2', REPO/'experiments/web_search_v0/src',
 REPO/'experiments/web_search_v0_followup/src', REPO/'evaluation/answer_generation/v0/config',
 REPO/'prompts', REPO/'data_first', REPO/'data_second'
]
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():
 out={}
 for base in PROTECTED:
  if base.exists():
   for p in sorted(x for x in base.rglob('*') if x.is_file() and '__pycache__' not in x.parts and 'cache' not in x.parts):
    out[str(p.relative_to(REPO)).replace('\\','/')]={'sha256':sha_file(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
 try: status=subprocess.run(['git','status','--porcelain=v1'],cwd=REPO,text=True,capture_output=True,check=False).stdout.splitlines()
 except Exception: status=[]
 return {'captured_at':datetime.now(timezone.utc).isoformat(),'files':out,'git_status':status}
def rank(row): return hashlib.sha256(f"{row['id']}||{row['query']}||e2e12_router_v0_2".encode()).hexdigest()
def main():
 for d in ['evaluation','results','logs','analysis','audit']: (ROOT/d).mkdir(parents=True,exist_ok=True)
 (ROOT/'audit/pre_run_state.json').write_text(json.dumps(snapshot(),ensure_ascii=False,indent=2),encoding='utf-8')
 rows=json.loads(SOURCE.read_text(encoding='utf-8'))
 selected=[]
 subjects=sorted({r['subject'] for r in rows if r['group']=='ACADEMIC'})
 for subject in subjects: selected.append(min((r for r in rows if r.get('subject')==subject),key=rank))
 selected += sorted((r for r in rows if r['group']=='CAMPUS'),key=rank)[:2]
 selected += sorted((r for r in rows if r['group']=='GENERAL_CURRENT'),key=rank)[:2]
 selected += sorted((r for r in rows if r['group']=='NO_WEB_GENERAL'),key=rank)[:2]
 normalized=[]
 for r in selected:
  category='ACADEMIC' if r['group']=='ACADEMIC' else ('CAMPUS' if r['group']=='CAMPUS' else ('GENERAL' if r['group']=='GENERAL_CURRENT' else 'HARD_NEGATIVE'))
  normalized.append({'sample_id':r['id'],'query':r['query'],'expected_route':r['expected_mode'],'category':category,'academic_subject':r.get('subject'),'selection_sha256':rank(r)})
 payload={'set_name':'E2E12_ROUTER_V0_2_FROZEN','samples':normalized}
 set_hash=hashlib.sha256(canonical(payload)).hexdigest()
 (ROOT/'evaluation/e2e12_set.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 manifest={'status':'FROZEN','creation_time':datetime.now(timezone.utc).isoformat(),'source_dataset':str(SOURCE),'source_dataset_sha256':sha_file(SOURCE),'selection_method':'sha256(stable_id || query || e2e12_router_v0_2), ascending within required stratum','sample_ids':[r['sample_id'] for r in normalized],'samples':normalized,'canonical_json_sha256':set_hash,'git_commit':subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,text=True,capture_output=True).stdout.strip() or None,'working_tree_status':'recorded in pre_run_state.json'}
 (ROOT/'audit/e2e12_freeze.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'count':len(normalized),'subjects':subjects,'ids':manifest['sample_ids'],'sha256':set_hash},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
