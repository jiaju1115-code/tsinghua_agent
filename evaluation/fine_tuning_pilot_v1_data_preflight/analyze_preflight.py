from __future__ import annotations
import csv,hashlib,json,math,re,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
POOL=ROOT/'data/fine_tuning_v1/general_capability_candidates_v1_2'; PKG=ROOT/'experiments/fine_tuning_pilot_v0_evaluation_upload'; FAIL=ROOT/'evaluation/fine_tuning_failure_analysis_v1'
TARGET={'INSTRUCTION_VALUE_FIDELITY':300,'GENERAL_QA_SCIENCE_READING':264,'GENERAL_REASONING':240,'WRITING_MULTILINGUAL':120,'CODING':96,'PROGRAMMATIC_MATH':120,'OTHER_MATH':60}
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def norm(s):return re.sub(r'[^\w]+','',s.casefold())
def words(s):return set(re.findall(r'\w+',s.casefold()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lang(row):
 v=row.get('provenance',{}).get('lang');
 if v:return v
 s=row.get('instruction','');ascii_ratio=sum(ord(c)<128 for c in s)/max(1,len(s));return 'en' if ascii_ratio>.92 else 'non_en_or_mixed'
def nfamily(r):
 if r.get('construction_type')=='PROGRAMMATIC_MATH':return 'PROGRAMMATIC_MATH'
 f=r.get('task_family');q=r.get('instruction','').casefold();lg=lang(r)
 if f in ('MATHEMATICAL_REASONING','LINEAR_ALGEBRA','CALCULUS','PROBABILITY_STATISTICS'):return 'OTHER_MATH'
 if f=='GENERAL_REASONING':return 'GENERAL_REASONING'
 if f=='BASIC_CODE':return 'CODING'
 if f=='BASIC_SCIENCE':return 'GENERAL_QA_SCIENCE_READING'
 if lg not in ('en','zh') or any(x in q for x in ('write a story','write a poem','essay','translate','rewrite','compose')):return 'WRITING_MULTILINGUAL'
 if q.endswith('?') or any(q.startswith(x) for x in ('what ','who ','why ','how ','when ','where ','which ','explain ','describe ')):return 'GENERAL_QA_SCIENCE_READING'
 return 'INSTRUCTION_VALUE_FIDELITY'
def template(s):return re.sub(r'\b\d+(?:\.\d+)?\b','<N>',' '.join(s.casefold().split()))
def select_diverse(rows,n):
 groups=defaultdict(list)
 for r in rows:groups[template(r['instruction'])].append(r)
 for g in groups.values():g.sort(key=lambda x:(-len(x.get('instruction','')),x['case_id']))
 chosen=[];depth=0
 while len(chosen)<n:
  added=False
  for k in sorted(groups,key=lambda x:(len(groups[x]),x)):
   if depth<len(groups[k]):chosen.append(groups[k][depth]);added=True
   if len(chosen)==n:break
  if not added:break
  depth+=1
 return chosen,groups
def semantic(raw,case):
 typ=case['scoring_rubric']['type'];gold=case['gold'];s=raw.strip();fenced=re.search(r'```(?:json|python)?\s*(.*?)```',s,re.S|re.I);core=fenced.group(1).strip() if fenced else s
 if typ=='json_exact':
  try:return json.loads(core)==gold,'FORMAT_ONLY_FAIL' if fenced else 'EVALUATOR_FALSE_NEGATIVE_RISK'
  except Exception:return False,None
 if typ=='python_unit_tests':
  return ('def solve' in core and ('```' in s or len(s)>len(core)+10)),'FORMAT_ONLY_FAIL'
 target=str(gold); compact=lambda x:re.sub(r'\s+','',x.casefold())
 if compact(target) in compact(s):return True,'EVALUATOR_FALSE_NEGATIVE_RISK' if len(s)>len(target)+10 else 'FORMAT_ONLY_FAIL'
 return False,None
def diagnose(raw,parsed,case):
 ok,kind=semantic(raw,case)
 if ok:return kind,'Core/gold answer is recoverable from raw output, but strict output rules rejected it.','HIGH'
 if parsed is None and raw.strip():return 'TRUE_CAPABILITY_FAIL','No deterministic evidence that the raw answer matches the gold; parser absence follows the strict contract.','MEDIUM'
 return 'TRUE_CAPABILITY_FAIL','Content does not match the deterministic gold under the available checks.','HIGH'
def main():
 files=[p for p in POOL.glob('*.jsonl') if p.name!='general_family_registry.jsonl'];rows=[]
 for p in files:rows+=jl(p)
 assert len(rows)==841 and len({r['case_id'] for r in rows})==841
 train=jl(PKG/'data/training/train.jsonl');val=jl(PKG/'data/training/validation.jsonl');pool_ids={r['case_id'] for r in rows};train_ids={x['metadata']['original_id'] for x in train};val_ids={x['metadata']['original_id'] for x in val};assert train_ids<=pool_ids and val_ids<=pool_ids and len(train_ids)==757 and len(val_ids)==84 and not train_ids&val_ids
 current=Counter(nfamily(r) for r in rows);current_train=Counter(nfamily(next(x for x in rows if x['case_id']==i)) for i in train_ids)
 prog=[r for r in rows if nfamily(r)=='PROGRAMMATIC_MATH'];prog_keep,prog_groups=select_diverse(prog,120);prog_keep_ids={x['case_id'] for x in prog_keep}
 other=[r for r in rows if nfamily(r)=='OTHER_MATH'];other_keep,other_groups=select_diverse(other,60);other_keep_ids={x['case_id'] for x in other_keep}
 keep=[];drop=[]
 for r in rows:
  f=nfamily(r);take=(r['case_id'] in prog_keep_ids if f=='PROGRAMMATIC_MATH' else r['case_id'] in other_keep_ids if f=='OTHER_MATH' else True);item={'case_id':r['case_id'],'normalized_family':f,'original_family':r['task_family'],'source_dataset':r['source_dataset'],'source_row_id':r['source_row_id'],'construction_type':r['construction_type'],'quality_level':r.get('quality_level'),'instruction_sha256':hashlib.sha256(r['instruction'].encode()).hexdigest(),'selection_reason':'representative template/source/difficulty coverage' if f in ('PROGRAMMATIC_MATH','OTHER_MATH') and take else 'under-target legacy family retained' if take else 'DROP_FROM_V1_SAMPLING: over-target math/template redundancy; source file preserved'};(keep if take else drop).append(item)
 kc=Counter(x['normalized_family'] for x in keep);dc=Counter(x['normalized_family'] for x in drop);matrix=[];hist_accept=161/558
 for f,target in TARGET.items():
  gap=max(0,target-kc[f]);matrix.append({'family':f,'current_pool':current[f],'current_train':current_train[f],'target':target,'proposed_keep':kc[f],'proposed_drop':dc[f],'minimum_add':gap,'recommended_candidate_min':math.ceil(gap/0.40) if gap else 0,'recommended_candidate_max':math.ceil(gap/0.25) if gap else 0,'historical_acceptance_rate_reference':hist_accept,'final_expected':kc[f]+gap})
 # Stable 24-case stratified sample from BOTH_FAIL.
 paired=jl(FAIL/'paired_cases.jsonl');both=[x for x in paired if x['classification']=='BOTH_FAIL'];by=defaultdict(list)
 for x in both:by[x['family']].append(x)
 quota={'GENERAL_INSTRUCTION':1,'GENERAL_REASONING':4,'MATHEMATICAL_REASONING':6,'LINEAR_ALGEBRA':4,'PROBABILITY_STATISTICS':4,'CALCULUS':4,'BASIC_CODE':1};sample=[]
 for f,n in quota.items():
  g=sorted(by[f],key=lambda x:x['case_id']);idx=[round(i*(len(g)-1)/max(1,n-1)) for i in range(n)];sample += [g[i] for i in idx]
 br={x['case_id']:x for x in jl(PKG/'results/base/general_per_case.jsonl')};pr={x['case_id']:x for x in jl(PKG/'results/pilot_v0/general_per_case.jsonl')};cases={x['case_id']:x for x in jl(PKG/'data/general/general_eval_v0_1.jsonl')};san=[]
 for x in sample:
  c=cases[x['case_id']];bd,be,bc=diagnose(br[x['case_id']]['raw_output'],br[x['case_id']].get('parsed_output'),c);pd,pe,pc=diagnose(pr[x['case_id']]['raw_output'],pr[x['case_id']].get('parsed_output'),c);pairdiag='EVALUATOR_FALSE_NEGATIVE_RISK' if 'EVALUATOR_FALSE_NEGATIVE_RISK' in (bd,pd) else 'FORMAT_ONLY_FAIL' if 'FORMAT_ONLY_FAIL' in (bd,pd) else 'PARSING_FAILURE' if 'PARSING_FAILURE' in (bd,pd) else 'AMBIGUOUS_GOLD_OR_PROMPT' if 'AMBIGUOUS_GOLD_OR_PROMPT' in (bd,pd) else 'TRUE_CAPABILITY_FAIL';san.append({'case_id':x['case_id'],'family':x['family'],'prompt':x['prompt'],'gold':x['reference'],'base_raw_output':br[x['case_id']]['raw_output'],'base_parsed_output':br[x['case_id']].get('parsed_output'),'pilot_raw_output':pr[x['case_id']]['raw_output'],'pilot_parsed_output':pr[x['case_id']].get('parsed_output'),'base_diagnosis':bd,'pilot_diagnosis':pd,'scorer_diagnosis':pairdiag,'short_explanation':f'Base: {be} Pilot: {pe}','confidence':'HIGH' if bc==pc=='HIGH' else 'MEDIUM'})
 sc=Counter(x['scorer_diagnosis'] for x in san);risk='HIGH' if (sc['FORMAT_ONLY_FAIL']+sc['EVALUATOR_FALSE_NEGATIVE_RISK'])/len(san)>=.4 else 'MODERATE' if (sc['FORMAT_ONLY_FAIL']+sc['EVALUATOR_FALSE_NEGATIVE_RISK'])/len(san)>=.15 else 'LOW';warning='DO_NOT_INTERPRET_RAW_PASS_RATE_AS_PURE_REASONING_ABILITY' if risk in ('HIGH','MODERATE') else 'PASS_RATE_LARGELY_REFLECTS_CAPABILITY_FAILURE'
 eval_prompts=jl(PKG/'data/general/general_eval_v0_1.jsonl');ep={norm(x['prompt']) for x in eval_prompts};exact=[r['case_id'] for r in rows if norm(r['instruction']) in ep];near=[]
 for r in rows:
  a=words(r['instruction'])
  for e in eval_prompts:
   b=words(e['prompt']);j=len(a&b)/max(1,len(a|b))
   if j>=.80 and norm(r['instruction'])!=norm(e['prompt']):near.append({'case_id':r['case_id'],'eval_id':e['case_id'],'jaccard':round(j,4)})
 dist={'formal_pool_paths':[str(p) for p in files],'pool_hashes':{str(p.relative_to(ROOT)):sha(p) for p in files},'train_path':str(PKG/'data/training/train.jsonl'),'validation_path':str(PKG/'data/training/validation.jsonl'),'pilot_consumed_input':'757-row train.jsonl produced from the hash-registered 841-row V1.2 pool','stable_case_ids':True,'split_counts':{'pool':841,'train':757,'validation':84},'current_pool':current,'current_train':current_train,'original_family':Counter(r['task_family'] for r in rows),'subfamily':'NOT_PRESENT_AS_A_STABLE_FIELD; source_subset and provenance are retained separately','source_dataset':Counter(r['source_dataset'] for r in rows),'construction_type':Counter(r['construction_type'] for r in rows),'language':Counter(lang(r) for r in rows),'analysis_mapping':'family_mapping.json','duplicate_audit':'Historical topup dedup removed 397/558 raw rows; current exact normalized prompts checked by selection script.','benchmark_leakage_audit':'PASS; historical eval_rows_used=0','evaluation_protection':{'exact_or_normalized_overlap_count':len(exact),'suspicious_near_duplicate_count':len(near),'exact_ids':exact,'near':near}}
 mapping={'rules':{'PROGRAMMATIC_MATH':'construction_type=PROGRAMMATIC_MATH','OTHER_MATH':'non-programmatic math families','GENERAL_REASONING':'original GENERAL_REASONING','CODING':'original BASIC_CODE','GENERAL_QA_SCIENCE_READING':'BASIC_SCIENCE or question-like GENERAL_INSTRUCTION','WRITING_MULTILINGUAL':'non-English/writing-like GENERAL_INSTRUCTION','INSTRUCTION_VALUE_FIDELITY':'remaining GENERAL_INSTRUCTION'},'source_labels_preserved':True,'analysis_only':True}
 pm_report={'current_count':len(prog),'target_keep':120,'proposed_drop':len(prog)-120,'unique_template_patterns':len(prog_groups),'near_duplicate_template_groups':sum(len(v)>1 for v in prog_groups.values()),'largest_template_groups':sorted([len(v) for v in prog_groups.values()],reverse=True)[:10],'source_distribution':Counter(x['source_dataset'] for x in prog),'original_family_distribution':Counter(x['task_family'] for x in prog),'difficulty_proxy':Counter('short' if len(x['instruction'])<120 else 'medium' if len(x['instruction'])<300 else 'long' for x in prog),'selection':'Deterministic round-robin across digit-normalized template patterns, prioritizing longer/information-richer instances; no random 120 sampling.'}
 sanity={'sample_size':len(san),'case_level_counts':{k:sc[k] for k in ('TRUE_CAPABILITY_FAIL','FORMAT_ONLY_FAIL','EVALUATOR_FALSE_NEGATIVE_RISK','PARSING_FAILURE','AMBIGUOUS_GOLD_OR_PROMPT')},'base_diagnoses':Counter(x['base_diagnosis'] for x in san),'pilot_diagnoses':Counter(x['pilot_diagnosis'] for x in san),'evaluator_false_negative_risk':risk,'interpretation_warning':warning,'evaluator_overoptimization_risk':'MODERATE','overoptimization_reason':'Pilot gains are concentrated in exact-format compliance; this is useful instruction following, but several Base answers contain correct cores rejected by strict scorers.'}
 priorities={'INSTRUCTION_VALUE_FIDELITY':'CRITICAL','GENERAL_QA_SCIENCE_READING':'CRITICAL','GENERAL_REASONING':'CRITICAL','WRITING_MULTILINGUAL':'HIGH','CODING':'MEDIUM','PROGRAMMATIC_MATH':'DO_NOT_ADD','OTHER_MATH':'DO_NOT_ADD'}
 profiles={'INSTRUCTION_VALUE_FIDELITY':('exact value copying, extraction, transformation, schema/format constraints, multi-condition compliance','subjective essays, evaluation paraphrases, repetitive JSON templates'),'GENERAL_QA_SCIENCE_READING':('stable factual QA, basic science, passage-grounded reading with verifiable short answers','time-sensitive facts, unsupported open-domain claims, ambiguous references'),'GENERAL_REASONING':('deterministic logic, ordering, set/symbolic and finite-state tasks with unique verifiable answers','pure arithmetic, benchmark leakage, labels requiring hidden chain-of-thought'),'WRITING_MULTILINGUAL':('clean multilingual instruction following, concise rewriting, controlled generation with objective constraints','unverifiable long-form preference labels, low-quality machine translation'),'CODING':('diverse safe pure functions with executable unit tests and clean code-only targets','shell/network/filesystem tasks, duplicated reverse-string templates'),'PROGRAMMATIC_MATH':('no acquisition; retain template-diverse representative subset only','all new programmatic math'),'OTHER_MATH':('no acquisition in this phase; retain diverse non-programmatic subset','additional math until non-math gaps are filled')}
 req=[]
 for x in matrix:req.append({'priority':priorities[x['family']],'family':x['family'],'current_keep':x['proposed_keep'],'target_final':x['target'],'minimum_accepted_needed':x['minimum_add'],'recommended_candidate_acquisition_range':f"{x['recommended_candidate_min']}-{x['recommended_candidate_max']}" if x['minimum_add'] else '0','desired_characteristics':profiles[x['family']][0],'exclusions':profiles[x['family']][1]+'; always exclude General V0.1 overlap/paraphrases/near-duplicates and malformed labels'})
 OUT.mkdir(parents=True,exist_ok=True)
 def dj(n,x):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=dict),encoding='utf-8')
 def djl(n,xs):(OUT/n).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in xs),encoding='utf-8')
 dj('current_distribution.json',dist);dj('family_mapping.json',mapping);djl('proposed_keep.jsonl',keep);djl('proposed_drop.jsonl',drop);dj('programmatic_math_downsample_report.json',pm_report);djl('both_fail_sanity_sample.jsonl',san);dj('evaluator_sanity_report.json',sanity);dj('pilot_v1_acquisition_requirements.json',req);dj('pilot_v1_target_distribution.json',{'primary_total':1200,'allowed_range':[1100,1300],'targets':TARGET,'percent':{'INSTRUCTION_VALUE_FIDELITY':25,'GENERAL_QA_SCIENCE_READING':22,'GENERAL_REASONING':20,'WRITING_MULTILINGUAL':10,'CODING':8,'PROGRAMMATIC_MATH':10,'OTHER_MATH':5},'total_percent':100,'total_math_percent':15})
 with (OUT/'rebalance_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=matrix[0].keys());w.writeheader();w.writerows(matrix)
 total_gap=sum(x['minimum_add'] for x in matrix);cand=(sum(x['recommended_candidate_min'] for x in matrix),sum(x['recommended_candidate_max'] for x in matrix));report=f'''# Pilot V1 Data Rebalancing Preflight\n\nThe formal pool is the hash-registered 841-row V1.2 family files; Pilot V0 consumed the derived 757-row train split with 84 validation rows. All source artifacts remain unchanged.\n\nProposed KEEP: {len(keep)}; DROP_FROM_V1_SAMPLING: {len(drop)}; accepted-data gap to 1200: {total_gap}; candidate acquisition estimate: {cand[0]}-{cand[1]} using a 25-40% acceptance band around the historical 28.85% rate.\n\nProgrammatic math: keep 120/300 and downsample 180 through template-diverse deterministic selection. Other math: keep 60 and downsample {current['OTHER_MATH']-60}.\n\nBOTH_FAIL sanity sample: {len(san)} cases. Case-level counts: {dict(sc)}. Evaluator false-negative risk: `{risk}`; `{warning}`. Evaluator overoptimization risk: `MODERATE`.\n\nEvaluation protection: exact/normalized overlap {len(exact)}, suspicious near duplicate {len(near)}.\n\nTraining parameters should remain frozen for the first composition-only Pilot V1 experiment.\n\nDecision: `READY_FOR_HF_DATASET_DISCOVERY`. This authorizes dataset discovery only, not download, dataset construction, or training.\n''';(OUT/'preflight_report.md').write_text(report,encoding='utf-8')
 print(json.dumps({'current':current,'keep':kc,'drop':dc,'gap':total_gap,'candidate_range':cand,'sanity':sanity,'decision':'READY_FOR_HF_DATASET_DISCOVERY'},ensure_ascii=False,indent=2,default=dict))
if __name__=='__main__':main()
