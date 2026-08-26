from pathlib import Path
import json, math, yaml
from family_sampler import EpochAwareFamilySampler
ROOT=Path(__file__).resolve().parents[1]
def main():
    cfg=yaml.safe_load((ROOT/'config/training_config.yaml').read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in (ROOT/'data/train.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    families=[x['metadata']['task_family'] for x in rows]
    sampler=EpochAwareFamilySampler(families,seed=cfg['seed'],mathematical_reasoning_ratio=cfg['sampling']['mathematical_reasoning_target_ratio'],num_samples=len(rows))
    list(sampler); list(sampler)
    batches=math.ceil(len(rows)/cfg['per_device_train_batch_size']); optimizer_steps_per_epoch=math.ceil(batches/cfg['gradient_accumulation_steps'])
    out={'config_parse':'PASS','train_count':len(rows),'epochs_simulated':2,'sampling_epochs':sampler.history,'optimizer_steps_per_epoch':optimizer_steps_per_epoch,'estimated_total_optimizer_steps':optimizer_steps_per_epoch*cfg['epochs'],'no_forward_backward_executed':True,'status':'PASS' if all(x['status']=='PASS' for x in sampler.history) else 'FAIL'}
    (ROOT/'audit').mkdir(exist_ok=True); (ROOT/'audit/sampling_dry_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))
    return 0 if out['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
