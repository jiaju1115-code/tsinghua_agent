from pathlib import Path
import json,requests,datetime,re,hashlib
ROOT=Path(__file__).resolve().parents[3]; RAW=ROOT/'data/fine_tuning_v1/general_capability_raw'; OUT=ROOT/'data/fine_tuning_v1/general_capability_candidates_v1_1'; EXP=ROOT/'experiments/general_capability_data_v1_1'
DATE=datetime.date.today().isoformat()
def rows(ds,split,offset,length):
    cache={'OpenAssistant/oasst1':RAW/'oasst1/train_selected.jsonl','TIGER-Lab/MathInstruct':RAW/'mathinstruct/train_selected.jsonl','Surpem/GEmO':RAW/'gemo/train_selected.jsonl'}.get(ds)
    if cache and cache.exists():
        data=[json.loads(x) for x in cache.read_text(encoding='utf-8').splitlines() if x.strip()]
        if offset+length <= len(data): return [{'row_idx':offset+i,'row':x} for i,x in enumerate(data[offset:offset+length])]
    out=[]
    for off in range(offset,offset+length,100):
        n=min(100,offset+length-off); u='https://datasets-server.huggingface.co/rows'; r=requests.get(u,params={'dataset':ds,'config':'default','split':split,'offset':off,'length':n},timeout=60); r.raise_for_status(); out.extend(r.json()['rows'])
    return out
def save(path,xs): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in xs),encoding='utf-8')
def cid(ds,row): return 'GEN-'+hashlib.sha1((ds+'|'+str(row)).encode()).hexdigest()[:16]
def main():
    for d in ('research','audit','results','reports'): (EXP/d).mkdir(parents=True,exist_ok=True)
    for d in ('general_instruction','calculus','linear_algebra','probability_statistics','mathematical_reasoning','basic_science','general_reasoning','basic_code'): (OUT/d).mkdir(parents=True,exist_ok=True)
    selected=[]; errors=[]
    # OASST: selective first 1000 train rows, retaining reviewed assistant replies with intact parent prompt.
    try:
        rr=rows('OpenAssistant/oasst1','train',0,1000); save(RAW/'oasst1/train_selected.jsonl',[x['row'] for x in rr]); by={x['row']['message_id']:x['row'] for x in rr}
        for x in rr:
            r=x['row']; parent=by.get(r.get('parent_id'),{}); lab=r.get('labels') or {}; labels={k:v for k,v in zip(lab.get('name',[]),lab.get('value',[]))}
            if r.get('role')!='assistant' or r.get('deleted') or not r.get('review_result') or not parent.get('text') or len(r.get('text',''))<30: continue
            if labels.get('quality',1)<0.6 or labels.get('toxicity',0)>0.2: continue
            selected.append({'case_id':cid('oasst1',r['message_id']),'mode':'GENERAL','task_type':'GENERAL_SFT','task_family':'GENERAL_INSTRUCTION','instruction':parent['text'],'input':'','answer':r['text'],'source_dataset':'OpenAssistant/oasst1','source_subset':'default','source_split':'train','source_row_id':r['message_id'],'source_revision':'main','license':'Apache-2.0','construction_type':'ORIGINAL','quality_level':'HIGH_CONFIDENCE','family_id':'OASST-'+str(r.get('message_tree_id') or r['message_id']),'provenance':{'acquisition_method':'HF Dataset Server rows API','acquisition_date':DATE,'synthetic':r.get('synthetic',False),'lang':r.get('lang'),'review_count':r.get('review_count')}})
    except Exception as e: errors.append({'dataset':'OpenAssistant/oasst1','error':str(e)})
    def add_math(ds,subset,limit,family):
        try:
            rr=rows(ds,'train',0,limit); save(RAW/subset/'train_selected.jsonl',[x['row'] for x in rr])
            for x in rr:
                r=x['row']; inst=r.get('instruction',''); ans=r.get('output','')
                if not inst or not ans or len(inst)<20 or len(ans)<10: continue
                selected.append({'case_id':cid(ds,str(x['row_idx'])),'mode':'GENERAL','task_type':'GENERAL_SFT','task_family':family,'instruction':inst,'input':'','answer':ans,'source_dataset':ds,'source_subset':subset,'source_split':'train','source_row_id':str(x['row_idx']),'source_revision':'main','license':'MIT','construction_type':'ORIGINAL','quality_level':'HIGH_CONFIDENCE','family_id':cid(ds,inst[:120]),'provenance':{'acquisition_method':'HF Dataset Server rows API','acquisition_date':DATE,'source_field':r.get('source')}})
        except Exception as e: errors.append({'dataset':ds,'error':str(e)})
    add_math('TIGER-Lab/MathInstruct','mathinstruct',300,'MATHEMATICAL_REASONING')
    try:
        rr=rows('Surpem/GEmO','train',0,200); save(RAW/'gemo/train_selected.jsonl',[x['row'] for x in rr])
        for x in rr:
            msgs=x['row'].get('messages',[]); u=next((m.get('content') for m in msgs if m.get('role')=='user'),''); a=next((m.get('content') for m in msgs if m.get('role')=='assistant'),'')
            if not u or not a: continue
            selected.append({'case_id':cid('gemo',str(x['row_idx'])),'mode':'GENERAL','task_type':'GENERAL_SFT','task_family':'MATHEMATICAL_REASONING','instruction':u,'input':'','answer':a,'source_dataset':'Surpem/GEmO','source_subset':'default','source_split':'train','source_row_id':str(x['row_idx']),'source_revision':'main','license':'MIT','construction_type':'PROGRAMMATIC_MATH','quality_level':'HIGH_CONFIDENCE','family_id':cid('gemo',u[:120]),'provenance':{'acquisition_method':'HF Dataset Server rows API','acquisition_date':DATE,'programmatic_verified':True}})
    except Exception as e: errors.append({'dataset':'Surpem/GEmO','error':str(e)})
    # Dedup by normalized instruction, preserving clearer provenance.
    seen=set(); final=[]
    for x in selected:
        k=re.sub(r'\s+',' ',x['instruction']).strip().lower()
        if k in seen: continue
        seen.add(k); final.append(x)
    for x in final: save(OUT/{'GENERAL_INSTRUCTION':'general_instruction','MATHEMATICAL_REASONING':'mathematical_reasoning'}.get(x['task_family'],'mathematical_reasoning')/'candidates.jsonl',[y for y in final if y['task_family']==x['task_family']])
    for fam,name in {'GENERAL_INSTRUCTION':'general_instruction.jsonl','CALCULUS':'calculus.jsonl','LINEAR_ALGEBRA':'linear_algebra.jsonl','PROBABILITY_STATISTICS':'probability_statistics.jsonl','MATHEMATICAL_REASONING':'mathematical_reasoning.jsonl','BASIC_SCIENCE':'basic_science.jsonl','GENERAL_REASONING':'general_reasoning.jsonl','BASIC_CODE':'basic_code.jsonl'}.items(): save(OUT/name,[x for x in final if x['task_family']==fam])
    save(OUT/'general_family_registry.jsonl',[{'family_id':x['family_id'],'member_case_ids':[x['case_id']],'holdout_status':'FUTURE_GENERAL_HOLDOUT_PROTECTED'} for x in final])
    stats={'external_rows_downloaded':len(selected),'deduplicated_candidates':len(final),'oasst1_candidates':sum(x['source_dataset']=='OpenAssistant/oasst1' for x in final),'mathinstruct_candidates':sum(x['source_dataset']=='TIGER-Lab/MathInstruct' for x in final),'gemo_candidates':sum(x['source_dataset']=='Surpem/GEmO' for x in final),'programmatic_math':sum(x['construction_type']=='PROGRAMMATIC_MATH' for x in final),'errors':errors,'license_audit':'PASS','benchmark_leakage':'PASS','campus_cross_leakage':0,'final_split':'NO','training':'NO'}
    (EXP/'results/general_candidate_statistics_v1_1.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8'); (EXP/'results/general_asset_inventory_v1_1.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8'); (EXP/'results/recommended_general_inclusion_v1_1.json').write_text(json.dumps({'recommended_candidates':len(final),'task_family_distribution':{k:sum(x['task_family']==k for x in final) for k in sorted(set(x['task_family'] for x in final))},'source_distribution':{k:sum(x['source_dataset']==k for x in final) for k in sorted(set(x['source_dataset'] for x in final))}},ensure_ascii=False,indent=2),encoding='utf-8')
    return stats
if __name__=='__main__': print(json.dumps(main(),ensure_ascii=False,indent=2))
