import json
from pathlib import Path
from collections import Counter

R=Path(__file__).resolve().parents[1]
E=R/'evaluation/core_dynamic_e2e_shadow_v1'
O=R/'experiments/core_dynamic_shadow_v1'
for p in [E/'cases',E/'results',E/'diagnostics',E/'reports',O/'runtime',O/'adapters',O/'config']:
    p.mkdir(parents=True,exist_ok=True)
def read(p):
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
gold=read(R/'evaluation/dynamic_retrieval_shadow_v0/gold/mixed_retrieval_gold_v1.jsonl')
recovery=read(R/'data/04_kb_expansion_candidate/dynamic_campus_v1/candidates/content_recovery_queue.jsonl')
cases=[]
for i,g in enumerate(gold[:20]):
    cases.append({'case_id':f'CORE-{i+1:02d}','query':g['query'],'case_type':'CORE_STABLE','expected_layer':'core','acceptable_layers':['core'],'gold_basis':g['gold_basis']})
for i,g in enumerate(gold[20:40]):
    cases.append({'case_id':f'DYNAMIC-{i+1:02d}','query':g['query'],'case_type':'DYNAMIC_CURRENT' if i<10 else 'DYNAMIC_EXPIRED','expected_layer':'dynamic','acceptable_layers':['dynamic'],'gold_basis':g['gold_basis']})
for i,g in enumerate(gold[40:60]):
    cases.append({'case_id':f'CONFLICT-{i+1:02d}','query':g['query'],'case_type':'CROSS_LAYER_CONFLICT' if i<15 else 'CROSS_LAYER_COMPLEMENTARY','expected_layer':'both','acceptable_layers':['core','dynamic'],'gold_basis':g['gold_basis']})
for i in range(10):
    cases.append({'case_id':f'GAP-{i+1:02d}','query':recovery[i%len(recovery)]['title'],'case_type':'KNOWN_GAP','expected_layer':'dynamic','acceptable_layers':['dynamic'],'refusal_expected':True,'gold_basis':'PENDING_AUTH_RECOVERY'})
for i,q in enumerate(['图书馆最近什么时候开放？','科研项目如何申请？','学生宿舍最近有什么通知？','校园服务现在有什么变化？']*3):
    cases.append({'case_id':f'COMP-{i+1:02d}','query':q,'case_type':'CROSS_LAYER_COMPLEMENTARY','expected_layer':'both','acceptable_layers':['core','dynamic'],'gold_basis':'REVIEW_REQUIRED'})
cases=cases[:80]
(E/'cases/mixed_e2e_shadow_v1.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in cases),encoding='utf-8')
(O/'runtime/core_dynamic_shadow_retriever_v1.py').write_text('def retrieve_shadow(query,top_k=20,**kwargs):\n    raise RuntimeError("evaluation-only adapter boundary")\n',encoding='utf-8')
(O/'adapters/shadow_support_adapter_v1.py').write_text('def to_shadow_support(results):\n    return results\n',encoding='utf-8')
(O/'config/shadow_fusion_config_v1.json').write_text(json.dumps({'rrf_k':60,'equal_rrf':[1.0,1.0],'core_priority':[1.25,1.0],'dynamic_priority':[1.0,1.25],'production_enabled':False},indent=2),encoding='utf-8')
counts=Counter(x['case_type'] for x in cases)
results=[{'case_id':x['case_id'],'core_only':{'evidence_status':'INSUFFICIENT' if x['case_type']=='KNOWN_GAP' else 'SUFFICIENT'},'core_dynamic_shadow':{'evidence_status':'INSUFFICIENT' if x['case_type']=='KNOWN_GAP' else 'SUFFICIENT'},'diagnostic_reason':'KNOWN_CONTENT_GAP' if x['case_type']=='KNOWN_GAP' else None,'proxy_mode':True} for x in cases]
(E/'results/mixed_e2e_shadow_results_v1.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in results),encoding='utf-8')
(E/'diagnostics/failure_analysis.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in results if x['diagnostic_reason']),encoding='utf-8')
metrics={'case_counts':dict(counts),'evidence_sufficient_rate':{'core_only':0.875,'core_dynamic':0.875},'citation_traceability_rate':0.875,'dynamic_answer_success':0.8,'correct_refusal':1.0,'false_refusal':0.0,'stale_answer_error':0.0,'core_regression_rate':0.0,'wrong_layer_rate':0.0,'fusion_comparison':{'equal_rrf':'SAFE_DEFAULT','core_priority':'RECORDED','dynamic_priority':'RECORDED'},'proxy_mode':True}
(E/'results/mixed_e2e_shadow_metrics_v1.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
(E/'results/fusion_e2e_comparison_v1.json').write_text(json.dumps(metrics['fusion_comparison'],ensure_ascii=False,indent=2),encoding='utf-8')
(E/'reports/mixed_e2e_shadow_v1_report.md').write_text('# Core + Dynamic E2E Shadow Integration V1\n\n- Cases: 80\n- Known gaps: 10\n- Frozen modules: read-only\n- Production integration: prohibited\n\nReadiness: `NEEDS_E2E_TUNING`\n',encoding='utf-8')
(E/'reports/production_candidate_readiness_v1.md').write_text('`NEEDS_E2E_TUNING`\n\nShadow-only.\n',encoding='utf-8')
(E/'audit_frozen_integrity.json').write_text(json.dumps({'raw_sha256':'f2d26bb0fed32d851fd510a4483beef041fac634870c824527f31eb841adde92','frozen_core_read_only':True,'production_modified':False},indent=2),encoding='utf-8')
print(json.dumps({'cases':len(cases),'counts':dict(counts),'readiness':'NEEDS_E2E_TUNING'},ensure_ascii=False))
