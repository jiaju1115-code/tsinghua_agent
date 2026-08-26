"""Canonicalize pinned Parquet metadata types, then replay the frozen OpenCode gate."""
import hashlib, importlib.util, json
from pathlib import Path
from datasets import load_dataset
from huggingface_hub import hf_hub_url, get_hf_file_metadata
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'data/03_fine_tuning/pilot_v1/general_acquisition_v2';OUT=ROOT/'data/03_fine_tuning/pilot_v1/opencode_revision_recovery_v2_2';DS='nvidia/OpenCodeInstruct';SHA='8f3ba5bafe4d6e8db46082cf7ae6741bc370604d';FILE='data/train-00000-of-00050.parquet'
sp=importlib.util.spec_from_file_location('s',ROOT/'scripts/run_pilot_v1_general_acquisition_v2.py');s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)
def read(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def emit(p,x):p.write_text(''.join(json.dumps(i,ensure_ascii=False,sort_keys=True)+'\n' for i in x),encoding='utf8')
def h(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def nh(r):return h({k:r.get(k,'') for k in ('instruction','context','response')})
def canonical(row):
 r=dict(row)
 for k in ('unit_tests','tests_execution_status'):
  if not isinstance(r.get(k),str):r[k]=json.dumps(r.get(k),ensure_ascii=False)
 if not isinstance(r.get('llm_judgement'),str):r['llm_judgement']=json.dumps(r.get('llm_judgement'),ensure_ascii=False)
 v=r.get('average_test_score')
 if isinstance(v,(int,float)):r['average_test_score']=str(int(v)) if float(v).is_integer() else str(v)
 return r
def main():
 final=OUT/'opencode_recovery_report_final.json'
 if final.exists():raise RuntimeError('final OpenCode recovery exists')
 old=[x for x in read(OLD/'accepted_candidates.jsonl') if x['source_dataset']==DS];targets={str(x['source_row_id']):x for x in old};url=hf_hub_url(DS,FILE,repo_type='dataset',revision=SHA);meta=get_hf_file_metadata(url);rows=[];maps=[]
 for idx,raw in enumerate(load_dataset('parquet',data_files={'train':url},split='train',streaming=True)):
  if not targets:break
  key=str(raw['id'])
  if key not in targets:
   if idx>=89:break
   continue
  legacy=targets.pop(key); pinned=dict(raw); rec=s.adapt(DS,legacy['source_config'],legacy['source_split'],legacy['family'],legacy['subfamily'],{'row_idx':legacy['source_row_index'],'row':canonical(pinned)})[0];match='EXACT_RAW_MATCH' if h(legacy['metadata']['raw_fields'])==h(rec['metadata']['raw_fields']) else ('NORMALIZED_CONTENT_MATCH' if nh(legacy)==nh(rec) else 'CONTENT_MISMATCH');reason=s.quality(rec);material='\x1f'.join([DS,SHA,rec['source_config'],rec['source_split'],key,s.norm(rec['instruction'])]);vid=hashlib.sha256(material.encode()).hexdigest();rec.update({'legacy_candidate_id':legacy['candidate_id'],'revision_verified_candidate_id':vid,'source_revision':SHA,'source_file':FILE,'source_row':idx,'pinned_raw_hash_before_io_canonicalization':h(pinned),'canonicalized_raw_hash':h(rec['metadata']['raw_fields']),'normalized_hash':nh(rec),'match_status':match,'quality_status':'ACCEPT' if reason is None else 'REJECT','quality_reason':reason});rows.append(rec);maps.append({'legacy_candidate_id':legacy['candidate_id'],'matched':match in ('EXACT_RAW_MATCH','NORMALIZED_CONTENT_MATCH'),'source_file':FILE,'source_row':idx,'source_id':key,'commit':SHA,'raw_hash':h(pinned),'normalized_hash':nh(rec),'match_status':match,'quality_status':rec['quality_status'],'quality_reason':reason,'revision_verified_candidate_id':vid})
 verified=[x for x in rows if x['match_status'] in ('EXACT_RAW_MATCH','NORMALIZED_CONTENT_MATCH') and x['quality_status']=='ACCEPT'];_,evals=s.frozen_texts();leaked=[x['legacy_candidate_id'] for x in verified if max((s.lexical(x['instruction']+' '+x['context'],e) for e in evals),default=0)>=.55];verified=[x for x in verified if x['legacy_candidate_id'] not in set(leaked)]
 emit(OUT/'opencode_legacy_to_verified_final.jsonl',maps);emit(OUT/'opencode_revision_verified_accepted_final.jsonl',verified);report={'dataset':DS,'commit_sha':SHA,'source_file':FILE,'source_file_etag':meta.etag,'legacy_accepted':len(old),'recovered':len(verified),'failed':len(old)-len(verified),'normalized_content_match':sum(x['match_status']=='NORMALIZED_CONTENT_MATCH' for x in maps),'accepted_leakage':len(leaked),'io_adapter_change':'Parquet list/numeric metadata deterministically serialized to the frozen Dataset Server string representation; quality rules unchanged.','recovery_status':'OPENCODE_RECOVERY_SUCCESS' if len(verified)>=29 else ('OPENCODE_RECOVERY_PARTIAL' if verified else 'OPENCODE_RECOVERY_FAILED')};final.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
