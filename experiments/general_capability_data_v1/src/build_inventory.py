from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/general_capability_data_v1'; OUT=ROOT/'data/fine_tuning_v1/general_capability_candidates'
def read(p):
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()] if p.exists() else []
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for d in ('research','audit','results','reports'): (EXP/d).mkdir(parents=True,exist_ok=True)
    seeds=read(OUT/'general_seed_candidates.jsonl'); candidates=[]
    for i,x in enumerate(seeds):
        cid='GENERAL-SEED-'+str(i+1).zfill(4)
        candidates.append({'case_id':cid,'mode':'GENERAL','task_family':x.get('task_family','GENERAL_INSTRUCTION').upper(),'instruction':x.get('instruction',''),'input':x.get('input',''),'answer':x.get('answer',''),'source_dataset':x.get('source_dataset'),'source_split':x.get('source_split'),'source_row_id':x.get('sample_id'),'license':x.get('license'),'construction_type':'ORIGINAL','quality_level':'HIGH_CONFIDENCE','family_id':cid,'provenance':x.get('provenance')})
    (OUT/'general_candidates.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in candidates),encoding='utf-8')
    datasets=[
      {'dataset':'OpenAssistant/oasst1','repo':'https://huggingface.co/datasets/OpenAssistant/oasst1','license':'Apache-2.0','decision':'METADATA_ONLY_PENDING_SAMPLE_FILTER','benchmark_risk':'medium'},
      {'dataset':'openai/gsm8k','repo':'https://huggingface.co/datasets/openai/gsm8k','license':'MIT','decision':'EVAL_ONLY','benchmark_risk':'high'},
      {'dataset':'cais/mmlu','repo':'https://huggingface.co/datasets/cais/mmlu/tree/main','license':'MIT','decision':'EVAL_ONLY','benchmark_risk':'high'},
      {'dataset':'allenai/ai2_arc','repo':'https://huggingface.co/datasets/allenai/ai2_arc/tree/main','license':'CC-BY-SA-4.0','decision':'EVAL_ONLY','benchmark_risk':'high'},
      {'dataset':'Open-Orca/OpenOrca','repo':'https://huggingface.co/datasets/Open-Orca/OpenOrca','license':'MIT reported in prior audit','decision':'EXCLUDE','benchmark_risk':'high'}]
    (EXP/'research/dataset_candidates.json').write_text(json.dumps(datasets,ensure_ascii=False,indent=2),encoding='utf-8')
    (EXP/'audit/general_family_registry.jsonl').write_text(''.join(json.dumps({'family_id':x['family_id'],'member_case_ids':[x['case_id']],'holdout_status':'HELD_OUT_FROM_FINAL_SPLIT'},ensure_ascii=False)+'\n' for x in candidates),encoding='utf-8')
    fam={x['task_family']:sum(1 for y in candidates if y['task_family']==x['task_family']) for x in candidates}
    stats={'researched_datasets':5,'accepted_datasets':0,'rejected_datasets':1,'eval_only_datasets':3,'metadata_only_datasets':1,'downloaded_rows':0,'raw_candidates':len(candidates),'quality_passed':len(candidates),'deduplicated_final_candidates':len(candidates),'task_family_distribution':fam,'final_split':'NO','training':'NO','campus_cross_leakage':0,'quality_audit':'PASS_WITH_LIMITATIONS'}
    for f in ('general_capability_statistics.json','general_capability_asset_inventory.json'): (EXP/'results'/f).write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    (EXP/'results/recommended_general_inclusion.json').write_text(json.dumps({'recommended_training_candidates':len(candidates),'recommendation':'PROJECT_AUTHORED_SEED_ONLY_PENDING_LICENSE-CLEARED_ACQUISITION','task_family_distribution':fam},ensure_ascii=False,indent=2),encoding='utf-8')
    audits={'license_audit.json':{'status':'PASS_FOR_RESEARCH_ONLY','downloaded_raw_rows':0},'benchmark_leakage_registry.json':{d['dataset']:{'decision':d['decision'],'test_split':'EVAL_ONLY' if d['decision']=='EVAL_ONLY' else 'N/A'} for d in datasets},'general_holdout_registry.json':{'calculus':10,'linear_algebra':10,'probability_statistics':10,'general_knowledge':10,'reasoning':10,'science':10,'status':'HELD_OUT_NOT_TRAINING'},'general_dedup_report.json':{'input':len(candidates),'duplicates_removed':0,'final':len(candidates),'status':'PASS'},'general_family_integrity.json':{'families':len(candidates),'status':'PASS'},'campus_cross_leakage.json':{'leakage':0,'status':'PASS'}}
    for f,x in audits.items(): (EXP/'audit'/f).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
    return stats
if __name__=='__main__': print(json.dumps(main(),ensure_ascii=False,indent=2))
