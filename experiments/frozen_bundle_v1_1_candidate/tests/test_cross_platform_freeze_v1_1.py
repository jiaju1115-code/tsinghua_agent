import importlib.util, json, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
module_path=ROOT/'experiments/frozen_bundle_v1_1_candidate/candidate/dense_retriever_v1_portability_adapter.py'
spec=importlib.util.spec_from_file_location('portable',module_path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
adapter=mod.DenseRetrieverV1PortabilityAdapter()
cases=[json.loads(x) for x in open(ROOT/'evaluation/e2e_heldout/v1/cases/e2e_50_cases.jsonl',encoding='utf-8') if x.strip()][:10]
results=[]
for row in cases:
    first=adapter.retrieve(row['query'],row['case_id']+'-A'); second=adapter.retrieve(row['query'],row['case_id']+'-B')
    ids_a=[x['chunk_id'] for x in first['ordered_top5_chunks']]; ids_b=[x['chunk_id'] for x in second['ordered_top5_chunks']]
    scores_a=np.array(first['scores']); scores_b=np.array(second['scores'])
    results.append({'case_id':row['case_id'],'chunk_ids_equal':ids_a==ids_b,'rankings_equal':ids_a==ids_b,'scores_equal':bool(np.array_equal(scores_a,scores_b)),'max_abs_score_delta':float(np.max(np.abs(scores_a-scores_b)))})
out={'cases':len(results),'chunk_count':len(adapter.chunks),'embedding_count':len(adapter.embeddings),'all_rankings_equal':all(x['rankings_equal'] for x in results),'all_scores_equal':all(x['scores_equal'] for x in results),'retrieval_regression':sum(not x['rankings_equal'] or not x['scores_equal'] for x in results),'case_results':results}
(Path(__file__).parent/'retrieval_equivalence_results_v1.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
assert out['chunk_count']==488 and out['embedding_count']==488 and out['retrieval_regression']==0
print(json.dumps({'cases':out['cases'],'rankings_equal':out['all_rankings_equal'],'scores_equal':out['all_scores_equal'],'regression':out['retrieval_regression']}))
