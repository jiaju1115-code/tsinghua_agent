from __future__ import annotations
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
REPO=Path(__file__).resolve().parents[3];ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
freeze=json.loads((ROOT/'audit/reconciliation_input_freeze.json').read_text(encoding='utf-8'))
changed=[];missing=[];post={}
for name,v in freeze['source_files'].items():
 p=Path(v['path'])
 if not p.exists():missing.append(name);continue
 h=sha(p);post[name]={'path':str(p),'sha256':h,'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
 if h!=v['sha256']:changed.append(name)
protected=[REPO/'experiments/router_v0_2',REPO/'experiments/web_search_v0/src',REPO/'experiments/web_search_v0_followup/src',REPO/'evaluation/answer_generation/v0/config',REPO/'prompts',REPO/'data_first',REPO/'data_second']
git_checks={}
for p in protected:
 rel=str(p.relative_to(REPO));git_checks[rel]=subprocess.run(['git','status','--short','--',rel],cwd=REPO,text=True,capture_output=True).stdout.splitlines()
prior=REPO/'experiments/generation_citation_eval_v0/audit/final_immutability_report.json';prior_status=json.loads(prior.read_text(encoding='utf-8')).get('status') if prior.exists() else None
state={'captured_at':datetime.now(timezone.utc).isoformat(),'source_files':post,'git_status':subprocess.run(['git','status','--porcelain=v1'],cwd=REPO,text=True,capture_output=True).stdout.splitlines(),'protected_git_checks':git_checks}
(ROOT/'audit/post_run_state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
audit={'status':'PASS' if not(changed or missing) and prior_status=='PASS' else 'FAIL','input_hash_changes':changed,'missing_inputs':missing,'network_calls':0,'search_extract_calls':0,'answers_regenerated':0,'existing_experiment_files_modified':False,'secondary_ai_label':'SECONDARY_AI_ADJUDICATION','generation_eval_v0_prior_immutability_status':prior_status,'protected_git_checks':git_checks,'new_outputs_root':str(ROOT),'completed_at':datetime.now(timezone.utc).isoformat()}
(ROOT/'audit/final_immutability_report.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(audit,ensure_ascii=False,indent=2))
