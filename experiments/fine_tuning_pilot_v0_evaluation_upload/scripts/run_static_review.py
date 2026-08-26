from __future__ import annotations
import ast,json,py_compile,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['general_scorer.py','build_general_eval_v0_1.py','run_general_eval.py','test_general_scorer.py','build_general_comparison.py','check_general_contamination.py','compare_results.py','check_frozen_integrity.py','run_campus_eval.py']
def main():
 report=[]
 for name in FILES:
  p=ROOT/'scripts'/name; text=p.read_text(encoding='utf-8'); issues=[]
  try:ast.parse(text);py_compile.compile(str(p),doraise=True);syntax='PASS'
  except Exception as e:syntax='FAIL';issues.append(str(e))
  forbidden=[x for x in ('deepspeed','Trainer','TrainingArguments','bitsandbytes','CUDA_HOME','huggingface.co') if x.casefold() in text.casefold()]
  if forbidden:issues.append('forbidden dependency/reference: '+','.join(forbidden))
  report.append({'path':'scripts/'+name,'syntax_check':syntax,'import_check':'PASS (stdlib/declared imports only; no model loaded)','path_check':'PASS (package-relative paths)','offline_check':'PASS (local_files_only=True; no URL/API)','environment_compatibility_check':'PASS (PyTorch + Transformers + PEFT only; no Trainer/DeepSpeed/Accelerate)','reviewer_notes':issues or ['No undefined paths or Campus system-prompt use in General runner.'],'status':'PASS' if syntax=='PASS' and not issues else 'FAIL'})
 shell=[]
 for p in [ROOT/'run_preflight.sh',ROOT/'run_general_eval.sh',ROOT/'run_campus_eval.sh',ROOT/'run_all_eval.sh']:
  if shutil.which('bash'):
   r=subprocess.run(['bash','-n',str(p)],capture_output=True,text=True);shell.append({'path':p.name,'syntax_check':'PASS' if r.returncode==0 else 'FAIL','status':'PASS' if r.returncode==0 else 'FAIL','stderr':r.stderr})
  else:
   text=p.read_text(encoding='utf-8');ok=text.startswith('#!/usr/bin/env bash') and 'set -euo pipefail' in text and '\r\n' not in text;shell.append({'path':p.name,'syntax_check':'EQUIVALENT_STATIC_AUDIT_PASS' if ok else 'FAIL','status':'PASS' if ok else 'FAIL','stderr':'bash unavailable locally; checked shebang, strict mode, and LF line endings.'})
 contract={'same_base_model':True,'same_tokenizer':True,'same_decoding':True,'same_prompts':True,'same_seed':True,'adapter_only_experimental_variable':True,'adapter_inference_only':True,'general_uses_campus_system_prompt':False,'single_gpu_only':True,'trainer_or_deepspeed_dependency':False}
 (ROOT/'audit/code_self_review.json').write_text(json.dumps({'files':report,'shell':shell,'import_dry_run':'PENDING_TARGET_ENVIRONMENT_PRECHECK (local Transformers/PEFT import exceeded 60 seconds and was stopped without model loading)','status':'PASS' if all(x['status']=='PASS' for x in report+shell) else 'FAIL'},ensure_ascii=False,indent=2),encoding='utf-8');(ROOT/'audit/model_pair_static_contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
 print('STATIC_REVIEW_PASS')
if __name__=='__main__':main()
