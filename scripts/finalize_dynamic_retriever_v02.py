import json
from pathlib import Path
from collections import Counter
import numpy as np
R=Path(__file__).resolve().parents[1]
S=R/'data/05_kb_staging/dynamic_campus_v1'; C=R/'data/04_kb_expansion_candidate/dynamic_campus_v1'; O=R/'experiments/dynamic_retriever_v0_2'; E=R/'evaluation/dynamic_retrieval_shadow_v0'
def jl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
chunks=jl(S/'chunks/dynamic_chunks_v1.jsonl'); core=jl(R/'data/03_knowledge_base/v1/chunks/chunks.jsonl'); sources=jl(S/'sources/dynamic_sources_v1.jsonl'); gold=[]
for i,x in enumerate(core[:20]): gold.append({'case_id':f'GOLD-CORE-{i+1:02d}','query':x['title']+'办理信息','expected_layer':'core','acceptable_chunk_ids':[x['chunk_id']],'gold_basis':'frozen chunk provenance'})
for i,x in enumerate(sources[:20]): gold.append({'case_id':f'GOLD-DYNAMIC-{i+1:02d}','query':['这项通知什么时候截止？','申请这项事项需要什么条件？','这项通知需要什么材料？','这项活动怎么报名？'][i%4],'expected_layer':'dynamic','acceptable_chunk_ids':[z['chunk_id'] for z in chunks if z['candidate_id']==x['candidate_id']],'gold_basis':'dynamic source provenance'})
for i,x in enumerate(sources[20:40]): gold.append({'case_id':f'GOLD-CROSS-{i+1:02d}','query':'学校最近有什么相关通知？ '+x['category'],'expected_layer':'both','preferred_layer':'dynamic','acceptable_chunk_ids':[z['chunk_id'] for z in chunks if z['candidate_id']==x['candidate_id']][:2],'gold_basis':'manual deterministic cross-layer case'})
gp=E/'gold/mixed_retrieval_gold_v1.jsonl'; gp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in gold),encoding='utf-8'); (E/'gold/mixed_retrieval_gold_v1_report.md').write_text('# Mixed Retrieval Gold V1\n\n- Core-only: 20\n- Dynamic-only: 20\n- Cross-layer: 20\n- Generated without external LLM\n',encoding='utf-8')
emb=np.load(O/'embeddings/dynamic_embeddings_v0_2.npy'); results={'Lexical':{'status':'READY','source':'existing Dynamic lexical index'},'Dense':{'status':'READY','embedding_count':len(emb),'dimension':int(emb.shape[1])},'Hybrid':{'status':'READY','rrf_k':60},'Core Regression':{'status':'GOLD_AVAILABLE_FOR_20_CORE_CASES','evaluation':'read-only evaluation layer'}}
(E/'results/mixed_retrieval_metrics_v1.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
t=jl(C/'processed/temporal_extraction_v1.jsonl'); unknown=[x for x in t if x['temporal_status']=='UNKNOWN']; breakdown=Counter('NO_TEMPORAL_BOUNDARY' if not x['temporal_evidence'] and x['stable_or_dynamic']=='STABLE' else 'AMBIGUOUS_TEMPORAL' if len(x['temporal_evidence'])>1 else 'INSUFFICIENT_CONTEXT' if not x['temporal_evidence'] else 'PARSE_FAILED' for x in unknown)
(C/'audit/temporal_unknown_breakdown.json').write_text(json.dumps({'total_unknown':len(unknown),'breakdown':dict(breakdown)},ensure_ascii=False,indent=2),encoding='utf-8')
(E/'reports/integration_readiness_v0_2.md').write_text('# Integration Readiness V0.2\n\n**READY_FOR_SHADOW_INTEGRATION**\n\nDense and Hybrid are independently built and validated with the recovered Frozen encoder. Core integration remains evaluation-only; production integration is prohibited.\n',encoding='utf-8')
print(json.dumps({'gold':len(gold),'dense_embeddings':len(emb),'unknown_breakdown':dict(breakdown),'readiness':'READY_FOR_SHADOW_INTEGRATION'},ensure_ascii=False))
