"""Build the V0.3 seen calibration corpus. No network or model calls."""
from __future__ import annotations
import csv,hashlib,json,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; EXP=ROOT.parent; REPO=ROOT.parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon_ev(ev):
 if isinstance(ev,str):
  try:ev=json.loads(ev)
  except:ev=[]
 return ev
def norm(q):return re.sub(r'\W','',q or '').lower()
def pair_hash(q,ev):return hashlib.sha256((norm(q)+'||'+json.dumps(ev,ensure_ascii=False,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 for d in ['dataset','candidates','results','analysis','audit','scripts']:(ROOT/d).mkdir(parents=True,exist_ok=True)
 old17=load(EXP/'evidence_sufficiency_v0_1/development/adjudicated_development_set.json')+load(EXP/'evidence_sufficiency_v0_1/evaluation/adjudicated_holdout.json')
 new32=load(EXP/'evidence_sufficiency_v0_2/development/real_development_set.json')+load(EXP/'evidence_sufficiency_v0_2/evaluation/real_internal_holdout.json')
 syn2=load(EXP/'evidence_benchmark_expansion_v0_2/synthetic/synthetic_stress_set_v0_2.json');syn1=load(EXP/'evidence_sufficiency_v0_1/evaluation/synthetic_stress_set.json')
 rows=[]
 for source,data,kind in [('ADJUDICATED_17',old17,'REAL_ADJUDICATED'),('ADJUDICATED_32',new32,'REAL_ADJUDICATED'),('SYNTHETIC_V0_2',syn2,'SYNTHETIC_CONSTRUCTED'),('LEGACY_SYNTHETIC_V0_1',syn1,'SYNTHETIC_CONSTRUCTED')]:
  for r in data:
   ev=canon_ev(r.get('frozen_evidence',[]));label=r.get('label') or r.get('expected_gate')
   rows.append({'record_id':f'{source}::{r["sample_id"]}','sample_id':r['sample_id'],'query':r['query'],'frozen_evidence':ev,'label':label,'data_kind':kind,'source_dataset':source,'category':r.get('category',''),'academic_subject':r.get('academic_subject',''),'construction_type':r.get('construction_type','REAL'),'source_query_id':r.get('source_query_id') or r.get('source_sample_id',''),'transformation':r.get('transformation',''),'prior_usage':'SEEN_CALIBRATION','normalized_query':norm(r['query']),'query_evidence_sha256':pair_hash(r['query'],ev)})
 bypair=defaultdict(list);byq=defaultdict(list)
 for r in rows:bypair[r['query_evidence_sha256']].append(r['record_id']);byq[r['normalized_query']].append(r['record_id'])
 for r in rows:
  r['exact_pair_duplicate_count']=len(bypair[r['query_evidence_sha256']]);r['normalized_query_overlap_count']=len(byq[r['normalized_query']]);r['duplicate_status']='EXACT_PAIR_DUPLICATE' if r['exact_pair_duplicate_count']>1 else ('QUERY_OVERLAP' if r['normalized_query_overlap_count']>1 else 'UNIQUE')
 # Collapse duplicates only within the same evaluation kind. Cross-kind copies (notably
 # SUFFICIENT_CONTROL identities) remain explicitly marked and are reported separately.
 unique=[];seen=set()
 for r in rows:
  key=(r['data_kind'],r['query_evidence_sha256'])
  if key in seen:continue
  seen.add(key);unique.append(r)
 dump(ROOT/'dataset/unified_calibration_dataset.json',unique)
 fields=[k for k in unique[0] if k!='frozen_evidence']+['frozen_evidence']
 with (ROOT/'dataset/unified_calibration_dataset.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in unique:w.writerow({**r,'frozen_evidence':json.dumps(r['frozen_evidence'],ensure_ascii=False)})
 real=[r for r in unique if r['data_kind']=='REAL_ADJUDICATED'];syn=[r for r in unique if r['data_kind']=='SYNTHETIC_CONSTRUCTED']
 overlap={'raw_rows':len(rows),'unique_rows':len(unique),'duplicates_removed':len(rows)-len(unique),'exact_duplicate_groups':sum(len(v)>1 for v in bypair.values()),'normalized_query_overlap_groups':sum(len(v)>1 for v in byq.values()),'real_count':len(real),'real_labels':dict(Counter(r['label'] for r in real)),'synthetic_unique_count':len(syn),'synthetic_types':dict(Counter(r['construction_type'] for r in syn))}
 (ROOT/'analysis/calibration_dataset_overlap.md').write_text(f"# Calibration dataset overlap\n\nRaw rows: {overlap['raw_rows']}; unique Query+Evidence rows: {overlap['unique_rows']}; exact duplicates removed: {overlap['duplicates_removed']}; exact-pair duplicate groups: {overlap['exact_duplicate_groups']}; normalized-query overlap groups: {overlap['normalized_query_overlap_groups']}.\n\nReal adjudicated and synthetic metrics are always reported separately. Real labels: {overlap['real_labels']}. Synthetic types: {overlap['synthetic_types']}.\n",encoding='utf-8')
 inputs=[EXP/'generation_citation_eval_v0/results/independent_review_packet_adjudicated.xlsx',EXP/'evidence_benchmark_expansion_v0_2/adjudication/new_real_adjudication_packet_adjudicated.xlsx',EXP/'evidence_benchmark_expansion_v0_2/synthetic/synthetic_stress_set_v0_2.json',EXP/'evidence_sufficiency_v0_1/evaluation/synthetic_stress_set.json']
 dump(ROOT/'audit/input_freeze.json',{'timestamp':datetime.now(timezone.utc).isoformat(),'inputs':{str(p):sha(p) for p in inputs},'unified_dataset_sha256':sha(ROOT/'dataset/unified_calibration_dataset.json'),'all_samples_status':'SEEN_CALIBRATION','offline_calls':{'search':0,'tavily':0,'extract':0,'external_llm':0,'answer_generation':0}})
 print(json.dumps(overlap,ensure_ascii=False))
if __name__=='__main__':main()
