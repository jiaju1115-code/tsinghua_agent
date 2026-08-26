"""Stable-ID addendum for the two V2.1 sources whose server representation drifted."""
import hashlib, json, importlib.util
from pathlib import Path
from collections import Counter
from datasets import load_dataset
from huggingface_hub import hf_hub_url

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'data/03_fine_tuning/pilot_v1/general_acquisition_v2'
BASE=ROOT/'data/03_fine_tuning/pilot_v1/general_acquisition_v2_1_revision_recovery'
OUT=ROOT/'data/03_fine_tuning/pilot_v1/general_acquisition_v2_1_revision_recovery_stable_id_addendum'
AUDIT=ROOT/'evaluation/fine_tuning_pilot_v1_revision_recovery_v2_1_stable_id_addendum'
spec=importlib.util.spec_from_file_location('stage2',ROOT/'scripts/run_pilot_v1_general_acquisition_v2.py'); s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
SOURCES={
 'nvidia/Nemotron-Instruction-Following-Chat-v1':('83dcd3aded0d289b0bbc018d3f9af4c5dd4005df','json','data/structured_outputs.jsonl','uuid'),
 'nvidia/OpenCodeInstruct':('8f3ba5bafe4d6e8db46082cf7ae6741bc370604d','parquet','data/train-00000-of-00050.parquet','id')}
def h(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def nh(r): return h({k:r.get(k,'') for k in ('instruction','context','response')})
def read(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def emit(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(i,ensure_ascii=False,sort_keys=True)+'\n' for i in x),encoding='utf-8')
def main():
 if OUT.exists(): raise RuntimeError('addendum data path exists')
 AUDIT.mkdir(parents=True, exist_ok=True)
 old=read(OLD/'raw_candidates.jsonl'); accepted={x['candidate_id'] for x in read(OLD/'accepted_candidates.jsonl')}; existing={x['legacy_candidate_id'] for x in read(BASE/'revision_verified_candidates.jsonl')}
 additions=[]; mapping=[]
 for ds,(sha,fmt,file,idkey) in SOURCES.items():
  targets={x['source_row_id']:x for x in old if x['source_dataset']==ds and x['candidate_id'] not in existing}
  url=hf_hub_url(ds,file,repo_type='dataset',revision=sha); stream=load_dataset(fmt,data_files={'train':url},split='train',streaming=True)
  for idx,row in enumerate(stream):
   if not targets: break
   key=str(row[idkey])
   if key not in targets:
    if idx>=max(x['source_row_index'] for x in targets.values()): break
    continue
   legacy=targets.pop(key); item={'row_idx':legacy['source_row_index'],'row':dict(row)}
   rec=s.adapt(ds,legacy['source_config'],legacy['source_split'],legacy['family'],legacy['subfamily'],item)[0]
   raw_exact=h(legacy['metadata']['raw_fields'])==h(rec['metadata']['raw_fields'])
   normalized_exact=nh(legacy)==nh(rec)
   status='EXACT_RAW_MATCH' if raw_exact else ('NORMALIZED_CONTENT_MATCH' if normalized_exact else 'CONTENT_MISMATCH')
   material='\x1f'.join([ds,sha,rec['source_config'],rec['source_split'],key,s.norm(rec['instruction'])])
   rec.update({'legacy_candidate_id':legacy['candidate_id'],'revision_verified_candidate_id':hashlib.sha256(material.encode()).hexdigest(),'source_revision':sha,'match_status':status,'old_status':legacy['status'],'new_status':'REJECT' if s.quality(rec) else 'ACCEPT'})
   rec['status_match']=rec['old_status']==rec['new_status']; additions.append(rec)
   mapping.append({'old_candidate_id':legacy['candidate_id'],'revision_verified_candidate_id':rec['revision_verified_candidate_id'],'source_dataset':ds,'stable_row_identifier':key,'pinned_revision':sha,'match_status':status,'old_status':legacy['status'],'new_status':rec['new_status'],'status_match':rec['status_match']})
  for legacy in targets.values(): mapping.append({'old_candidate_id':legacy['candidate_id'],'source_dataset':ds,'stable_row_identifier':legacy['source_row_id'],'pinned_revision':sha,'match_status':'SOURCE_ROW_NOT_FOUND','old_status':legacy['status'],'new_status':None,'status_match':False})
 verified_add=[x for x in additions if x['match_status'] in ('EXACT_RAW_MATCH','NORMALIZED_CONTENT_MATCH') and x['new_status']=='ACCEPT' and x['legacy_candidate_id'] in accepted]
 base_verified=read(BASE/'revision_verified_accepted.jsonl'); combined=base_verified+verified_add
 emit(OUT/'stable_id_replay_candidates.jsonl',additions);emit(OUT/'stable_id_verified_accepted.jsonl',verified_add);emit(OUT/'combined_revision_verified_accepted.jsonl',combined);emit(OUT/'stable_id_legacy_map.jsonl',mapping)
 summary={'base_verified_accepted':len(base_verified),'stable_id_additional_verified_accepted':len(verified_add),'combined_verified_accepted':len(combined),'legacy_accepted':len(accepted),'verification_rate':len(combined)/len(accepted),'match_statuses':dict(Counter(x['match_status'] for x in mapping)),'transitions':dict(Counter(f"{x['old_status']}->{x['new_status']}" for x in mapping)),'accepted_leakage':0,'decision':'REVISION_PROVENANCE_RECOVERED' if len(combined)==len(accepted) else 'REVISION_RECOVERY_BLOCKED'}
 (AUDIT/'stable_id_recovery_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 (AUDIT/'stable_id_recovery_report.md').write_text('# Stable-ID recovery addendum\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':
 try:
  main()
 except Exception as exc:
  AUDIT.mkdir(parents=True, exist_ok=True)
  (AUDIT/'stable_id_recovery_failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc)},ensure_ascii=False,indent=2),encoding='utf-8')
  raise
