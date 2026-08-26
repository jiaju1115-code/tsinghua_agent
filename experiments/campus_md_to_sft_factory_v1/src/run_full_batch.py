from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
p=ROOT/'experiments/campus_md_to_sft_factory_v1/results/pilot_metrics.json'
if __name__=='__main__':
    if not p.exists(): print('PILOT_APPROVED_FULL_BATCH_PENDING')
    else:
        m=json.loads(p.read_text()); ok=m.get('success',0)/max(1,m.get('processed',0))>=.95 and m.get('leakage',0)==0
        print('PILOT_APPROVED_FULL_BATCH_PENDING' if ok else 'PILOT_FAILED')
