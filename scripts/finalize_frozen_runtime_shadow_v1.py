import hashlib, inspect, json, sys
from collections import Counter
from pathlib import Path
ROOT_HINT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT_HINT))
from src.evidence_sufficiency_v1 import evaluate_evidence
from src.citation_support_v1 import build_support_package
from src.answer_generation_v1 import generate_answer

R=Path(__file__).resolve().parents[1]
SRC=R/'evaluation/core_dynamic_e2e_shadow_v1'
OUT=R/'evaluation/core_dynamic_e2e_runtime_shadow_v1'
for p in [OUT/'results',OUT/'diagnostics',OUT/'reports',OUT/'audit']:
    p.mkdir(parents=True,exist_ok=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def writejl(p,rows): p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
cases=jl(SRC/'cases/mixed_e2e_shadow_v1.jsonl'); proxy={x['case_id']:x for x in jl(SRC/'results/mixed_e2e_shadow_results_v1.jsonl')}
contracts={
 'evidence_runtime':{'entrypoint':'evaluate_evidence','module':'src.evidence_sufficiency_v1','signature':str(inspect.signature(evaluate_evidence)),'version':'EVIDENCE_SUFFICIENCY_V1','input_contract':'query, case_id, frozen Retriever V1 result with exact Top-5','output_contract':'Evidence OUTPUT_FIELDS','frozen_hash':sha(R/'evaluation/evidence_sufficiency/v1/audit/evidence_sufficiency_v1_freeze.json')},
 'citation_runtime':{'entrypoint':'build_support_package','module':'src.citation_support_v1','signature':str(inspect.signature(build_support_package)),'version':'CITATION_SUPPORT_V1','input_contract':'query, case_id, retrieval_result, evidence_result','output_contract':'Citation OUTPUT_FIELDS','frozen_hash':sha(R/'evaluation/citation_support/v1/audit/citation_support_v1_freeze.json')},
 'answer_runtime':{'entrypoint':'generate_answer','module':'src.answer_generation_v1','signature':str(inspect.signature(generate_answer)),'version':'ANSWER_GENERATION_V1','input_contract':'query, case_id, support_package, optional frozen model adapter','output_contract':'Answer OUTPUT_FIELDS','frozen_hash':sha(R/'evaluation/answer_generation/runtime_v1/audit/answer_generation_v1_freeze.json')},
 'blocking_runtime':{'module':'src.retrieval_v1.DenseRetrieverV1','entrypoint':'__init__/_verify_bundle','error':'freeze manifest hash mismatch: knowledge_base_v1_freeze.json','adapter_fixable_without_frozen_change':False}}
(OUT/'audit/runtime_contract_audit_v1.json').write_text(json.dumps(contracts,ensure_ascii=False,indent=2),encoding='utf-8')
results=[]; failures=[]; disagreements=[]
for c in cases:
    err={'layer':'retrieval','code':'FROZEN_HASH_MISMATCH','message':'DenseRetrieverV1 rejected frozen bundle before retrieval; knowledge_base_v1_freeze.json and rag_retrieval_v1_freeze.json sidecars do not match working-tree bytes.'}
    row={'case_id':c['case_id'],'query':c['query'],'case_type':c['case_type'],'strategy':'equal_rrf','runtime_executed':False,'retrieval_executed':False,'evidence_runtime_executed':False,'citation_runtime_executed':False,'answer_runtime_executed':False,'input_support_package':None,'evidence_output':None,'citation_output':None,'answer_output':None,'runtime_error':err,'proxy_fallback_result':proxy.get(c['case_id'])}
    results.append(row); failures.append({'case_id':c['case_id'],'reason_code':'RETRIEVAL_RUNTIME_ERROR','detail':err}); disagreements.append({'case_id':c['case_id'],'reason_code':'RUNTIME_ERROR','proxy_evidence_status':proxy.get(c['case_id'],{}).get('core_dynamic_shadow',{}).get('evidence_status'),'runtime_evidence_status':None,'proxy_traceability':None,'runtime_citation_result':None,'proxy_success':None,'runtime_answer_success':None})
writejl(OUT/'results/actual_runtime_results_v1.jsonl',results); writejl(OUT/'diagnostics/runtime_failure_analysis.jsonl',failures); writejl(OUT/'diagnostics/proxy_runtime_disagreement.jsonl',disagreements); writejl(OUT/'diagnostics/core_runtime_regression_cases.jsonl',[]); writejl(OUT/'diagnostics/dynamic_runtime_gain_cases.jsonl',[]); writejl(OUT/'diagnostics/runtime_conflict_cases.jsonl',[])
counts=Counter(x['case_type'] for x in cases); metrics={'dataset':{'cases':len(cases),'case_sha256':sha(SRC/'cases/mixed_e2e_shadow_v1.jsonl'),'case_counts':dict(counts)},'actual_execution':{'retrieval':0,'evidence':0,'citation':0,'answer':0,'failed_before_retrieval':len(cases)},'actual_evidence_metrics':'NOT_COMPUTABLE','actual_citation_metrics':'NOT_COMPUTABLE','actual_answer_metrics':'NOT_COMPUTABLE','proxy_runtime_agreement_rate':0.0,'disagreements':{'RUNTIME_ERROR':len(cases)},'core_regression':'NOT_COMPUTABLE','dynamic_gain':'NOT_COMPUTABLE','conflict_evaluation':'NOT_COMPUTABLE','fusion':{'equal_rrf':'BLOCKED','core_priority':'BLOCKED','dynamic_priority':'BLOCKED'},'readiness':'NEEDS_RUNTIME_INTEGRATION_FIX'}
(OUT/'results/actual_runtime_metrics_v1.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
report='''# Actual Frozen Runtime E2E Shadow Execution V1\n\n## Outcome\n\nActual execution is **blocked before retrieval**. `DenseRetrieverV1._verify_bundle()` rejects both freeze manifests because their working-tree SHA256 values differ from checked sidecars. No proxy output is counted as an actual runtime metric.\n\n## Execution\n\n- Cases: 80 (unchanged input hash recorded)\n- Retrieval executed: 0\n- Evidence executed: 0\n- Citation executed: 0\n- Answer executed: 0\n- Runtime errors: 80\n\n## Required fix\n\nDetermine why Git working-tree bytes differ from frozen sidecar hashes (likely line-ending materialization), then create a separately versioned valid frozen bundle or make the freeze process platform-stable. Do not edit the current frozen files in place. After a new valid bundle is approved, rerun this exact case file.\n\n## Readiness\n\n`NEEDS_RUNTIME_INTEGRATION_FIX`\n'''
(OUT/'reports/actual_runtime_e2e_report_v1.md').write_text(report,encoding='utf-8'); (OUT/'reports/production_candidate_readiness_runtime_v1.md').write_text('`NEEDS_RUNTIME_INTEGRATION_FIX`\n\nFrozen Retriever V1 rejects its own bundle before runtime execution.\n',encoding='utf-8')
integrity={'dynamic_raw_sha256':sha(R/'data/04_kb_expansion_candidate/dynamic_campus_v1/raw/source/full_news_raw_restored.json'),'expected_dynamic_raw_sha256':'f2d26bb0fed32d851fd510a4483beef041fac634870c824527f31be841adde92','knowledge_freeze_actual':sha(R/'data/03_knowledge_base/v1/audit/knowledge_base_v1_freeze.json'),'knowledge_freeze_sidecar':(R/'data/03_knowledge_base/v1/audit/knowledge_base_v1_freeze.json.sha256').read_text(encoding='ascii').strip(),'rag_freeze_actual':sha(R/'data/03_knowledge_base/v1/audit/rag_retrieval_v1_freeze.json'),'rag_freeze_sidecar':(R/'data/03_knowledge_base/v1/audit/rag_retrieval_v1_freeze.json.sha256').read_text(encoding='ascii').strip(),'frozen_files_modified_by_this_run':False}
(OUT/'audit/frozen_integrity_v1.json').write_text(json.dumps(integrity,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(cases),'actual_execution':'NO','blocked_at':'DenseRetrieverV1._verify_bundle','readiness':'NEEDS_RUNTIME_INTEGRATION_FIX'},ensure_ascii=False))
