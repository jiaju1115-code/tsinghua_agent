from __future__ import annotations
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]; ROOT=Path(__file__).resolve().parents[1]
SRC=REPO/'experiments/generation_citation_eval_v0'; RES=SRC/'results'
FILES={
 'generation_case_matrix':RES/'generation_case_matrix.json',
 'generation_metrics':RES/'generation_metrics.json',
 'human_review_queue':RES/'human_review_queue.csv',
 'independent_review_packet':RES/'independent_review_packet.xlsx',
 'independent_review_packet_adjudicated':RES/'independent_review_packet_adjudicated.xlsx',
 'claim_level_audit':RES/'claim_level_audit.json',
 'completeness_matrix':RES/'completeness_matrix.csv',
 'generation_eval_freeze':SRC/'audit/generation_eval_freeze.json',
 'e2e12_freeze':REPO/'experiments/e2e12_router_v0_2/audit/e2e12_freeze.json'
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():
 return {str(p.relative_to(REPO)).replace('\\','/'):{'sha256':sha(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in FILES.values() if p.exists()}
def main():
 for d in ['inputs','results','analysis','audit']: (ROOT/d).mkdir(parents=True,exist_ok=True)
 missing=[k for k,p in FILES.items() if not p.exists()]
 if missing: raise SystemExit('MISSING_INPUTS:'+','.join(missing))
 state={'captured_at':datetime.now(timezone.utc).isoformat(),'files':snapshot(),'git_status':subprocess.run(['git','status','--porcelain=v1'],cwd=REPO,text=True,capture_output=True).stdout.splitlines()}
 (ROOT/'audit/pre_run_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
 gen=json.loads(FILES['generation_eval_freeze'].read_text(encoding='utf-8'));e2e=json.loads(FILES['e2e12_freeze'].read_text(encoding='utf-8'))
 freeze={'status':'FROZEN','creation_time':datetime.now(timezone.utc).isoformat(),'source_files':{k:{'path':str(p),'sha256':sha(p),'size':p.stat().st_size} for k,p in FILES.items()},'generation_eval_v0_freeze_hash':gen.get('canonical_manifest_sha256'),'e2e12_freeze_hash':e2e.get('canonical_json_sha256'),'git_status':state['git_status'],'working_tree_status':'recorded in pre_run_state.json'}
 (ROOT/'audit/reconciliation_input_freeze.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'missing':missing,'files':len(FILES),'generation_freeze':freeze['generation_eval_v0_freeze_hash'],'e2e12_freeze':freeze['e2e12_freeze_hash']},ensure_ascii=False))
if __name__=='__main__':main()
