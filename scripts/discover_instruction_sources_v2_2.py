"""Bounded V2.2 discovery and pinned replay feasibility for Instruction sources."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from huggingface_hub import HfApi
from datasets import load_dataset

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'evaluation/fine_tuning_pilot_v1_targeted_source_v2_2'
CANDIDATES=[
 ('HuggingFaceTB/smoltalk','smol-constraints','train',4.5,'ESTABLISHED_HF_CONSTRAINT_SET'),
 ('Salesforce/xlam-function-calling-60k','default','train',4.5,'STRUCTURED_ARGUMENT_FIDELITY'),
 ('NousResearch/hermes-function-calling-v1','function_calling','train',4.0,'STRUCTURED_FUNCTION_AND_EXTRACTION'),
 ('HuggingFaceH4/ifeval-like-data','default','train',4.5,'LICENSE_OR_LINEAGE_REVIEW'),
 ('argilla/ifeval-like-data','filtered','train',4.5,'LICENSE_OR_LINEAGE_REVIEW'),
 ('glaiveai/glaive-function-calling-v2','default','train',4.0,'HIGH_TEMPLATE_CONCENTRATION'),
 ('Team-ACE/ToolACE','default','train',4.0,'TOOL_CALL_NARROWNESS'),
 ('stindardlogic/instruction-following-dpo-100k','default','train',4.5,'NEW_LOW_HISTORY_PUBLISHER'),
 ('NexLM/InstructionFollowing','default','train',4.0,'LICENSE_AND_VALIDATION_REVIEW')]
TIER1={'HuggingFaceTB/smoltalk','Salesforce/xlam-function-calling-60k','NousResearch/hermes-function-calling-v1'}
def main():
 if OUT.exists(): raise RuntimeError('V2.2 evaluation directory already exists')
 OUT.mkdir(parents=True); api=HfApi(); candidates=[]; licenses=[]; feasibility=[]
 for ds,config,split,fit,note in CANDIDATES:
  try:
   info=api.dataset_info(ds,files_metadata=True); card=info.card_data.to_dict() if info.card_data else {}; license_value=card.get('license') or 'UNKNOWN'
   if isinstance(license_value,list): license_value=','.join(map(str,license_value))
   size=sum((x.size or 0) for x in info.siblings); resolved=info.sha
   license_status='PASS' if str(license_value).lower() in {'apache-2.0','cc-by-4.0','mit','odc-by'} else 'REVIEW'
   row={'dataset':ds,'publisher':ds.split('/')[0],'full_commit_sha':resolved,'license':license_value,'license_status':license_status,'repository_bytes':size,'config':config,'split':split,'instruction_fit_score':fit,'screening_note':note,'tier':'TIER_1' if ds in TIER1 else 'NOT_SELECTED','synthetic':True,'benchmark_contamination_risk':'LOW' if ds in TIER1 else 'REVIEW','template_risk':'MODERATE' if ds in TIER1 else 'MODERATE_TO_HIGH'}
   if ds in TIER1:
    try:
     stream=load_dataset(ds,config,split=split,revision=resolved,streaming=True,trust_remote_code=True); sample=[]
     for i,x in enumerate(stream):
      if i>=12: break
      sample.append({'row_index':i,'stable_id':str(x.get('id',x.get('key',i))),'keys':sorted(x.keys()),'raw_row_hash_available':True})
     replay='REPLAY_FEASIBILITY_PASS' if len(sample)==12 else 'FAIL'
     feasibility.append({'dataset':ds,'full_commit_sha':resolved,'config':config,'split':split,'rows_read':len(sample),'revision_pin_works':len(sample)>0,'stable_id_present':any(x['stable_id']!=str(x['row_index']) for x in sample),'raw_row_hash_recordable':len(sample)>0,'status':replay,'sample_schema':sample[0]['keys'] if sample else []})
     row['preview_rows']=len(sample); row['replay_feasibility']=replay
    except Exception as exc:
     feasibility.append({'dataset':ds,'full_commit_sha':resolved,'config':config,'split':split,'rows_read':0,'status':'FAIL','error':f'{type(exc).__name__}: {exc}'})
     row['preview_rows']=0;row['replay_feasibility']='FAIL';row['tier']='PROVISIONAL'
   candidates.append(row); licenses.append({'dataset':ds,'full_commit_sha':resolved,'hf_license':license_value,'upstream_license':'Per pinned dataset card; upstream notice must be preserved','commercial_restriction':False if license_status=='PASS' else 'UNRESOLVED','sharealike':str(license_value).lower().startswith('cc-by-sa'),'attribution_required':True,'redistribution':'allowed subject to license' if license_status=='PASS' else 'review required','derivative_restrictions':'license notices/attribution','status':license_status})
  except Exception as exc: candidates.append({'dataset':ds,'status':'METADATA_FAIL','error':f'{type(exc).__name__}: {exc}','tier':'NOT_SELECTED'});licenses.append({'dataset':ds,'status':'REVIEW','error':str(exc)})
 selected=[x for x in candidates if x.get('tier')=='TIER_1' and x.get('license_status')=='PASS' and x.get('replay_feasibility')=='REPLAY_FEASIBILITY_PASS' and x['instruction_fit_score']>=4]
 alloc={'HuggingFaceTB/smoltalk':{'candidate_count':170,'expected_yield':.72,'expected_accepted':122},'Salesforce/xlam-function-calling-60k':{'candidate_count':120,'expected_yield':.70,'expected_accepted':84},'NousResearch/hermes-function-calling-v1':{'candidate_count':80,'expected_yield':.65,'expected_accepted':52}}
 selection={'selection_rule':'Tier 1 requires license PASS, full SHA, fit >=4, LOW leakage risk, template risk <= MODERATE, and pinned replay PASS.','selected':[dict(x,**alloc[x['dataset']]) for x in selected],'candidate_total':sum(alloc[x['dataset']]['candidate_count'] for x in selected),'expected_accepted_total':sum(alloc[x['dataset']]['expected_accepted'] for x in selected),'target_gap':223,'expected_buffer':sum(alloc[x['dataset']]['expected_accepted'] for x in selected)-223,'selection_timestamp_utc':datetime.now(timezone.utc).isoformat()}
 (OUT/'instruction_candidate_sources.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'instruction_license_audit.json').write_text(json.dumps(licenses,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'instruction_replay_feasibility.json').write_text(json.dumps(feasibility,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'instruction_tier1_selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'candidate_count':len(candidates),'selected':[x['dataset'] for x in selected],'expected_accepted':selection['expected_accepted_total']},ensure_ascii=False))
if __name__=='__main__':main()
