from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(); p.add_argument('--base-model-path'); p.add_argument('--adapter-path'); a=p.parse_args()
    errors=[]
    if not a.base_model_path: errors.append('--base-model-path is required')
    if not a.adapter_path: errors.append('--adapter-path is required')
    if os.environ.get('HF_HUB_OFFLINE') != '1': errors.append('HF_HUB_OFFLINE must equal 1')
    if os.environ.get('TRANSFORMERS_OFFLINE') != '1': errors.append('TRANSFORMERS_OFFLINE must equal 1')
    for path, label in ((a.base_model_path,'base'), (a.adapter_path,'adapter')):
        if path and not Path(path).is_dir(): errors.append(f'{label} path does not exist: {path}')
    result={'status':'PASS' if not errors else 'FAIL','errors':errors,'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),'offline':True}
    out=ROOT/'results'/'preflight_environment.json'; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False)); sys.exit(bool(errors))
if __name__=='__main__': main()
