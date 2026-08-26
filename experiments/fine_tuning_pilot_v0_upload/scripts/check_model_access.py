"""Preflight only: never downloads model weights."""
import argparse, json
from pathlib import Path
def main():
    p=argparse.ArgumentParser(); p.add_argument('--local-only',action='store_true'); a=p.parse_args(); model='Qwen/Qwen2.5-1.5B-Instruct'
    if a.local_only:
        from huggingface_hub import scan_cache_dir
        repos=[x.repo_id for x in scan_cache_dir().repos]
        ok=model in repos; print(json.dumps({'mode':'local_only','model':model,'available':ok,'weights_downloaded':False})); return 0 if ok else 2
    from huggingface_hub import HfApi, hf_hub_download
    info=HfApi().model_info(model); config=hf_hub_download(model,'config.json')
    print(json.dumps({'mode':'network_metadata_and_config','model':model,'revision':info.sha,'config_path':config,'weights_downloaded':False})); return 0
if __name__=='__main__': raise SystemExit(main())
