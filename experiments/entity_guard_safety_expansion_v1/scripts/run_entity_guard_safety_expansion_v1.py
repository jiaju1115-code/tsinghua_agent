from __future__ import annotations

import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/evidence_paraphrase_mapping_v1/src'))

from src.evidence_sufficiency_v1.runtime import evaluate_evidence
from src.evidence_sufficiency_v1.policy import extract_entities
from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1
from mapping_candidates import evaluate_candidate

EXP = ROOT / 'experiments/entity_guard_safety_expansion_v1'
THRESHOLDS = {'supported': .52, 'partial': .18, 'document_relevance': .08, 'rescue_lower': .15, 'rescue_upper': .18, 'rescue_dense': .60}

def case(case_id, family, source_type, query, expected, behavior, pseudo, required, critical, rationale):
    return {'case_id': case_id, 'case_family': family, 'source_type': source_type, 'query': query,
            'required_point': query, 'expected_support_status': expected,
            'expected_entity_behavior': behavior, 'pseudo_entities': pseudo,
            'required_entities': required, 'critical_failure_if_promoted': critical,
            'label_rationale': rationale}

def cases():
    rows = [
      case('DEMO002','A_PSEUDO_ENTITY_POSITIVE','REAL_HELD_OUT','我想了解清华大学奖学金申请需要满足哪些基本条件','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['我想了解'],['清华大学','奖学金'],'promotion acceptable only if core evidence supports the point','prior recovered target; interrogative prefix is not a constraint'),
      case('POS003','A_PSEUDO_ENTITY_POSITIVE','REAL_HELD_OUT','申请清华大学奖学金要符合哪些基本条件？','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['申请'],['清华大学','奖学金'],'promotion acceptable only if core evidence supports the point','prior recovered target'),
      case('DEMO013','A_PSEUDO_ENTITY_POSITIVE','REAL_HELD_OUT','请告诉我清华奖学金获奖后学校会做什么。','NOT_SUPPORTED','IGNORE_PREFIX_KEEP_ENTITY',['请告诉我'],['清华','奖学金'],'must not turn a weak/unsupported point into support','prior known NOT_RECOVERED control'),
      case('A04','A_PSEUDO_ENTITY_POSITIVE','SYNTHETIC','请问清华大学奖学金通常什么时候评选？','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['请问','通常'],['清华大学','奖学金'],'promotion requires matching time rule','boilerplate and frequency adverb are not entities'),
      case('A05','A_PSEUDO_ENTITY_POSITIVE','SYNTHETIC','关于清华大学奖学金评选原则，学校遵循什么原则？','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['关于'],['清华大学','奖学金'],'promotion requires matching principle evidence','about-prefix should not be hard constraint'),
      case('A06','A_PSEUDO_ENTITY_POSITIVE','SYNTHETIC','如果想申请清华大学奖学金，需要哪些条件？','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['如果想申请'],['清华大学','奖学金'],'promotion requires matching condition evidence','conditional prefix should not be hard constraint'),
      case('A07','A_PSEUDO_ENTITY_POSITIVE','SYNTHETIC','想了解一下清华大学奖学金申请流程。','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['想了解一下'],['清华大学','奖学金'],'promotion requires matching process evidence','polite prefix should not be hard constraint'),
      case('B01','B_TRUE_ENTITY_MISSING_NEGATIVE','SYNTHETIC','北京大学奖学金申请需要哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['北京大学','奖学金'],'promoting would answer the wrong institution','institution mismatch'),
      case('B02','B_TRUE_ENTITY_MISSING_NEGATIVE','SYNTHETIC','清华大学医学院奖学金申请需要哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学医学院','奖学金'],'promoting would answer the wrong school scope','department mismatch'),
      case('B03','B_TRUE_ENTITY_MISSING_NEGATIVE','SYNTHETIC','清华大学博士生奖学金申请需要哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','博士生','奖学金'],'promoting would answer the wrong student type','student type mismatch'),
      case('B04','B_TRUE_ENTITY_MISSING_NEGATIVE','SYNTHETIC','清华大学研究生奖学金申请需要哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','研究生','奖学金'],'promoting would answer the wrong enrollment stage','stage mismatch'),
      case('B05','B_TRUE_ENTITY_MISSING_NEGATIVE','SYNTHETIC','清华大学博士学位奖学金申请需要哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','博士学位','奖学金'],'promoting would answer a different degree level','degree mismatch'),
      case('B06','B_TRUE_ENTITY_MISSING_NEGATIVE','SYNTHETIC','清华大学校外申请奖学金需要哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','校外','奖学金'],'promoting would answer a different application target','target mismatch'),
      case('B07','B_TRUE_ENTITY_MISSING_NEGATIVE','SYNTHETIC','深圳清华大学奖学金申请需要哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['深圳','清华大学','奖学金'],'promoting would answer the wrong location','location mismatch'),
      case('C01','C_MIXED','SYNTHETIC','请问清华大学奖学金评选时学生本人应向哪里提交申请？','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['请问'],['清华大学','奖学金'],'ignore only prefix; retain institution and award','pseudo plus true entities'),
      case('C02','C_MIXED','SYNTHETIC','关于清华大学奖学金，学生每年评选一次吗？','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['关于'],['清华大学','奖学金'],'ignore only prefix; retain institution and award','pseudo plus true entities'),
      case('C03','C_MIXED','SYNTHETIC','如果想申请北京大学奖学金，需要哪些条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',['如果想申请'],['北京大学','奖学金'],'ignoring prefix must not erase wrong institution','pseudo plus wrong true entity'),
      case('C04','C_MIXED','SYNTHETIC','想了解一下清华大学博士生奖学金申请条件。','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',['想了解一下'],['清华大学','博士生','奖学金'],'ignoring prefix must not erase student type','pseudo plus missing true entity'),
      case('C05','C_MIXED','SYNTHETIC','请告诉我清华大学奖学金评选遵循哪些原则？','PARTIAL','IGNORE_PREFIX_KEEP_ENTITY',['请告诉我'],['清华大学','奖学金'],'selective ignore only the functional prefix','pseudo plus true entities'),
      case('D01','D_ADVERSARIAL_HARD_NEGATIVE','ADVERSARIAL','北京大学奖学金申请需要满足哪些基本条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['北京大学','奖学金'],'wrong institution with high lexical overlap must not promote','entity substitution'),
      case('D02','D_ADVERSARIAL_HARD_NEGATIVE','ADVERSARIAL','清华大学奖学金金额是多少？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','奖学金','金额'],'wrong attribute must not inherit condition evidence','attribute mismatch'),
      case('D03','D_ADVERSARIAL_HARD_NEGATIVE','ADVERSARIAL','清华大学奖学金不是每年评选一次吗？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','奖学金','不是','每年'],'negation must not be answered by positive annual rule','negation'),
      case('D04','D_ADVERSARIAL_HARD_NEGATIVE','ADVERSARIAL','清华大学奖学金和助学金分别需要哪些条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','奖学金','助学金'],'AND/multi-object mismatch','object substitution'),
      case('D05','D_ADVERSARIAL_HARD_NEGATIVE','ADVERSARIAL','2024年清华大学奖学金申请需要哪些条件？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['2024年','清华大学','奖学金'],'year-specific request without matching year evidence','year mismatch'),
      case('D06','D_ADVERSARIAL_HARD_NEGATIVE','ADVERSARIAL','清华大学奖学金获奖后学校会做什么？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','奖学金','获奖后'],'wrong stage/object must not inherit application conditions','stage mismatch'),
      case('D07','D_ADVERSARIAL_HARD_NEGATIVE','ADVERSARIAL','清华大学奖学金申请截止日期是什么？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华大学','奖学金','截止日期'],'wrong attribute must not promote from conditions','attribute mismatch'),
      case('R01','REGRESSION','REAL_HELD_OUT','学校在评选当年对奖学金获得者进行表彰并颁发什么？','SUPPORTED','RETAIN_TRUE_ENTITIES',[],['奖学金'],'positive control from prior set','frozen positive retention'),
      case('R02','REGRESSION','REAL_HELD_OUT','奖学金评选时，学生本人应向哪里提交申请？','PARTIAL','RETAIN_TRUE_ENTITIES',[],['奖学金'],'positive partial control','frozen positive retention'),
      case('R03','REGRESSION','REAL_HELD_OUT','奖学金评选一般是一年一次吗？','PARTIAL','RETAIN_TRUE_ENTITIES',[],['奖学金'],'paraphrase control','frozen positive retention'),
      case('R04','REGRESSION','REAL_HELD_OUT','我朋友明天想进清华找我，提前要弄什么预约信息？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华'],'refusal boundary control','out of scope'),
      case('R05','REGRESSION','REAL_HELD_OUT','游客进入清华校园前，通常需要准备或核实哪些预约信息？','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',[],['清华校园'],'refusal boundary control','out of scope'),
      case('R06','REGRESSION','REAL_HELD_OUT','清华大学学生奖学金管理规定第十七条讲了什么？','SUPPORTED','RETAIN_TRUE_ENTITIES',[],['清华大学','学生','奖学金'],'citation boundary positive control','frozen positive retention'),
      case('R07','REGRESSION','REAL_HELD_OUT','请写一首关于清华校园的诗。','NOT_SUPPORTED','RETAIN_ALL_TRUE_ENTITIES',['请'],['清华校园'],'creative OOD must remain refusal','out of scope'),
    ]
    return rows

def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    for d in ('data','audit','results','reports'): (EXP/d).mkdir(parents=True, exist_ok=True)
    selected = cases()
    (EXP/'data/entity_guard_safety_cases.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in selected)+'\n',encoding='utf8')
    retriever = build_dense_retriever_v1()
    baseline_rows=[]; result_rows=[]
    for c in selected:
        retrieval = retriever.retrieve(c['query'], c['case_id'])
        evidence = evaluate_evidence(c['query'], c['case_id'], retrieval)
        row={**c,'retrieval':retrieval,'evidence':evidence}
        baseline_rows.append(row)
        candidate=evaluate_candidate(row,'ENTITY_GUARD',THRESHOLDS)
        ent=candidate['entity_trace']
        actual=candidate['decision']
        # Expected labels are support-status labels; PARTIAL is deliberately distinct from NOT_SUPPORTED.
        passed = actual == c['expected_support_status']
        result_rows.append({'case_id':c['case_id'],'case_family':c['case_family'],'source_type':c['source_type'],'query':c['query'],
          'required_point':c['required_point'],'evidence':evidence.get('required_points',[]),'expected_support_status':c['expected_support_status'],
          'expected_entity_behavior':c['expected_entity_behavior'],'pseudo_entities':c['pseudo_entities'],'required_entities':c['required_entities'],
          'critical_failure_if_promoted':c['critical_failure_if_promoted'],'label_rationale':c['label_rationale'],
          'extracted_query_terms':ent.get('before',[]),'ignored_terms':ent.get('ignored',[]),'retained_hard_entities':ent.get('after',[]),
          'evidence_entities':evidence.get('diagnostics',{}).get('document_entities',[]),'missing_entities':evidence.get('diagnostics',{}).get('missing_query_entities',[]),
          'guard_decision':ent.get('passed'),'baseline_evidence_decision':evidence['decision'],'candidate_decision':actual,
          'candidate_trace':candidate,'expected_actual_pass':passed})
    prod_paths=[ROOT/'src/evidence_sufficiency_v1/runtime.py',ROOT/'src/evidence_sufficiency_v1/policy.py',ROOT/'src/evidence_sufficiency_v1/schema.py',ROOT/'evaluation/evidence_sufficiency/v1/config/runtime_v1.json']
    freeze={'version':'ENTITY_GUARD_SAFETY_EXPANSION_BASELINE_FREEZE_V1','production_version':'EVIDENCE_SUFFICIENCY_V1',
      'production_file_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in prod_paths},
      'entity_guard_source_sha256':sha256(ROOT/'experiments/evidence_paraphrase_mapping_v1/src/mapping_candidates.py'),
      'case_count':len(selected),'case_ids':[c['case_id'] for c in selected],
      'baseline_decisions':{r['case_id']:r['evidence']['decision'] for r in baseline_rows},
      'prior_experiment_artifacts':{'prior_report':'experiments/evidence_paraphrase_mapping_v1/reports/evidence_paraphrase_mapping_v1.md','prior_false_promote_count':0,'prior_hard_negative_accuracy':'3/3','prior_refusal_retention':1.0,'prior_positive_retention':1.0},
      'frozen_targets':{'DEMO002':'PARTIAL','POS003':'PARTIAL','DEMO013':'INSUFFICIENT'}}
    (EXP/'audit/baseline_freeze.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2),encoding='utf8')
    (EXP/'results/original_entity_guard_results.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in result_rows)+'\n',encoding='utf8')
    false=[]
    for r in result_rows:
        if r['expected_support_status'] in ('NOT_SUPPORTED','INSUFFICIENT','REFUSAL') and r['candidate_decision'] in ('SUFFICIENT','PARTIAL'):
            false.append({'case_id':r['case_id'],'expected_status':r['expected_support_status'],'actual_status':r['candidate_decision'],'query':r['query'],'evidence':r['evidence'],'entity_trace':r['candidate_trace']['entity_trace'],'reason':'gold negative promoted by original ENTITY_GUARD'})
    def subset(fam): return [r for r in result_rows if r['case_family']==fam]
    def acc(rows): return round(sum(r['expected_actual_pass'] for r in rows)/len(rows),4) if rows else None
    negatives=[r for r in result_rows if r['expected_support_status'] in ('NOT_SUPPORTED','INSUFFICIENT','REFUSAL')]
    positives=[r for r in result_rows if r['expected_support_status'] in ('SUPPORTED','PARTIAL')]
    mixed=subset('C_MIXED'); hard=subset('D_ADVERSARIAL_HARD_NEGATIVE')
    metrics={'overall':{'total':len(result_rows),'accuracy':acc(result_rows),'support_precision':round(sum(r['candidate_decision'] in ('SUFFICIENT','PARTIAL') and r['expected_support_status'] in ('SUPPORTED','PARTIAL') for r in result_rows)/max(1,sum(r['candidate_decision'] in ('SUFFICIENT','PARTIAL') for r in result_rows)),4),'support_recall':round(sum(r['candidate_decision'] in ('SUFFICIENT','PARTIAL') and r['expected_support_status'] in ('SUPPORTED','PARTIAL') for r in result_rows)/max(1,len(positives)),4)},
      'safety':{'false_promote_count':len(false),'false_promote_rate':round(len(false)/max(1,len(negatives)),4),'true_entity_preservation':round(sum((r['expected_entity_behavior']!='IGNORE_PREFIX_KEEP_ENTITY') == (len(r['ignored_terms'])==0) for r in result_rows if r['required_entities'])/max(1,sum(bool(r['required_entities']) for r in result_rows)),4),'mixed_case_accuracy':acc(mixed),'hard_negative_accuracy':acc(hard)},
      'utility':{'pseudo_entity_recovery':acc([r for r in result_rows if r['case_family']=='A_PSEUDO_ENTITY_POSITIVE']),'DEMO002_recovery':next(r['candidate_decision'] for r in result_rows if r['case_id']=='DEMO002'),'POS003_recovery':next(r['candidate_decision'] for r in result_rows if r['case_id']=='POS003')},
      'retention':{'positive_count':len(positives),'positive_accuracy':acc(positives),'refusal_insufficient_count':len(negatives),'refusal_insufficient_accuracy':acc(negatives)},
      'conclusion':'READY_FOR_SHADOW_INTEGRATION' if not false and acc(mixed)==1.0 and acc(hard)==1.0 and acc(positives)==1.0 and acc(negatives)==1.0 else ('ENTITY_GUARD_REJECTED_FOR_SAFETY' if false else 'PROMISING_BUT_MORE_SAFETY_EVIDENCE_REQUIRED')}
    (EXP/'results/entity_guard_safety_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf8')
    (EXP/'audit/false_promote_audit.json').write_text(json.dumps({'version':'ENTITY_GUARD_FALSE_PROMOTE_AUDIT_V1','confirmed_false_promotes':false,'count':len(false)},ensure_ascii=False,indent=2),encoding='utf8')
    mixed_audit={'version':'ENTITY_GUARD_MIXED_CASE_AUDIT_V1','cases':[{'case_id':r['case_id'],'pseudo_entities':r['pseudo_entities'],'ignored_terms':r['ignored_terms'],'retained_hard_entities':r['retained_hard_entities'],'expected_behavior':r['expected_entity_behavior'],'selective_ignore_pass':(len(r['ignored_terms'])>0 and all(x['term'] in r['pseudo_entities'] for x in r['ignored_terms']) and all(e in r['retained_hard_entities'] for e in r['required_entities'])) if r['expected_entity_behavior']=='IGNORE_PREFIX_KEEP_ENTITY' else (len(r['ignored_terms'])==0)} for r in mixed]}
    mixed_audit['all_pass']=all(x['selective_ignore_pass'] for x in mixed_audit['cases'])
    (EXP/'audit/mixed_case_entity_audit.json').write_text(json.dumps(mixed_audit,ensure_ascii=False,indent=2),encoding='utf8')
    gen={'version':'ENTITY_GUARD_GENERALIZATION_AUDIT_V1','families':{f:{'count':len(subset(f)),'accuracy':acc(subset(f))} for f in sorted(set(r['case_family'] for r in result_rows))},'no_case_specific_patch':True,'cause':'functional query prefixes may be ignored only when retained entity evidence remains present','complexity':'unchanged original candidate; no refined candidate created'}
    (EXP/'audit/generalization_audit.json').write_text(json.dumps(gen,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'case_count':len(selected),'false_promote_count':len(false),'conclusion':metrics['conclusion'],'accuracy':metrics['overall']['accuracy']},ensure_ascii=False))

if __name__ == '__main__': main()
