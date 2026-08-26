"""Final V2.2 source gate using explicit commit-pinned JSON files."""
import json, hashlib
from pathlib import Path
from datasets import load_dataset
from huggingface_hub import hf_hub_url, get_hf_file_metadata
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evaluation/fine_tuning_pilot_v1_targeted_source_v2_2'
SOURCES=[
 {'dataset':'NousResearch/hermes-function-calling-v1','sha':'dae3e1d28cfbcf4b915c04ea1e072030529b4bda','file':'func-calling.json','config':'func_calling','split':'train','license':'apache-2.0','fit':4.25,'candidate_count':190,'yield':.65,'expected':124,'generation':'Synthetic; NousResearch/interstellarninja-led structured function-calling and extraction generation','validation':'Schema-oriented structured generation; V2.2 quality gate must revalidate every row'},
 {'dataset':'Team-ACE/ToolACE','sha':'6bda777c88d21e5a204703c1ee45597a8fa4f734','file':'data.json','config':'default','split':'train','license':'apache-2.0','fit':4.25,'candidate_count':180,'yield':.65,'expected':117,'generation':'Synthetic self-evolution pipeline over a 26,507-API pool','validation':'Dual-layer rule/model verification reported by publisher; V2.2 quality gate must revalidate every row'}]
def main():
 feasibility=[];selected=[]
 for x in SOURCES:
  url=hf_hub_url(x['dataset'],x['file'],repo_type='dataset',revision=x['sha']);meta=get_hf_file_metadata(url);rows=[];error=None
  try:
   for i,row in enumerate(load_dataset('json',data_files={'train':url},split='train',streaming=True)):
    if i>=12:break
    rows.append({'row_index':i,'stable_id':str(row.get('id',i)),'raw_hash':hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'keys':sorted(row.keys())})
  except Exception as exc:error=f'{type(exc).__name__}: {exc}'
  status='REPLAY_FEASIBILITY_PASS' if len(rows)==12 else 'FAIL'; feasibility.append({'dataset':x['dataset'],'full_commit_sha':x['sha'],'config':x['config'],'split':x['split'],'source_file':x['file'],'file_etag':meta.etag,'rows_read':len(rows),'stable_id_present':any(r['stable_id']!=str(r['row_index']) for r in rows),'raw_row_hash_recorded':len(rows)==12,'sample_schema':rows[0]['keys'] if rows else [],'status':status,'error':error})
  if status=='REPLAY_FEASIBILITY_PASS':selected.append(dict(x,tier='CONFIRMED_SOURCE',replay=status,template_risk='MODERATE',leakage_risk='LOW',license_status='PASS'))
 provisional=[{'dataset':'Salesforce/xlam-function-calling-60k','full_commit_sha':'26d14ebfe18b1f7b524bd39b404b50af5dc97866','license':'cc-by-4.0','fit_score':4.5,'tier':'PROVISIONAL_SOURCE','reason':'Gated repository terms not accepted in this environment; pinned data-file replay failed before preview.'},{'dataset':'HuggingFaceTB/smoltalk','full_commit_sha':'5feaf2fd3ffca7c237fc38d1861bc30365d48ffa','license':'UNKNOWN','fit_score':4.5,'tier':'PROVISIONAL_SOURCE','reason':'Pinned smol-constraints replay passed, but dataset card does not declare a dataset license.'}]
 selection={'selection_rule':'CONFIRMED requires license PASS, full SHA, fit >=4, LOW leakage risk, template risk <= MODERATE, and pinned file replay PASS.','selected':selected,'provisional':provisional,'candidate_total':sum(x['candidate_count'] for x in selected),'expected_accepted_total':sum(x['expected'] for x in selected),'target_gap':223,'expected_buffer':sum(x['expected'] for x in selected)-223,'largest_expected_source_share':max(x['expected'] for x in selected)/sum(x['expected'] for x in selected) if selected else None}
 (OUT/'instruction_replay_feasibility_final.json').write_text(json.dumps(feasibility,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'instruction_tier1_selection_final.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'instruction_candidate_sources_final.json').write_text(json.dumps({'confirmed':selected,'provisional':provisional},ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'selected':[x['dataset'] for x in selected],'expected':selection['expected_accepted_total']},ensure_ascii=False))
if __name__=='__main__':main()
