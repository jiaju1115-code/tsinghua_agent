from pathlib import Path
import json, random, hashlib, statistics, re
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'data/fine_tuning_v1/general_capability_candidates_v1_2'
PKG=ROOT/'experiments/fine_tuning_pilot_v0_upload'
TRAIN=PKG/'data/train.jsonl'; VALID=PKG/'data/validation.jsonl'
SEED=42
def read_pool():
    rows=[]
    for p in SRC.glob('*.jsonl'):
        if p.name=='general_family_registry.jsonl': continue
        rows += [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
    return rows
def msg(x):
    return {'messages':[{'role':'user','content':x.get('instruction','') + (('\n'+x.get('input','')) if x.get('input') else '')},{'role':'assistant','content':x.get('answer','')}], 'metadata':{'task_family':x.get('task_family'),'source_id':x.get('source_row_id'),'source':x.get('source_dataset'),'original_id':x.get('case_id'),'family_id':x.get('family_id')}}
def main():
    rows=read_pool(); ids=[x.get('case_id') for x in rows]; assert len(rows)==841 and len(set(ids))==len(ids), 'POOL_DISCREPANCY'
    by={};
    for x in rows: by.setdefault(x['task_family'],[]).append(x)
    rng=random.Random(SEED); tr=[]; va=[]
    for fam,xs in sorted(by.items()):
        rng.shuffle(xs); n=max(1,round(len(xs)*.1));
        if len(xs)==1: n=0
        va += xs[:n]; tr += xs[n:]
    TRAIN.parent.mkdir(parents=True,exist_ok=True); TRAIN.write_text(''.join(json.dumps(msg(x),ensure_ascii=False)+'\n' for x in tr),encoding='utf-8'); VALID.write_text(''.join(json.dumps(msg(x),ensure_ascii=False)+'\n' for x in va),encoding='utf-8')
    dist=lambda xs:{f:sum(x['task_family']==f for x in xs) for f in sorted(by)}
    manifest={'dataset_version':'general_capability_candidates_v1_2','input_count':len(rows),'train_count':len(tr),'validation_count':len(va),'task_family_distribution':{'input':dist(rows),'train':dist(tr),'validation':dist(va)},'split_seed':SEED,'split_algorithm_version':'family_stratified_random_v1','source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.glob('*.jsonl')},'generation_timestamp':'2026-08-16','test_created':False,'final_split':False}
    (PKG/'data/split_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8'); (PKG/'data/dataset_statistics.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest
if __name__=='__main__': print(json.dumps(main(),ensure_ascii=False,indent=2))
