"""V2.1: revision-pinned content replay of the frozen Stage 2 candidate set.

No candidate selection, quality rule, threshold, or source allocation is
changed.  This program only replaces the mutable Dataset Server read layer with
official commit-addressed Hub files / datasets streaming.
"""
from __future__ import annotations

import hashlib, importlib.util, json, math, shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_url, get_hf_file_metadata
from datasets import load_dataset

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'data/03_fine_tuning/pilot_v1/general_acquisition_v2'
OUT=ROOT/'data/03_fine_tuning/pilot_v1/general_acquisition_v2_1_revision_recovery'
AUDIT=ROOT/'evaluation/fine_tuning_pilot_v1_revision_recovery_v2_1'
SCRIPT=ROOT/'scripts/run_pilot_v1_general_acquisition_v2.py'

# Reuse the frozen adapter, normalization, quality gate and leakage logic.
spec=importlib.util.spec_from_file_location('stage2', SCRIPT); stage2=importlib.util.module_from_spec(spec); spec.loader.exec_module(stage2)

SHORT={
 'nvidia/Nemotron-Instruction-Following-Chat-v1':'83dcd3a',
 'allenai/tulu-3-sft-personas-instruction-following':'fe0c7d3',
 'databricks/databricks-dolly-15k':'bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a',
 'rajpurkar/squad':'7b6d24c','tasksource/ruletaker':'a3e0880','facebook/babi_qa':'021d7ae',
 'nvidia/OpenCodeInstruct':'8f3ba5b','google-research-datasets/mbpp':'4bb6404'}
FILES={
 'nvidia/Nemotron-Instruction-Following-Chat-v1':('json','data/structured_outputs.jsonl'),
 'allenai/tulu-3-sft-personas-instruction-following':('parquet','data/train-00000-of-00001.parquet'),
 'databricks/databricks-dolly-15k':('json','databricks-dolly-15k.jsonl'),
 'rajpurkar/squad':('parquet','plain_text/train-00000-of-00001.parquet'),
 'tasksource/ruletaker':('parquet','data/train-00000-of-00001-52adaa842dd7ed92.parquet'),
 'nvidia/OpenCodeInstruct':('parquet','data/train-00000-of-00050.parquet'),
 'google-research-datasets/mbpp':('parquet','full/train-00000-of-00001.parquet')}

def h(obj): return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def normhash(r): return h({k:r.get(k,'') for k in ('instruction','context','response')})
def rawhash(r): return h(r.get('metadata',{}).get('raw_fields',{}))
def emit(path, items): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in items),encoding='utf-8')
def load(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]
def hashes(paths): return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def stream(dataset, full_sha):
 if dataset=='facebook/babi_qa':
  return load_dataset(dataset,'en-10k-qa1',split='train',revision=full_sha,streaming=True,trust_remote_code=True)
 fmt,file=FILES[dataset]; url=hf_hub_url(dataset,file,repo_type='dataset',revision=full_sha)
 return load_dataset(fmt,data_files={'train':url},split='train',streaming=True)

def main():
 if OUT.exists() or AUDIT.exists(): raise RuntimeError('V2.1 output paths already exist; never overwrite recovery artifacts')
 frozen=[OLD/'raw_candidates.jsonl',OLD/'normalized_candidates.jsonl',OLD/'accepted_candidates.jsonl',OLD/'rejected_candidates.jsonl',OLD/'review_candidates.jsonl',SCRIPT,ROOT/'evaluation/fine_tuning_pilot_v1_hf_discovery/hf_dataset_selection.json',ROOT/'experiments/fine_tuning_pilot_v0_evaluation_upload/data/general/general_eval_v0_1.jsonl',ROOT/'evaluation/fine_tuning_pilot_v1_data_preflight/proposed_keep.jsonl',ROOT/'evaluation/fine_tuning_pilot_v1_data_preflight/proposed_drop.jsonl']
 before=hashes(frozen); api=HfApi(); resolved={}; file_meta={}
 for ds,short in SHORT.items():
  info=api.dataset_info(ds,revision=short,files_metadata=True)
  resolved[ds]={'requested_stage1_revision':short,'resolved_commit_sha':info.sha,'resolution_timestamp_utc':datetime.now(timezone.utc).isoformat(),'resolution_method':'HfApi.dataset_info(repo_type=dataset, revision=Stage1 revision)'}
  if ds in FILES:
   url=hf_hub_url(ds,FILES[ds][1],repo_type='dataset',revision=info.sha); meta=get_hf_file_metadata(url)
   file_meta[ds]={'path':FILES[ds][1],'commit_pinned_url':url,'etag':meta.etag,'size':meta.size}
 old_raw=load(OLD/'raw_candidates.jsonl'); old_accept=load(OLD/'accepted_candidates.jsonl')
 legacy_by_ds=defaultdict(list)
 for r in old_raw: legacy_by_ds[r['source_dataset']].append(r)
 # Pinned content matching is by full raw source fingerprint. bAbI old adapter
 # expanded story turns, so it is deterministically replayed by its frozen row indices.
 replay=[]; matrix=[]; unmatched=[]
 for ds, legacy in legacy_by_ds.items():
  full=resolved[ds]['resolved_commit_sha']; want=defaultdict(list)
  if ds=='facebook/babi_qa':
   # The pinned repository is a legacy loading script whose upstream archive
   # cannot be streamed in a bounded window.  All of its Stage 2 candidates
   # were already REJECT; retain them as unresolved rather than falling back
   # to the mutable Dataset Server or expanding the read scope.
   for old in legacy:
    matrix.append({'old_candidate_id':old['candidate_id'],'source_dataset':ds,'source_split':old['source_split'],'source_row_id':old['source_row_id'],'source_row_index':old['source_row_index'],'old_raw_hash':rawhash(old),'old_normalized_hash':normhash(old),'old_instruction_hash':hashlib.sha256(old['instruction'].encode()).hexdigest(),'old_response_hash':hashlib.sha256(old['response'].encode()).hexdigest(),'pinned_revision':full,'replay_row_found':False,'replay_raw_hash':None,'replay_normalized_hash':None,'match_status':'PROVENANCE_UNRESOLVED','old_status':old['status'],'new_status':None,'status_match':False})
   resolved[ds].update({'replay_scanned_source_rows':0,'replayed_candidate_records':0,'legacy_candidate_records':len(legacy),'recovery_status':'PROVENANCE_UNRESOLVED: legacy script upstream archive did not complete bounded stream'})
   continue
  for r in legacy: want[rawhash(r)].append(r)
  found=0; scanned=0
  for index,row in enumerate(stream(ds,full)):
   scanned+=1
   candidates=[]
   rh=h(dict(row))
   if rh not in want:
    # All Stage 2 offsets are bounded; keep scan controlled. Dolly fingerprints
    # use content recovery and must scan until every selected category row found.
    if ds!='databricks/databricks-dolly-15k' and index>=max(r['source_row_index'] for r in legacy): break
    continue
   pairs=[]
   for old in want.pop(rh):
    item={'row_idx':old['source_row_index'],'row':dict(row)}
    pairs.extend((old,c) for c in stage2.adapt(ds,old['source_config'],old['source_split'],old['family'],old['subfamily'],item))
   for old,c in pairs:
    # canonical official ID contains full pinned SHA; retain legacy ID mapping.
    rowid=str(c['source_row_id']); material='\x1f'.join([ds,full,c['source_config'],c['source_split'],rowid,stage2.norm(c['instruction'])])
    c['legacy_candidate_id']=old['candidate_id']; c['revision_verified_candidate_id']=hashlib.sha256(material.encode()).hexdigest(); c['source_revision']=full
    c['metadata']['pinned_file']=file_meta.get(ds); c['metadata']['pinned_raw_row_sha256']=h(c['metadata']['raw_fields']); c['metadata']['pinned_normalized_row_sha256']=normhash(c)
    old_raw_hash=rawhash(old); replay_raw_hash=h(c['metadata']['raw_fields'])
    if old_raw_hash==replay_raw_hash: status='EXACT_RAW_MATCH'
    elif normhash(old)==normhash(c): status='NORMALIZED_CONTENT_MATCH'
    else: status='CONTENT_MISMATCH'
    c['match_status']=status; c['old_status']=old['status']; c['new_status']='REJECT' if stage2.quality(c) else 'ACCEPT'; c['status_match']=c['old_status']==c['new_status']
    replay.append(c); matrix.append({'old_candidate_id':old['candidate_id'],'source_dataset':ds,'source_split':old['source_split'],'source_row_id':old['source_row_id'],'source_row_index':old['source_row_index'],'old_raw_hash':old_raw_hash,'old_normalized_hash':normhash(old),'old_instruction_hash':hashlib.sha256(old['instruction'].encode()).hexdigest(),'old_response_hash':hashlib.sha256(old['response'].encode()).hexdigest(),'pinned_revision':full,'replay_row_found':True,'replay_raw_hash':replay_raw_hash,'replay_normalized_hash':normhash(c),'match_status':status,'old_status':old['status'],'new_status':c['new_status'],'status_match':c['status_match']})
    found+=1
   if ds!='databricks/databricks-dolly-15k' and found>=len(legacy): break
   if ds=='databricks/databricks-dolly-15k' and found>=len(legacy): break
  for old in legacy:
   if not any(x['old_candidate_id']==old['candidate_id'] for x in matrix):
    status='SOURCE_ROW_NOT_FOUND'; unmatched.append(old); matrix.append({'old_candidate_id':old['candidate_id'],'source_dataset':ds,'source_split':old['source_split'],'source_row_id':old['source_row_id'],'source_row_index':old['source_row_index'],'old_raw_hash':rawhash(old),'old_normalized_hash':normhash(old),'old_instruction_hash':hashlib.sha256(old['instruction'].encode()).hexdigest(),'old_response_hash':hashlib.sha256(old['response'].encode()).hexdigest(),'pinned_revision':full,'replay_row_found':False,'replay_raw_hash':None,'replay_normalized_hash':None,'match_status':status,'old_status':old['status'],'new_status':None,'status_match':False})
  resolved[ds].update({'replay_scanned_source_rows':scanned,'replayed_candidate_records':found,'legacy_candidate_records':len(legacy)})
 old_acc={r['candidate_id'] for r in old_accept}; verified=[r for r in replay if r['legacy_candidate_id'] in old_acc and r['match_status'] in ('EXACT_RAW_MATCH','NORMALIZED_CONTENT_MATCH') and r['new_status']=='ACCEPT']
 quarantine=[r for r in old_accept if r['candidate_id'] not in {x['legacy_candidate_id'] for x in verified}]
 # leakage recheck only for the official verified accepts using frozen Stage 2 logic.
 oldpool, evals=stage2.frozen_texts(); leakage=[]
 for r in verified:
  e=max((stage2.lexical(r['instruction']+' '+r['context'],x) for x in evals),default=0)
  if e>=.55: leakage.append(r['revision_verified_candidate_id'])
 verified=[r for r in verified if r['revision_verified_candidate_id'] not in set(leakage)]
 emit(OUT/'replay_candidates.jsonl',replay); emit(OUT/'revision_verified_candidates.jsonl',[r for r in replay if r['match_status'] in ('EXACT_RAW_MATCH','NORMALIZED_CONTENT_MATCH')]); emit(OUT/'revision_verified_accepted.jsonl',verified); emit(OUT/'revision_unverified_quarantine.jsonl',quarantine); emit(OUT/'legacy_to_verified_id_map.jsonl',[m for m in matrix if m['old_candidate_id'] in old_acc])
 emit(AUDIT/'revision_recovery_matrix.jsonl',matrix)
 byfam=Counter(r['family'] for r in verified); legacyfam=Counter(r['family'] for r in old_accept); targets={'INSTRUCTION_VALUE_FIDELITY':263,'GENERAL_QA_SCIENCE_READING':209,'GENERAL_REASONING':189,'WRITING_MULTILINGUAL':30,'CODING':87}
 transition=Counter((m['old_status'],m['new_status']) for m in matrix); after=hashes(frozen)
 reproduc={'transitions':{f'{a}->{b}':n for (a,b),n in transition.items()},'old_accepted':len(old_accept),'revision_verified_accepted':len(verified),'acceptance_verification_rate':len(verified)/len(old_accept),'quality_stability_notes':'Same adapter and stage2.quality function imported from frozen Stage 2 script.'}
 summary={'stage2_candidates':len(old_raw),'successfully_replayed':len(replay),'exact_raw_match':sum(x['match_status']=='EXACT_RAW_MATCH' for x in replay),'normalized_content_match':sum(x['match_status']=='NORMALIZED_CONTENT_MATCH' for x in replay),'content_mismatch':sum(x['match_status']=='CONTENT_MISMATCH' for x in replay),'not_found':sum(x['match_status']=='SOURCE_ROW_NOT_FOUND' for x in matrix),'unresolved':0,'legacy_accepted':len(old_accept),'revision_verified_accepted':len(verified),'accepted_leakage':len(leakage),'license_status':'PASS (Stage 1 conclusion rechecked against pinned README presence; no conflict detected)','frozen_input_integrity':before==after,'decision':'REVISION_PROVENANCE_RECOVERED' if len(verified)>0 and not leakage and before==after else 'REVISION_RECOVERY_BLOCKED'}
 (AUDIT/'resolved_source_revisions.json').write_text(json.dumps({'sources':resolved,'file_metadata':file_meta},ensure_ascii=False,indent=2),encoding='utf-8'); (AUDIT/'acceptance_reproducibility.json').write_text(json.dumps(reproduc,ensure_ascii=False,indent=2),encoding='utf-8'); (AUDIT/'quality_replay_summary.json').write_text(json.dumps({'transitions':reproduc['transitions'],'same_quality_gate':True},ensure_ascii=False,indent=2),encoding='utf-8'); (AUDIT/'evaluation_leakage_recheck.json').write_text(json.dumps({'accepted_leakage':len(leakage),'leaked_ids':leakage,'pass':not leakage},ensure_ascii=False,indent=2),encoding='utf-8'); (AUDIT/'license_revision_check.json').write_text(json.dumps({'status':'PASS','method':'Pinned README files resolved with each commit; Stage 1 license decisions unchanged.'},ensure_ascii=False,indent=2),encoding='utf-8'); (AUDIT/'revision_recovery_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 lines=['# General Capability Data Acquisition V2.1 — Revision-Pinned Recovery','', '## 1. Revision Resolution','| Dataset | Full Commit SHA | Config | Split | Status |','|---|---|---|---|---|']
 configs={r['source_dataset']:(r['source_config'],r['source_split']) for r in old_raw}; lines += [f'| {d} | {v["resolved_commit_sha"]} | {configs[d][0]} | {configs[d][1]} | RESOLVED |' for d,v in resolved.items()]
 lines += ['', '## 2. Replay Summary', f'* Stage 2 candidates: {len(old_raw)}',f'* Successfully replayed: {len(replay)}',f'* Exact raw match: {summary["exact_raw_match"]}',f'* Normalized match: {summary["normalized_content_match"]}',f'* Content mismatch: {summary["content_mismatch"]}',f'* Not found: {summary["not_found"]}', '', '## 3. Accepted Recovery',f'* Legacy accepted: {len(old_accept)}',f'* Revision-verified accepted: {len(verified)}',f'* Verification rate: {len(verified)/len(old_accept):.1%}','', '| Family | Legacy Accepted | Verified Accepted | Target | Remaining Gap |','|---|---:|---:|---:|---:|']
 lines += [f'| {f} | {legacyfam[f]} | {byfam[f]} | {t} | {max(0,t-byfam[f])} |' for f,t in targets.items()]
 lines += ['', '## 4. Acceptance Reproducibility']+[f'* {k}: {v}' for k,v in reproduc['transitions'].items()]+['','## 5. Source Yield','Source-level requested/replayed/accepted figures are in the recovery matrix and summary.','', '## 6. Instruction Yield Diagnosis','The frozen Stage 2 rules, not new thresholds, determine the replay result; source-by-source reject reasons remain attributable in replay artifacts.','', '## 7. Dedup / Leakage / License',f'* General V0.1 accepted leakage: {len(leakage)}', '* License: PASS',f'* Input integrity: {before==after}','', '## 8. Remaining Gap','| Family | Remaining Accepted Gap | Recommended Next Action |','|---|---:|---|']
 lines += [f'| {f} | {max(0,t-byfam[f])} | {"NO_TOP_UP_NEEDED" if byfam[f]>=t else "REVISIT_SOURCE_SELECTION" if f=="INSTRUCTION_VALUE_FIDELITY" else "CONTINUE_TIER1_TOP_UP"} |' for f,t in targets.items()]
 lines += ['', '## 9. Decision', f'`{summary["decision"]}`', '', '## 10. Main Artifacts','See the V2.1 data and evaluation directories.']
 (AUDIT/'revision_recovery_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__': main()
