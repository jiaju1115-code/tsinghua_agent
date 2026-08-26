from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--base-model-path',required=True);p.add_argument('--adapter-path',required=True);a=p.parse_args()
 ap=Path(a.adapter_path); cfg=ap/'adapter_config.json'; weights=ap/'adapter_model.safetensors'; errors=[]
 if not cfg.exists() or not weights.exists(): errors.append('adapter_config.json and adapter_model.safetensors are both required')
 d=json.loads(cfg.read_text(encoding='utf-8')) if cfg.exists() else {}
 expected={'r':16,'lora_alpha':32,'lora_dropout':0.05}; errors += [f'adapter {k} mismatch' for k,v in expected.items() if d.get(k)!=v]
 if sorted(d.get('target_modules',[])) != sorted(['q_proj','k_proj','v_proj','o_proj']): errors.append('target modules mismatch')
 if d.get('inference_mode') is not True: errors.append('adapter is not in inference mode')
 digest=sha(weights) if weights.exists() else None
 expected=json.loads((ROOT/'config/experiment_manifest.json').read_text(encoding='utf-8'))['expected_adapter_sha256']
 if digest != expected: errors.append('adapter SHA-256 does not match the archived Pilot V0 final artifact')
 result={'status':'PASS' if not errors else 'FAIL','adapter_sha256':digest,'expected_adapter_sha256':expected,'adapter_config':d,'base_model_path':a.base_model_path,'trainable_parameters_at_evaluation':0,'errors':errors}
 (ROOT/'results'/'model_pair_check.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(result,ensure_ascii=False));sys.exit(bool(errors))
if __name__=='__main__':main()
