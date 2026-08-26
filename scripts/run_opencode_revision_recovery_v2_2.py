"""Recover the 36 legacy-accepted OpenCode rows by stable ID at the frozen SHA."""
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from datasets import load_dataset
from huggingface_hub import hf_hub_url, get_hf_file_metadata

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'data/03_fine_tuning/pilot_v1/general_acquisition_v2'
OUT=ROOT/'data/03_fine_tuning/pilot_v1/opencode_revision_recovery_v2_2'
SHA='8f3ba5bafe4d6e8db46082cf7ae6741bc370604d'; DS='nvidia/OpenCodeInstruct'; FILE='data/train-00000-of-00050.parquet'
spec=importlib.util.spec_from_file_location('stage2',ROOT/'scripts/run_pilot_v1_general_acquisition_v2.py'); s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def h(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def nh(r): return h({k:r.get(k,'') for k in ('instruction','context','response')})
def read(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def emit(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(i,ensure_ascii=False,sort_keys=True)+'\n' for i in x),encoding='utf-8')
def main():
 if OUT.exists(): raise RuntimeError('OpenCode V2.2 output already exists')
 legacy=[x for x in read(OLD/'accepted_candidates.jsonl') if x['source_dataset']==DS]
 targets={str(x['source_row_id']):x for x in legacy}; url=hf_hub_url(DS,FILE,repo_type='dataset',revision=SHA); meta=get_hf_file_metadata(url)
 recovered=[]; mapping=[]
 for idx,row in enumerate(load_dataset('parquet',data_files={'train':url},split='train',streaming=True)):
  if not targets: break
  key=str(row['id'])
  if key not in targets:
   if idx>=89: break
   continue
  old=targets.pop(key); item={'row_idx':old['source_row_index'],'row':dict(row)}; rec=s.adapt(DS,old['source_config'],old['source_split'],old['family'],old['subfamily'],item)[0]
  raw_match=h(old['metadata']['raw_fields'])==h(rec['metadata']['raw_fields']); normalized_match=nh(old)==nh(rec); status='EXACT_RAW_MATCH' if raw_match else ('NORMALIZED_CONTENT_MATCH' if normalized_match else 'CONTENT_MISMATCH')
  material='\x1f'.join([DS,SHA,rec['source_config'],rec['source_split'],key,s.norm(rec['instruction'])]); vid=hashlib.sha256(material.encode()).hexdigest(); new_status='REJECT' if s.quality(rec) else 'ACCEPT'
  rec.update({'legacy_candidate_id':old['candidate_id'],'revision_verified_candidate_id':vid,'source_revision':SHA,'match_status':status,'old_status':'ACCEPT','new_status':new_status,'status_match':new_status=='ACCEPT','source_file':FILE,'source_file_etag':meta.etag,'source_file_size':meta.size,'pinned_raw_hash':h(rec['metadata']['raw_fields']),'pinned_normalized_hash':nh(rec)})
  mapping.append({'legacy_candidate_id':old['candidate_id'],'matched':status in ('EXACT_RAW_MATCH','NORMALIZED_CONTENT_MATCH'),'source_file':FILE,'source_row':idx,'source_id':key,'commit':SHA,'raw_hash':h(rec['metadata']['raw_fields']),'normalized_hash':nh(rec),'match_status':status,'quality_status':new_status,'revision_verified_candidate_id':vid}); recovered.append(rec)
 for old in targets.values(): mapping.append({'legacy_candidate_id':old['candidate_id'],'matched':False,'source_file':FILE,'source_row':None,'source_id':old['source_row_id'],'commit':SHA,'raw_hash':None,'normalized_hash':None,'match_status':'SOURCE_ROW_NOT_FOUND','quality_status':None})
 verified=[x for x in recovered if x['match_status'] in ('EXACT_RAW_MATCH','NORMALIZED_CONTENT_MATCH') and x['new_status']=='ACCEPT']
 # Recheck General V0.1 with frozen Stage 2 lexical threshold.
 _,evals=s.frozen_texts(); leaked=[]
 for x in verified:
  score=max((s.lexical(x['instruction']+' '+x['context'],e) for e in evals),default=0)
  if score>=.55: leaked.append(x['legacy_candidate_id'])
 verified=[x for x in verified if x['legacy_candidate_id'] not in set(leaked)]
 emit(OUT/'opencode_legacy_to_verified.jsonl',mapping);emit(OUT/'opencode_revision_verified_accepted.jsonl',verified)
 report={'dataset':DS,'commit_sha':SHA,'source_file':FILE,'source_file_etag':meta.etag,'legacy_accepted':len(legacy),'recovered':len(verified),'failed':len(legacy)-len(verified),'exact_raw_match':sum(x['match_status']=='EXACT_RAW_MATCH' for x in mapping),'normalized_content_match':sum(x['match_status']=='NORMALIZED_CONTENT_MATCH' for x in mapping),'accepted_leakage':len(leaked),'recovery_status':'OPENCODE_RECOVERY_SUCCESS' if len(verified)>=29 else ('OPENCODE_RECOVERY_PARTIAL' if verified else 'OPENCODE_RECOVERY_FAILED')}
 (OUT/'opencode_recovery_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
