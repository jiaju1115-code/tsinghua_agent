from __future__ import annotations

import hashlib, json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/partial_semantics_audit_v1'
SRC=ROOT/'experiments/semantic_rescue_safety_expansion_v1'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')

def classify(row):
 """Apply only the reconstructed frozen semantics; this is not a new rule."""
 ident=row['case_id']; ev=row['evidence']; points=ev['required_points']; reasons=ev['reason_codes']
 conflicts=[]
 if row['scope_conflict']: conflicts.append('scope_conflict')
 if row['numeric_conflict']: conflicts.append('numeric_conflict')
 if row['temporal_conflict']: conflicts.append('temporal_conflict')
 if row['negation_conflict']: conflicts.append('negation_conflict')
 if row['multi_object_conflict']: conflicts.append('multi_object_conflict')
 if row['ood_conflict']: conflicts.append('ood_topic_near')
 attr=bool(ev['missing_requested_attributes'])
 # F04 is not a primary-PARTIAL result. The source audit mixed final-candidate
 # output into an alleged primary-path set, so no automatic policy adjudication.
 if ev['decision']!='PARTIAL':
  return 'HUMAN_REVIEW_REQUIRED','HUMAN_REVIEW','Source target is not currently a production PARTIAL; candidate and primary-path provenance conflict.',conflicts,attr
 # Explicit attribute omissions are the precise documented PARTIAL boundary:
 # README permits a partial answer when requested attributes remain incomplete.
 # The safety set instead labels every such query NOT_SUPPORTED, hence policy mismatch.
 if attr and ident in {'C01','C04','F01','F02','F03','F05','H04'}:
  return 'LABEL_POLICY_MISMATCH','EVAL_POLICY_FIX_REQUIRED','Frozen README permits PARTIAL when a requested attribute remains incomplete; the safety gold applies an all-or-nothing label.',conflicts,attr
 # A scope/value/direction/OOD constraint is not represented as a supported
 # required point. The runtime reached PARTIAL from lexical overlap alone.
 return 'CONFIRMED_PRODUCTION_FALSE_PROMOTE','HARD_NEGATIVE_CANDIDATE','Single or decomposed core point lacks support for a critical scope/value/direction/OOD constraint; PARTIAL was reached through lexical overlap rather than supported required-point content.',conflicts,attr

def main():
 for d in ('audit','results','reports'): (EXP/d).mkdir(parents=True,exist_ok=True)
 source_paths=[SRC/'results/case_level_results.jsonl',SRC/'audit/false_promote_audit.json',SRC/'results/semantic_rescue_safety_metrics.json',SRC/'reports/semantic_rescue_safety_expansion_v1.md',ROOT/'src/evidence_sufficiency_v1/runtime.py',ROOT/'src/evidence_sufficiency_v1/policy.py',ROOT/'src/evidence_sufficiency_v1/schema.py',ROOT/'evaluation/evidence_sufficiency/v1/config/runtime_v1.json',ROOT/'evaluation/evidence_sufficiency/v1/README.md',ROOT/'src/citation_support_v1/policy.py',ROOT/'src/answer_generation_v1/validation.py']
 rows={r['case_id']:r for r in (json.loads(x) for x in (SRC/'results/case_level_results.jsonl').read_text(encoding='utf8').splitlines() if x)}
 fp=json.loads((SRC/'audit/false_promote_audit.json').read_text(encoding='utf8'))['confirmed_false_promotes']
 ids=[x['case_id'] for x in fp]
 freeze={'version':'PARTIAL_SEMANTICS_SOURCE_FREEZE_V1','target_case_ids':ids,'target_count':len(ids),'source_file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},'current_production_outputs':{i:rows[i]['production_decision'] for i in ids},'current_safety_expected_outputs':{i:rows[i]['expected_status'] for i in ids}}
 write(EXP/'audit/source_freeze.json',freeze)
 reconstruction={'version':'PARTIAL_POLICY_RECONSTRUCTION_V1','sources':['src/evidence_sufficiency_v1/runtime.py','src/evidence_sufficiency_v1/schema.py','evaluation/evidence_sufficiency/v1/README.md','src/citation_support_v1/policy.py','src/answer_generation_v1/validation.py'],'decisions':{'SUFFICIENT':'Every parsed core point is SUPPORTED; explicitly requested attributes are present.','PARTIAL':'At least one point is SUPPORTED or PARTIALLY_SUPPORTED; documentation permits incomplete core points or requested attributes. Runtime marks a point PARTIALLY_SUPPORTED at lexical score >= 0.18 with no missing extracted entity, even when requested attributes are missing.','NOT_SUPPORTED':'Point-level status used when score < partial threshold or an extracted entity is missing.','INSUFFICIENT':'No point supported, retrieval/input failure, or detected evidence conflict; sends REQUIRE_REFUSAL.','REFUSAL':'Not an Evidence decision enum; downstream behavior for INSUFFICIENT/BLOCKED.'},'answers_to_questions':{'multiple_required_points':'Yes. Any supported/partial point yields PARTIAL when not all are fully supported.','single_point_incomplete':'Yes in implementation: a single point can be PARTIALLY_SUPPORTED from lexical score >= 0.18.','missing_entity':'No for extracted entities, but the extractor only recognizes organization-like patterns and does not model degree/scope/value constraints.','missing_attribute':'Yes: implementation allows PARTIALLY_SUPPORTED despite missing requested attributes; README describes this as an incomplete PARTIAL.','evidence_supports_only_part':'Yes, if the runtime calls that point usable support.','unresolved_qualifier':'Underspecified; only configured attribute conflicts and current-status checks are explicit.','partial_enters_answer_generation':'Yes. PARTIAL maps to ALLOW_PARTIAL_ANSWER and Answer permits only supported/PARTIALLY_SUPPORTED mapped units.','partial_answer_scope':'Citation/Answer contracts prohibit exposing unsupported point units, but they do not redefine the Evidence point threshold.','boundary':'INSUFFICIENT requires no support, conflict, or validation failure; PARTIAL is a lexical proxy boundary, not semantic entailment.'}}
 write(EXP/'audit/partial_policy_reconstruction.json',reconstruction)
 conflicts={'version':'PARTIAL_SEMANTICS_CONFLICT_V1','status':'PARTIAL_SEMANTICS_CONFLICT','conflicts':[{'sources':['runtime.py point-status branch','README Decisions section'],'issue':'Runtime permits PARTIALLY_SUPPORTED solely from score >= partial threshold and extracted-entity presence, while README requires "usable support" but does not define whether topic-only overlap qualifies.'},{'sources':['runtime.py entity extraction','README entity viability checks'],'issue':'Only organization-like entities are extracted. Degree, enrollment, location, year, numeric, negation, object, and scope constraints can be absent from the entity gate.'},{'sources':['semantic_rescue false_promote_audit.json','case_level_results.jsonl'],'issue':'F04 is listed among final false promotes although its production primary decision is INSUFFICIENT.'}]}
 write(EXP/'audit/partial_semantics_conflicts.json',conflicts)
 audits=[]
 for i in ids:
  r=rows[i]; ev=r['evidence']; klass,use,rationale,conflict_list,attr=classify(r)
  points=ev['required_points']; critical=[]
  if conflict_list: critical.extend(conflict_list)
  if attr: critical.append('requested_attribute_missing')
  if not critical: critical.append('single_required_point_lexical_partial')
  audits.append({'case_id':i,'query':r['query'],'required_points':points,'evidence':ev,'evidence_spans':[s for p in points for s in p['support_spans']],'production_status':ev['decision'],'production_reason_codes':ev['reason_codes'],'safety_gold_status':r['expected_status'],'safety_gold_rationale':r['label_rationale'],'supported_required_points':ev['supported_points'],'unsupported_required_points':ev['unsupported_points'],'partially_supported_required_points':ev['partially_supported_points'],'missing_entities':ev['diagnostics']['missing_query_entities'],'entity_conflicts':['scope_constraint'] if r['scope_conflict'] else [],'numeric_conflicts':['numeric_constraint'] if r['numeric_conflict'] else [],'temporal_conflicts':['temporal_constraint'] if r['temporal_conflict'] else [],'scope_conflicts':['scope_constraint'] if r['scope_conflict'] else [],'negation_conflicts':['negation_constraint'] if r['negation_conflict'] else [],'attribute_mismatch':attr,'critical_missing_information':critical,'production_partial_semantics_applicable':ev['decision']=='PARTIAL','audit_class':klass,'audit_rationale':rationale,'recommended_future_use':use,'source_case_family':r['case_family']})
 (EXP/'results/partial_case_audit.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in audits)+'\n',encoding='utf8')
 cnt=Counter(a['audit_class'] for a in audits); roots=Counter(x for a in audits if a['audit_class']=='CONFIRMED_PRODUCTION_FALSE_PROMOTE' for x in a['critical_missing_information'])
 summary={'target_cases':len(audits),'audit_class_counts':dict(cnt),'confirmed_root_causes':dict(roots),'policy':{'production_semantics_clear_consistent_cases':0,'policy_ambiguity_cases':len(audits),'safety_set_production_label_mismatch_cases':cnt['LABEL_POLICY_MISMATCH'],'source_provenance_conflict_cases':sum(a['production_status']!='PARTIAL' for a in audits)},'systematic_partial_boundary_weakness':{'present':cnt['CONFIRMED_PRODUCTION_FALSE_PROMOTE']>=8,'description':'The frozen runtime gives a single point PARTIALLY_SUPPORTED from lexical overlap >= 0.18 without modeling degree/scope/numeric/negation/object constraints.'},'future_use_counts':dict(Counter(a['recommended_future_use'] for a in audits)),'conclusion':'MIXED_PARTIAL_SEMANTICS'}
 write(EXP/'results/partial_audit_summary.json',summary)
 human=[a for a in audits if a['audit_class']=='HUMAN_REVIEW_REQUIRED']
 if human:
  (EXP/'reports/human_review_queue.md').write_text('# Human review queue\n\n'+'\n'.join(f"- `{a['case_id']}`: {a['audit_rationale']}" for a in human)+'\n',encoding='utf8')
 print(json.dumps({'targets':len(audits),'classes':dict(cnt),'conclusion':summary['conclusion']},ensure_ascii=False))
if __name__=='__main__': main()
