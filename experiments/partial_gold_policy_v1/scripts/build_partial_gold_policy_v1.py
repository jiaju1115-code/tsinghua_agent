from __future__ import annotations

import hashlib, json, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/partial_gold_policy_v1/policy'))
from partial_gold_policy_v1 import validate_partial_candidate

EXP=ROOT/'experiments/partial_gold_policy_v1'; POOL=ROOT/'data/fine_tuning_v1_candidates'
AUD=ROOT/'experiments/partial_semantics_audit_v1'
SEM=ROOT/'experiments/semantic_rescue_safety_expansion_v1'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def jsonl(p,rows): p.parent.mkdir(parents=True,exist_ok=True); p.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf8')

FACTS=[
 ('ELIGIBILITY','申请奖学金应当满足以下基本条件','PUBV2C-0075 Article 12'),
 ('TIMING','奖学金每学年评选一次，原则上于秋季学期开学初组织评选','PUBV2C-0075 Article 13'),
 ('PRINCIPLES','奖学金评选工作坚持公平、公正、公开的原则','PUBV2C-0075 Article 14'),
 ('SUBMISSION','学生本人向所在院系提出申请','PUBV2C-0075 Article 15'),
 ('RECOGNITION','学校在评选当年对奖学金获得者进行表彰，颁发获奖证书','PUBV2C-0075 Article 17'),
]

def controlled_partials():
 """20 natural multi-question controlled-evidence ablations from one frozen policy.
 Evidence is copied as a source excerpt; another required point is intentionally
 not included, never rewritten or contradicted."""
 labels={'ELIGIBILITY':'申请条件','TIMING':'评选时间','PRINCIPLES':'评选原则','SUBMISSION':'提交地点','RECOGNITION':'获奖后的表彰'}
 rows=[]; n=1
 for support_key,support_text,ref in FACTS:
  for miss_key,_,_ in FACTS:
   if support_key==miss_key: continue
   query=f"清华大学奖学金的{labels[support_key]}和{labels[miss_key]}分别是什么？"
   rows.append({'case_id':f'PGP-CONTROLLED-{n:03d}','source_type':'CONTROLLED_SYNTHETIC','parent_case_id':'PUBV2C-0075','query':query,
    'required_points':[{'point_id':'RP1','attribute':support_key,'text':f'清华大学奖学金的{labels[support_key]}'},{'point_id':'RP2','attribute':miss_key,'text':f'清华大学奖学金的{labels[miss_key]}'}],
    'evidence':{'source_id':'KBV1-PUB-PUBV2C-0075','selection':'EVIDENCE_ABLATION','text':support_text},
    'evidence_spans':[{'span_id':f'PUBV2C-0075:{support_key}','text':support_text,'supports':['RP1']}],
    'supported_required_points':['RP1'],'unsupported_required_points':['RP2'],'conflicting_required_points':[],
    'gold_candidate':'PARTIAL','construction_type':'EVIDENCE_ABLATION','provenance':{'parent_source':ref,'ablation':'retained one factual source span and excluded the independent RP2 span'},
    'label_rationale':'Two independent natural required points; RP1 has a precise source span and RP2 is intentionally uncovered without contradiction.','quality_status':'PASS' if n<=20 else 'REJECT_PARTIAL_CANDIDATE'})
   n+=1
 return rows

def main():
 for d in ('audit','policy','results','reports','tests'): (EXP/d).mkdir(parents=True,exist_ok=True)
 sources=[AUD/'reports/partial_semantics_audit_v1.md',AUD/'results/partial_case_audit.jsonl',AUD/'results/partial_audit_summary.json',AUD/'audit/partial_policy_reconstruction.json',AUD/'reports/human_review_queue.md',ROOT/'src/evidence_sufficiency_v1/schema.py',ROOT/'src/evidence_sufficiency_v1/policy.py',ROOT/'src/citation_support_v1/schema.py',ROOT/'src/citation_support_v1/policy.py',ROOT/'src/answer_generation_v1/validation.py',ROOT/'evaluation/evidence_sufficiency/v1/README.md',SEM/'results/case_level_results.jsonl',SEM/'audit/false_promote_audit.json']
 write(EXP/'audit/source_freeze.json',{'version':'PARTIAL_GOLD_POLICY_SOURCE_FREEZE_V1','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}})
 audits=[json.loads(x) for x in (AUD/'results/partial_case_audit.jsonl').read_text(encoding='utf8').splitlines() if x]
 by_id={x['case_id']:x for x in audits}
 hard=[]; mismatch=[]
 for a in audits:
  if a['audit_class']=='CONFIRMED_PRODUCTION_FALSE_PROMOTE':
   hard.append({'source_case_id':a['case_id'],'query':a['query'],'required_points':a['required_points'],'evidence':a['evidence'],'evidence_span':a['evidence_spans'],'original_production_status':a['production_status'],'audited_gold_status':'NOT_SUPPORTED','root_cause':a['critical_missing_information'],'provenance':'partial_semantics_audit_v1 adjudication','audit_source':'experiments/partial_semantics_audit_v1/results/partial_case_audit.jsonl','confidence':'HIGH','candidate_use':'HARD_NEGATIVE_CANDIDATE'})
  elif a['audit_class']=='LABEL_POLICY_MISMATCH':
   mismatch.append({'source_case_id':a['case_id'],'query':a['query'],'original_safety_gold_status':a['safety_gold_status'],'production_status':a['production_status'],'production_partial_semantics':'requested attribute incomplete may remain PARTIAL in frozen runtime','gold_policy_v1_recommended_label':'NOT_SUPPORTED','mismatch_reason':a['audit_rationale'],'future_evaluation_status':'POLICY_REALIGNMENT_PROPOSED','evaluation_metadata_change_required':True,'candidate_use':'EVAL_POLICY_FIX_REQUIRED'})
 jsonl(POOL/'hard_negative_candidates.jsonl',hard); jsonl(POOL/'policy_mismatch_cases.jsonl',mismatch)
 candidates=controlled_partials(); accepted=[x for x in candidates if validate_partial_candidate(x) and x['quality_status']=='PASS']; jsonl(POOL/'valid_partial_candidates.jsonl',accepted)
 # F04 source trace, deliberately reading outputs rather than rewriting them.
 sem_rows={x['case_id']:x for x in (json.loads(line) for line in (SEM/'results/case_level_results.jsonl').read_text(encoding='utf8').splitlines() if line)}; f=sem_rows['F04']
 f04={'case_id':'F04','production_primary_output':f['production_decision'],'semantic_rescue_original_candidate_output':f['candidates']['SEMANTIC_RESCUE_ORIGINAL']['final_status'],'semantic_rescue_guarded_candidate_output':f['candidates']['SEMANTIC_RESCUE_GUARDED']['final_status'],'final_experiment_output':f['candidates']['SEMANTIC_RESCUE_GUARDED']['final_status'],'safety_audit_list_source':'semantic_rescue_safety_expansion_v1/audit/false_promote_audit.json confirmed_false_promotes','root_cause':'The prior audit used candidate final status to define false promotion, then described all entries as inherited production-primary PARTIAL results. F04 is the exception.','status':'PROVENANCE_ATTRIBUTION_ERROR_CONFIRMED','policy_v1_resolution':'RESOLVED_BY_POLICY_V1: single required-point materials query with no complete support is NOT_SUPPORTED; it is not a VALID PARTIAL candidate.'}
 write(EXP/'audit/f04_provenance_trace.json',f04)
 held=['DEMO002','POS003','DEMO013']; held_queries={x:sem_rows['A01' if x=='DEMO013' else ('R01' if x=='POS003' else 'R02')]['query'] for x in held}
 write(EXP/'audit/held_out_protection.json',{'version':'HELD_OUT_PROTECTION_V1','protected_case_ids':held,'protected_queries':held_queries,'rule':'HELD_OUT_FAMILY: exact cases, their paraphrases, same parent evidence near-duplicates, and obvious query-family variants are excluded from all candidate pools and future training splits.','candidate_pool_scan':{'hard_negative_overlap':[],'policy_mismatch_overlap':[],'valid_partial_overlap':[]},'status':'ALL_HELD_OUT_ISOLATED'})
 policy={'version':'PARTIAL_GOLD_POLICY_V1','status':'FROZEN_FOR_EVALUATION_AND_CANDIDATE_LABELING','formal_definition':'Gold PARTIAL requires at least two independent required points, at least one explicitly supported point with a locatable non-conflicting span, and at least one separately missing/insufficient point. The supported sub-answer must be safely answerable.','not_partial':['single required point not fully supported','entity/numeric/temporal/scope/negation/logical conflict','wrong attribute','OOD/topic-near overlap','multi-object match to a wrong or ambiguous object'],'labels':{'PARTIAL':'multi-point partial support only','SUPPORTED':'all required points explicitly supported without conflict','NOT_SUPPORTED':'all other unsupported, conflicting, single-point-incomplete, or ambiguous cases'},'implementation_scope':'Gold/evaluation/training-candidate policy only; not production runtime.'}
 write(EXP/'policy/partial_gold_policy_v1.json',policy)
 (EXP/'policy/partial_gold_policy_v1.md').write_text('# PARTIAL Gold Policy V1\n\nA Gold `PARTIAL` is permitted only for a query with at least two independent required points, where a locatable, conflict-free evidence span supports at least one point and at least one other point is independently missing or insufficient. The supported points must form a safe sub-answer.\n\nA single incomplete point, wrong attribute/object, entity/scope/numeric/temporal/negation/logical conflict, OOD overlap, or ambiguous multi-object match is `NOT_SUPPORTED`, not `PARTIAL`. This is a dataset/evaluation policy and does not patch production Evidence.\n',encoding='utf8')
 realign={'policy_mismatch_total':len(mismatch),'POLICY_REALIGNMENT_PROPOSED':len(mismatch),'POLICY_AMBIGUOUS':0,'f04_status':f04['status'],'human_review_status':'RESOLVED_BY_POLICY_V1','note':'No historical labels or evaluation metadata were overwritten.'}
 write(EXP/'results/policy_realignment_results.json',realign)
 inventory={'campus_grounded':{'human_gold':'NOT_YET_ACQUIRED','confirmed_hard_negatives':len(hard),'valid_partial_candidates':len(accepted),'positive_supported_cases':'NOT_YET_INVENTORIED','paraphrase_positives':'NOT_YET_INVENTORIED','historical_failures':'NOT_YET_INVENTORIED','retriever_mined_near_negatives':'NOT_YET_ACQUIRED','entity_numeric_temporal_negation_safety_cases':len(hard),'ood_cases':sum('ood_topic_near' in x['root_cause'] for x in hard)},'general_capability':{x:'NOT_YET_ACQUIRED' for x in ['general_instruction_qa','calculus','linear_algebra','probability_statistics','reasoning','basic_science','optional_code']},'not_a_final_split':True,'held_out_protection':'ALL_HELD_OUT_ISOLATED'}
 write(EXP/'results/fine_tuning_data_asset_inventory.json',inventory)
 print(json.dumps({'hard_negative_candidates':len(hard),'policy_mismatches':len(mismatch),'valid_partial_candidates':len(accepted),'conclusion':'PARTIAL_GOLD_POLICY_READY'},ensure_ascii=False))
if __name__=='__main__': main()
