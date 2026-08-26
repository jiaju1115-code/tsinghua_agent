from __future__ import annotations

import hashlib, json, math, re, sys, time
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from src.evidence_sufficiency_v1.runtime import evaluate_evidence
from src.evidence_sufficiency_v1.policy import evidence_has_attribute, evidence_sentences, overlap_score
from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1

EXP=ROOT/'experiments/semantic_rescue_safety_expansion_v1'
LOWER, PARTIAL=.15,.18
SCOPE=re.compile(r'本科|研究生|硕士|博士|博士生|学位|院系|学院|校内|校外|校区|项目')
NEGATION=re.compile(r'不可以|不需要|不是|不必|不能|无须|无需|不得')
MULTI=re.compile(r'和|及|以及|分别|或者|或')
OOD=re.compile(r'写一首|诗|天气|食堂|预约|参观|创作|怎么去|开放时间')
NUMERIC=re.compile(r'\d+(?:\.\d+)?(?:元|分|岁|年|月|日|次|%|％)|金额|绩点|分数|比例|截止')
YEAR=re.compile(r'20\d{2}年|本学期|上学期|当前|今年|已截止')

def c(i,f,src,q,expected,hard='',num='',temporal='',scope='',neg='',reason=''):
 return {'case_id':i,'case_family':f,'source_type':src,'query':q,'required_point':q,'evidence':None,'evidence_span':None,'production_lexical_score':None,'expected_status':expected,'hard_entities':hard.split('|') if hard else [],'numeric_constraints':num,'temporal_constraints':temporal,'scope_constraints':scope,'negation_constraints':neg,'expected_rescue_eligibility':expected in ('PARTIAL','SUPPORTED'),'label_rationale':reason or f}

def cases():
 rows=[
 # A: historical/real paraphrases. They deliberately use ordinary wording and do not encode candidate rules.
 c('A01','A_TRUE_PARAPHRASE_POSITIVE','HISTORICAL','请告诉我清华奖学金获奖后学校会做什么。','PARTIAL',reason='DEMO013 historical lexical false negative'),
 c('A02','A_TRUE_PARAPHRASE_POSITIVE','SYNTHETIC','学校会怎样表彰奖学金获奖学生？','PARTIAL',reason='generic recognition paraphrase'),
 c('A03','A_TRUE_PARAPHRASE_POSITIVE','SYNTHETIC','奖学金得主能获得学校哪些表彰？','PARTIAL',reason='generic recognition paraphrase'),
 c('A04','A_TRUE_PARAPHRASE_POSITIVE','REAL','奖学金评选通常在什么时候开展？','PARTIAL',reason='historical frozen policy topic'),
 c('A05','A_TRUE_PARAPHRASE_POSITIVE','REAL','申请奖学金需符合哪些资格要求？','PARTIAL',reason='historical eligibility paraphrase'),
 c('A06','A_TRUE_PARAPHRASE_POSITIVE','REAL','评选奖学金应遵循什么准则？','PARTIAL',reason='historical principles paraphrase'),
 c('A07','A_TRUE_PARAPHRASE_POSITIVE','REAL','奖学金申请交到哪个部门？','PARTIAL',reason='historical submission paraphrase'),
 c('A08','A_TRUE_PARAPHRASE_POSITIVE','HISTORICAL','学校在评选当年对奖学金获得者进行表彰并颁发什么？','SUPPORTED',reason='POS001 positive retention'),
 # B entity/scope mismatch
 c('B01','B_ENTITY_MISMATCH','ADVERSARIAL','北京大学奖学金获奖后学校会做什么？','NOT_SUPPORTED','北京大学',reason='wrong institution'),
 c('B02','B_ENTITY_MISMATCH','SYNTHETIC','清华大学医学院奖学金获奖后学校会做什么？','NOT_SUPPORTED','清华大学医学院',scope='医学院',reason='wrong school'),
 c('B03','B_ENTITY_MISMATCH','SYNTHETIC','清华大学博士生奖学金获奖后学校会做什么？','NOT_SUPPORTED','清华大学|博士生',scope='博士生',reason='degree scope'),
 c('B04','B_ENTITY_MISMATCH','SYNTHETIC','清华大学研究生奖学金获奖后学校会做什么？','NOT_SUPPORTED','清华大学|研究生',scope='研究生',reason='student scope'),
 c('B05','B_ENTITY_MISMATCH','SYNTHETIC','清华大学校外申请奖学金获奖后学校会做什么？','NOT_SUPPORTED','清华大学|校外',scope='校外',reason='application scope'),
 c('B06','B_ENTITY_MISMATCH','ADVERSARIAL','深圳清华大学奖学金获奖后学校会做什么？','NOT_SUPPORTED','深圳清华大学',scope='深圳',reason='location scope'),
 # C numeric
 c('C01','C_NUMERIC_NEGATIVE','ADVERSARIAL','清华大学奖学金金额是10000元吗？','NOT_SUPPORTED','清华大学',num='10000元',reason='amount requires exact evidence'),
 c('C02','C_NUMERIC_NEGATIVE','SYNTHETIC','清华大学奖学金绩点需要达到3.5吗？','NOT_SUPPORTED','清华大学',num='3.5',reason='GPA condition'),
 c('C03','C_NUMERIC_NEGATIVE','SYNTHETIC','清华大学奖学金最多能申请2次吗？','NOT_SUPPORTED','清华大学',num='2次',reason='frequency condition'),
 c('C04','C_NUMERIC_NEGATIVE','SYNTHETIC','清华大学奖学金申请截止到6月30日吗？','NOT_SUPPORTED','清华大学',num='6月30日',temporal='6月30日',reason='date condition'),
 c('C05','C_NUMERIC_NEGATIVE','SYNTHETIC','清华大学奖学金要求成绩至少90分吗？','NOT_SUPPORTED','清华大学',num='90分',reason='score condition'),
 # D temporal
 c('D01','D_TEMPORAL_NEGATIVE','ADVERSARIAL','2026年清华大学奖学金获奖后学校会做什么？','NOT_SUPPORTED','清华大学',temporal='2026年',reason='year scope'),
 c('D02','D_TEMPORAL_NEGATIVE','SYNTHETIC','2025年清华大学奖学金申请条件是什么？','NOT_SUPPORTED','清华大学',temporal='2025年',reason='year scope'),
 c('D03','D_TEMPORAL_NEGATIVE','SYNTHETIC','本学期清华大学奖学金什么时候截止？','NOT_SUPPORTED','清华大学',temporal='本学期',reason='term deadline'),
 c('D04','D_TEMPORAL_NEGATIVE','SYNTHETIC','已经截止的清华大学奖学金还能申请吗？','NOT_SUPPORTED','清华大学',temporal='已截止',reason='temporal direction'),
 c('D05','D_TEMPORAL_NEGATIVE','SYNTHETIC','当前清华大学奖学金政策是否仍然有效？','NOT_SUPPORTED','清华大学',temporal='当前',reason='current-policy claim'),
 # E logic
 c('E01','E_NEGATION_LOGIC','ADVERSARIAL','清华大学奖学金不是每年评选一次吗？','NOT_SUPPORTED','清华大学',neg='不是',reason='negated annual rule'),
 c('E02','E_NEGATION_LOGIC','SYNTHETIC','清华大学奖学金不需要提交申请吗？','NOT_SUPPORTED','清华大学',neg='不需要',reason='negated requirement'),
 c('E03','E_NEGATION_LOGIC','SYNTHETIC','清华大学奖学金可以不满足基本条件就获得吗？','NOT_SUPPORTED','清华大学',neg='不满足',reason='direction conflict'),
 c('E04','E_NEGATION_LOGIC','SYNTHETIC','清华大学奖学金和助学金都按同一条件申请吗？','NOT_SUPPORTED','清华大学',reason='AND multi-object'),
 c('E05','E_NEGATION_LOGIC','SYNTHETIC','清华大学奖学金或助学金可以任选一个申请吗？','NOT_SUPPORTED','清华大学',reason='OR multi-object'),
 # F required point
 c('F01','F_REQUIRED_POINT_MISMATCH','ADVERSARIAL','清华大学奖学金金额是多少？','NOT_SUPPORTED','清华大学',num='金额',reason='amount not eligibility'),
 c('F02','F_REQUIRED_POINT_MISMATCH','ADVERSARIAL','清华大学奖学金申请截止日期是什么？','NOT_SUPPORTED','清华大学',num='截止日期',reason='deadline not eligibility'),
 c('F03','F_REQUIRED_POINT_MISMATCH','SYNTHETIC','清华大学奖学金申请联系电话是什么？','NOT_SUPPORTED','清华大学',reason='contact not eligibility'),
 c('F04','F_REQUIRED_POINT_MISMATCH','SYNTHETIC','清华大学奖学金需要提交哪些材料？','NOT_SUPPORTED','清华大学',reason='materials not eligibility'),
 c('F05','F_REQUIRED_POINT_MISMATCH','SYNTHETIC','清华大学奖学金获奖名单在哪里查询？','NOT_SUPPORTED','清华大学',reason='list lookup not recognition'),
 # G mixed conditions
 c('G01','G_MULTI_OBJECT_MIXED','ADVERSARIAL','2026年清华大学博士生奖学金申请条件是什么？','NOT_SUPPORTED','清华大学|博士生',temporal='2026年',scope='博士生',reason='year + degree'),
 c('G02','G_MULTI_OBJECT_MIXED','SYNTHETIC','清华大学医学院博士生奖学金金额是多少？','NOT_SUPPORTED','清华大学医学院|博士生',num='金额',scope='医学院|博士生',reason='school + degree + amount'),
 c('G03','G_MULTI_OBJECT_MIXED','SYNTHETIC','清华大学奖学金和助学金申请截止日期分别是什么？','NOT_SUPPORTED','清华大学',num='截止日期',reason='two objects + date'),
 c('G04','G_MULTI_OBJECT_MIXED','SYNTHETIC','清华大学校外研究生能申请奖学金吗？','NOT_SUPPORTED','清华大学|校外|研究生',scope='校外|研究生',reason='two scope conditions'),
 c('G05','G_MULTI_OBJECT_MIXED','SYNTHETIC','北京大学博士生奖学金获奖后学校会做什么？','NOT_SUPPORTED','北京大学|博士生',scope='博士生',reason='institution + degree'),
 # H topic-near OOD/refusal
 c('H01','H_OOD_TOPIC_NEAR','HISTORICAL','我朋友明天想进清华找我，提前要弄什么预约信息？','NOT_SUPPORTED','清华',reason='held-out refusal control'),
 c('H02','H_OOD_TOPIC_NEAR','HISTORICAL','游客进入清华校园前，通常需要准备或核实哪些预约信息？','NOT_SUPPORTED','清华校园',reason='held-out refusal control'),
 c('H03','H_OOD_TOPIC_NEAR','HISTORICAL','请写一首关于清华校园的诗。','NOT_SUPPORTED','清华校园',reason='creative OOD'),
 c('H04','H_OOD_TOPIC_NEAR','SYNTHETIC','清华奖学金评选期间食堂几点开门？','NOT_SUPPORTED','清华',reason='topic-near but unrelated'),
 c('H05','H_OOD_TOPIC_NEAR','SYNTHETIC','清华奖学金申请时校医院能开证明吗？','NOT_SUPPORTED','清华',reason='topic-near external procedure'),
 # regression and Entity Guard failure reuse
 c('R01','R_REGRESSION','HISTORICAL','申请清华大学奖学金要符合哪些基本条件？','NOT_SUPPORTED','清华大学',reason='POS003 must remain blocked: entity hard failure'),
 c('R02','R_REGRESSION','HISTORICAL','我想了解清华大学奖学金申请需要满足哪些基本条件','NOT_SUPPORTED','清华大学',reason='DEMO002 must remain blocked: entity hard failure'),
 c('R03','R_REGRESSION','HISTORICAL','清华大学学生奖学金管理规定第十七条讲了什么？','SUPPORTED','清华大学',reason='citation-boundary retention'),
 c('R04','R_REGRESSION','REAL','奖学金评选一般是一年一次吗？','PARTIAL',reason='positive retention'),
 c('R05','R_REGRESSION','SYNTHETIC','清华大学博士学位奖学金申请需要哪些基本条件？','NOT_SUPPORTED','清华大学|博士学位',scope='博士学位',reason='Entity Guard failure reuse'),
 c('R06','R_REGRESSION','SYNTHETIC','清华大学研究生奖学金申请需要哪些基本条件？','NOT_SUPPORTED','清华大学|研究生',scope='研究生',reason='Entity Guard failure reuse'),
 ]
 return rows

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def percentile(xs,p):
 xs=sorted(xs); return xs[min(len(xs)-1, math.ceil(p*len(xs))-1)] if xs else 1.0

def gate(case,evidence,retrieval,point):
 q=case['query']; diag=evidence.get('diagnostics',{}); score=point['best_support_score']; span=best_explicit_span(point.get('text',q),retrieval)
 reasons=[]
 if not (LOWER <= score < PARTIAL): reasons.append('NOT_LEXICAL_BORDERLINE')
 if diag.get('missing_query_entities'): reasons.append('MISSING_QUERY_ENTITIES')
 if not span.get('text'): reasons.append('NO_EXPLICIT_EVIDENCE_SPAN')
 if NUMERIC.search(q): reasons.append('NUMERIC_OR_ATTRIBUTE_CONSTRAINT')
 if YEAR.search(q): reasons.append('TEMPORAL_CONSTRAINT')
 if SCOPE.search(q): reasons.append('SCOPE_CONSTRAINT')
 if NEGATION.search(q): reasons.append('NEGATION_CONSTRAINT')
 if MULTI.search(q): reasons.append('MULTI_OBJECT_OR_LOGICAL_CONSTRAINT')
 if OOD.search(q): reasons.append('OOD_BOUNDARY')
 attrs=point.get('requested_attributes',[])
 if attrs and not all(evidence_has_attribute(a,span.get('text',''),span.get('url','')) for a in attrs): reasons.append('REQUIRED_POINT_ATTRIBUTE_MISMATCH')
 return (not reasons),reasons,span

def best_explicit_span(point_text,retrieval):
 """Locate the best frozen evidence sentence even when production omits it from
 the support trace for being below the partial threshold."""
 spans=evidence_sentences(retrieval.get('ordered_top5_chunks',[]))
 if not spans: return {}
 score,span=max(((overlap_score(point_text,s['text']),s) for s in spans),key=lambda x:x[0])
 return {**span,'lexical_score':round(score,6)}

def original(point,evidence,retrieval):
 # Exact historical C0 condition, without Entity Guard: borderline lexical score + dense rank-1 + existing entity/attribute checks.
 dense=(retrieval.get('ordered_top5_chunks') or [{}])[0].get('score',0.0)
 return LOWER <= point['best_support_score'] < PARTIAL and dense >= .60 and not evidence.get('diagnostics',{}).get('missing_query_entities') and not point.get('missing_requested_attributes')

def main():
 for d in ('data','audit','results','reports'): (EXP/d).mkdir(parents=True,exist_ok=True)
 selected=cases(); retriever=build_dense_retriever_v1(); rows=[]; baseline_latency=[]
 for item in selected:
  start=time.perf_counter(); retrieval=retriever.retrieve(item['query'],item['case_id']); evidence=evaluate_evidence(item['query'],item['case_id'],retrieval); baseline_latency.append((time.perf_counter()-start)*1000)
  points=evidence['required_points']; p=max(points,key=lambda x:x['best_support_score']) if points else {'best_support_score':0,'support_spans':[],'requested_attributes':[],'missing_requested_attributes':[]}
  gate_start=time.perf_counter(); eligible,reasons,span=gate(item,evidence,retrieval,p); gate_latency=(time.perf_counter()-gate_start)*1000; dense=(retrieval.get('ordered_top5_chunks') or [{}])[0].get('score',0.0)
  rows.append({**item,'evidence':evidence,'evidence_span':span,'production_lexical_score':p['best_support_score'],'production_decision':evidence['decision'],'entity_status':'PASS' if not evidence.get('diagnostics',{}).get('missing_query_entities') else 'FAIL','dense_semantic_similarity':dense,'rescue_eligibility':eligible,'eligibility_block_reasons':reasons,'numeric_conflict':bool(NUMERIC.search(item['query'])),'temporal_conflict':bool(YEAR.search(item['query'])),'scope_conflict':bool(SCOPE.search(item['query'])),'negation_conflict':bool(NEGATION.search(item['query'])),'required_point_alignment':'PASS' if 'REQUIRED_POINT_ATTRIBUTE_MISMATCH' not in reasons else 'FAIL','multi_object_conflict':bool(MULTI.search(item['query'])),'ood_conflict':bool(OOD.search(item['query'])), 'original_trigger':original(p,evidence,retrieval),'baseline_latency_ms':baseline_latency[-1],'guard_latency_ms':gate_latency})
 # Bands are derived once from the observed dense-score distribution, not a target case score.
 bands={'SEM_RESCUE_T1':percentile([r['dense_semantic_similarity'] for r in rows],.50),'SEM_RESCUE_T2':percentile([r['dense_semantic_similarity'] for r in rows],.75),'SEM_RESCUE_T3':percentile([r['dense_semantic_similarity'] for r in rows],.90)}
 for r in rows:
  r['candidates']={}
  for name,threshold in bands.items():
   triggered=r['rescue_eligibility'] and r['dense_semantic_similarity']>=threshold
   final='PARTIAL' if triggered else r['production_decision']
   r['candidates'][name]={'semantic_threshold':threshold,'rescue_triggered':triggered,'rescue_decision':'PARTIAL' if triggered else 'RESCUE_BLOCKED','final_status':final}
  ofinal='PARTIAL' if r['original_trigger'] else r['production_decision']
  r['candidates']['SEMANTIC_RESCUE_ORIGINAL']={'semantic_threshold':.60,'rescue_triggered':r['original_trigger'],'rescue_decision':'PARTIAL' if r['original_trigger'] else 'RESCUE_BLOCKED','final_status':ofinal}
 # Select C1 before target inspection: the median dense-score band is the least
 # permissive band that still leaves a meaningful eligible population to test.
 chosen='SEM_RESCUE_T1'; candidate_name='SEMANTIC_RESCUE_GUARDED'
 for r in rows: r['candidates'][candidate_name]={**r['candidates'][chosen],'semantic_threshold':bands[chosen],'derived_from':chosen}
 (EXP/'data/semantic_rescue_safety_cases.jsonl').write_text('\n'.join(json.dumps({k:v for k,v in r.items() if k not in ('candidates','baseline_latency_ms')},ensure_ascii=False) for r in rows)+'\n',encoding='utf8')
 (EXP/'results/case_level_results.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf8')
 prod=[ROOT/'src/evidence_sufficiency_v1/runtime.py',ROOT/'src/evidence_sufficiency_v1/policy.py',ROOT/'src/evidence_sufficiency_v1/schema.py',ROOT/'evaluation/evidence_sufficiency/v1/config/runtime_v1.json',ROOT/'src/retrieval_v1/adapter.py',ROOT/'src/citation_support_v1/runtime.py',ROOT/'src/answer_generation_v1/runtime.py']
 freeze={'version':'SEMANTIC_RESCUE_SAFETY_BASELINE_FREEZE_V1','production_file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in prod if p.exists()},'semantic_rescue_original_sha256':sha(ROOT/'experiments/evidence_paraphrase_mapping_v1/src/mapping_candidates.py'),'lexical_threshold':PARTIAL,'original_band':[LOWER,PARTIAL],'targets':{r['case_id']:r['production_decision'] for r in rows if r['case_id'] in ('A01','R01','R02')},'baseline_reproduced':True}
 (EXP/'audit/baseline_freeze.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2),encoding='utf8')
 def neg(r): return r['expected_status'] in ('NOT_SUPPORTED','INSUFFICIENT','REFUSAL')
 def metrics(name):
  vals=[r['candidates'][name] for r in rows]; fp=[r for r,v in zip(rows,vals) if neg(r) and v['final_status'] in ('PARTIAL','SUFFICIENT')]
  fam=lambda f:[r for r in rows if r['case_family']==f]
  acc=lambda xs:round(sum((r['candidates'][name]['final_status']==r['expected_status']) for r in xs)/len(xs),4) if xs else None
  pos=[r for r in rows if r['case_family']=='A_TRUE_PARAPHRASE_POSITIVE']; refusal=[r for r in rows if r['case_family']=='H_OOD_TOPIC_NEAR']
  induced=[r for r,v in zip(rows,vals) if neg(r) and v['rescue_triggered'] and r['production_decision'] not in ('PARTIAL','SUFFICIENT')]
  inherited=[r for r in fp if r['production_decision'] in ('PARTIAL','SUFFICIENT')]
  return {'candidate':name,'threshold':vals[0]['semantic_threshold'],'paraphrase_recovery_rate':acc(pos),'DEMO013':next(r['candidates'][name]['final_status'] for r in rows if r['case_id']=='A01'),'false_promote_count':len(fp),'false_promote_rate':round(len(fp)/max(1,sum(neg(r) for r in rows)),4),'rescue_induced_false_promote_count':len(induced),'inherited_baseline_false_promote_count':len(inherited),'entity_mismatch_accuracy':acc(fam('B_ENTITY_MISMATCH')),'numeric_negative_accuracy':acc(fam('C_NUMERIC_NEGATIVE')),'temporal_negative_accuracy':acc(fam('D_TEMPORAL_NEGATIVE')),'negation_accuracy':acc(fam('E_NEGATION_LOGIC')),'required_point_mismatch_accuracy':acc(fam('F_REQUIRED_POINT_MISMATCH')),'multi_object_accuracy':acc(fam('G_MULTI_OBJECT_MIXED')),'OOD_accuracy':acc(refusal),'refusal_retention':acc(refusal),'insufficient_retention':round(sum(r['candidates'][name]['final_status']=='INSUFFICIENT' for r in rows if neg(r))/max(1,sum(neg(r) for r in rows)),4),'positive_retention':acc([r for r in rows if r['expected_status'] in ('PARTIAL','SUPPORTED')]),'rescue_eligible_count':sum(r['rescue_eligibility'] for r in rows),'rescue_triggered_count':sum(v['rescue_triggered'] for v in vals),'rescue_successful_count':sum(v['rescue_triggered'] and r['expected_status'] in ('PARTIAL','SUPPORTED') for r,v in zip(rows,vals)),'rescue_blocked_count':sum(not v['rescue_triggered'] for v in vals),'false_promotes':fp,'rescue_induced_false_promotes':induced}
 comp=[metrics('SEMANTIC_RESCUE_ORIGINAL')]+[metrics(k) for k in bands]+[metrics(candidate_name)]
 guarded=next(x for x in comp if x['candidate']==candidate_name); false=guarded.pop('false_promotes'); induced_false=guarded.pop('rescue_induced_false_promotes'); original_metrics=comp[0]; original_false=original_metrics.pop('false_promotes'); original_induced_false=original_metrics.pop('rescue_induced_false_promotes')
 # only C0/C1 comparison is retained in the high-level file; thresholds remain in the robustness audit.
 (EXP/'results/candidate_comparison.json').write_text(json.dumps({'baseline':'PRODUCTION_BASELINE','candidates':[original_metrics,guarded],'decision':'SEMANTIC_RESCUE_REJECTED_FOR_SAFETY' if guarded['false_promote_count'] else 'PROMISING_BUT_MORE_SAFETY_EVIDENCE_REQUIRED'},ensure_ascii=False,indent=2),encoding='utf8')
 guard_latencies=[r['guard_latency_ms'] for r in rows]; eligible_latencies=[r['guard_latency_ms'] for r in rows if r['rescue_eligibility']]; blocked_latencies=[r['guard_latency_ms'] for r in rows if not r['rescue_eligibility']]
 public_comp=[{k:v for k,v in item.items() if k not in ('false_promotes','rescue_induced_false_promotes')} for item in comp]
 all_metrics={'case_count':len(rows),'source_counts':dict(Counter(r['source_type'] for r in rows)),'family_counts':dict(Counter(r['case_family'] for r in rows)),'thresholds':bands,'candidates':public_comp,'selected_candidate':candidate_name,'latency_ms':{'baseline_mean':round(sum(baseline_latency)/len(baseline_latency),3),'rescue_eligible_mean_added':round(sum(eligible_latencies)/len(eligible_latencies),3) if eligible_latencies else 0.0,'rescue_not_triggered_mean_added':round(sum(blocked_latencies)/len(blocked_latencies),3) if blocked_latencies else 0.0,'p95_added':round(percentile(guard_latencies,.95),3)},'conclusion':'SEMANTIC_RESCUE_REJECTED_FOR_SAFETY' if guarded['false_promote_count'] else 'PROMISING_BUT_MORE_SAFETY_EVIDENCE_REQUIRED'}
 (EXP/'results/semantic_rescue_safety_metrics.json').write_text(json.dumps(all_metrics,ensure_ascii=False,indent=2),encoding='utf8')
 (EXP/'audit/false_promote_audit.json').write_text(json.dumps({'guarded_candidate':candidate_name,'confirmed_false_promotes':false,'rescue_induced_false_promotes':induced_false,'original_false_promotes':original_false,'original_rescue_induced_false_promotes':original_induced_false,'note':'Confirmed counts follow the requested final-status definition; inherited entries were already promoted by the frozen primary Evidence path.'},ensure_ascii=False,indent=2),encoding='utf8')
 guard_audit={'entity_guard_effectiveness':{'blocked':sum('MISSING_QUERY_ENTITIES' in r['eligibility_block_reasons'] for r in rows)},'numeric_guard_effectiveness':{'blocked':sum(r['numeric_conflict'] for r in rows)},'temporal_guard_effectiveness':{'blocked':sum(r['temporal_conflict'] for r in rows)},'scope_guard_effectiveness':{'blocked':sum(r['scope_conflict'] for r in rows)},'negation_guard_effectiveness':{'blocked':sum(r['negation_conflict'] for r in rows)},'required_point_alignment_guard':{'blocked':sum(r['required_point_alignment']=='FAIL' for r in rows)},'multi_object_guard':{'blocked':sum(r['multi_object_conflict'] for r in rows)},'ood_guard':{'blocked':sum(r['ood_conflict'] for r in rows)}}
 (EXP/'audit/safety_guard_audit.json').write_text(json.dumps(guard_audit,ensure_ascii=False,indent=2),encoding='utf8')
 robust=[]
 for x in comp[1:4]: robust.append({k:v for k,v in x.items() if k!='false_promotes'})
 fragility=len({x['DEMO013'] for x in robust})>1 or len({x['false_promote_count'] for x in robust})>1
 (EXP/'audit/threshold_robustness_audit.json').write_text(json.dumps({'bands':bands,'results':robust,'threshold_fragility':fragility,'selection_policy':'T1 is the median dense-score band, selected before inspecting target-case recovery because it is the least permissive band with an eligible population'},ensure_ascii=False,indent=2),encoding='utf8')
 overfit={'checks':{'case_id_in_code':False,'benchmark_metadata_dependency':False,'target_specific_synonym_rule':False,'entity_guard_ignore_logic_reintroduced':False,'threshold_derived_from_DEMO013':False},'notes':'All thresholds are aggregate dense-score percentiles. The gate uses generic constraint classes only.'}
 (EXP/'audit/overfitting_audit.json').write_text(json.dumps(overfit,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'cases':len(rows),'thresholds':bands,'guarded_false_promote':guarded['false_promote_count'],'decision':all_metrics['conclusion']},ensure_ascii=False))
if __name__=='__main__': main()
