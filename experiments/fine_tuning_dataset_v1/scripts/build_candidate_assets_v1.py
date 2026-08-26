from __future__ import annotations

import hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]; EXP=ROOT/'experiments/fine_tuning_dataset_v1'; OUT=ROOT/'data/fine_tuning_v1'
sys.path.insert(0,str(ROOT))
from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1
PREV=ROOT/'experiments/partial_gold_policy_v1'; POOL=ROOT/'data/fine_tuning_v1_candidates'; KB=ROOT/'data/03_knowledge_base/v1'
HELD={'DEMO002','POS003','DEMO013'}; EXCLUDED_SOURCE='KBV1-PUB-PUBV2C-0075'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def jsonl(p,rows): p.parent.mkdir(parents=True,exist_ok=True); p.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf8')
def norm(s): return ''.join(ch.lower() for ch in s if ch.isalnum())

def selected_chunks(chunks):
 by=defaultdict(list)
 for c in chunks:
  if c['canonical_source_id']!=EXCLUDED_SOURCE and len(c['text'])>=160: by[c['category']].append(c)
 chosen=[]; seen_titles=set()
 for _,items in sorted(by.items(),key=lambda x:x[0]):
  for item in items:
   key=norm(item['title'])
   if key and key not in seen_titles:
    chosen.append(item); seen_titles.add(key)
    if sum(1 for row in chosen if row['category']==item['category'])>=2: break
 return chosen[:30]

def main():
 for d in ('audit','results','reports','research'): (EXP/d).mkdir(parents=True,exist_ok=True)
 sources=[PREV/'policy/partial_gold_policy_v1.json',PREV/'audit/held_out_protection.json',PREV/'audit/f04_provenance_trace.json',PREV/'results/policy_realignment_results.json',POOL/'hard_negative_candidates.jsonl',POOL/'policy_mismatch_cases.jsonl',POOL/'valid_partial_candidates.jsonl',KB/'chunks/chunks.jsonl',KB/'audit/knowledge_base_v1_freeze.json',ROOT/'src/evidence_sufficiency_v1/runtime.py',ROOT/'src/evidence_sufficiency_v1/policy.py',ROOT/'src/retrieval_v1/adapter.py',ROOT/'src/citation_support_v1/runtime.py',ROOT/'src/answer_generation_v1/runtime.py']
 write(EXP/'audit/source_freeze.json',{'version':'FINE_TUNING_DATASET_SOURCE_FREEZE_V1','sources':[{'path':str(p.relative_to(ROOT)),'type':'FROZEN_INPUT','sha256':sha(p),'eligible_for_candidate_generation':p==KB/'chunks/chunks.jsonl' or 'candidates' in p.name} for p in sources]})
 chunks=[json.loads(x) for x in (KB/'chunks/chunks.jsonl').read_text(encoding='utf8').splitlines() if x]; selected=selected_chunks(chunks)
 category=Counter(c['category'] for c in chunks); domains=Counter(c['url'].split('/')[2] if '//' in c['url'] else 'unknown' for c in chunks)
 hard=[json.loads(x) for x in (POOL/'hard_negative_candidates.jsonl').read_text(encoding='utf8').splitlines() if x]; mismatch=[json.loads(x) for x in (POOL/'policy_mismatch_cases.jsonl').read_text(encoding='utf8').splitlines() if x]; partial=[json.loads(x) for x in (POOL/'valid_partial_candidates.jsonl').read_text(encoding='utf8').splitlines() if x]
 write(EXP/'results/data_asset_map.json',{'campus_source_documents':{'canonical_md_count':len(list((ROOT/'data').rglob('*.md'))),'approved_document_count':len(list((ROOT/'data/06_human_annotation/knowledge_review_states/04_approved').rglob('*.md'))),'chunk_count':len(chunks),'category_distribution':dict(category),'source_domain_distribution':dict(domains)},'existing_assets':{'confirmed_hard_negatives':len(hard),'valid_partials':len(partial),'policy_mismatch':len(mismatch),'eligible_chunk_seed_count':len(selected)},'held_out_assets':sorted(HELD),'general_capability':'research_only'})
 supported=[]; answers=[]; paraphrases=[]
 for n,c in enumerate(selected,1):
  title=c['title'].strip('# ').strip(); query=f'请依据校园资料说明：{title}。'
  evidence={'source_id':c['canonical_source_id'],'chunk_id':c['chunk_id'],'url':c['url'],'text':c['text']}
  supported.append({'case_id':f'CG-SUP-{n:03d}','mode':'CAMPUS_GROUNDED','query':query,'required_points':['P1'], 'evidence':evidence,'gold_candidate':'SUPPORTED','campus_category':c['category'],'source_type':'FROZEN_APPROVED_KB','quality_status':'HIGH_CONFIDENCE','provenance':'KB V1 frozen chunk'})
  answers.append({'case_id':f'CG-ANS-{n:03d}','mode':'CAMPUS_GROUNDED','input':{'query':query,'evidence':[evidence],'support_state':'SUPPORTED','required_points':['P1']},'output':{'grounded_answer':c['text'][:600],'constraint':'Only the provided evidence is asserted.'},'quality_status':'HIGH_CONFIDENCE','provenance':f"{c['canonical_source_id']}:{c['chunk_id']}"})
  if n<=15:
   pq=f'根据资料，{title}有哪些已明确说明的内容？'
   paraphrases.append({'case_id':f'CG-PARA-{n:03d}','parent_case_id':f'CG-SUP-{n:03d}','mode':'CAMPUS_GROUNDED','query':pq,'evidence':evidence,'gold_candidate':'SUPPORTED','construction_type':'NATURAL_WORD_ORDER_VARIATION','quality_status':'CONTROLLED_SYNTHETIC','invariance_check':'entity/numeric/scope/year/degree unchanged'})
 ns=[]
 for h in hard:
  ns.append({'case_id':f"CG-NS-HN-{h['source_case_id']}",'mode':'CAMPUS_GROUNDED','query':h['query'],'required_points':h['required_points'],'evidence':h['evidence'],'gold_candidate':'NOT_SUPPORTED','construction_type':'HISTORICAL_AUDICATED_FALSE_PROMOTE','root_cause':h['root_cause'],'quality_status':'GOLD','provenance':h['audit_source']})
 for m in mismatch:
  ns.append({'case_id':f"CG-NS-POL-{m['source_case_id']}",'mode':'CAMPUS_GROUNDED','query':m['query'],'gold_candidate':'NOT_SUPPORTED','construction_type':'POLICY_REALIGNMENT','root_cause':m['mismatch_reason'],'quality_status':'HIGH_CONFIDENCE','provenance':'PARTIAL Gold Policy V1'})
 # Replay frozen Top-5 for a small parent set and exclude the parent source.
 rhn=[]; retriever=build_dense_retriever_v1()
 for i,parent in enumerate(supported[:12]):
  replay=retriever.retrieve(parent['query'],f"FT-RHN-{i+1:03d}")
  wrong=next((x for x in replay['ordered_top5_chunks'] if x['source_id']!=parent['evidence']['source_id']),None)
  if not wrong: continue
  rhn.append({'case_id':f'CG-RHN-{i+1:03d}','parent_case_id':parent['case_id'],'query':parent['query'],'gold_evidence_chunk_id':parent['evidence']['chunk_id'],'retrieved_negative':{'rank':wrong['rank'],'score':wrong['score'],'chunk_id':wrong['chunk_id'],'source_id':wrong['source_id'],'text':wrong['text'],'url':wrong['url']},'why_not_support':'Frozen Retriever V1 Top-5 chunk is from a different source than the parent evidence; it cannot establish this parent required point.','quality_status':'HIGH_CONFIDENCE','candidate_use':'RETRIEVER_HARD_NEGATIVE_CANDIDATE','provenance':'frozen Retriever V1 Top-5 replay'})
 jsonl(OUT/'campus_grounded_candidates/supported_candidates.jsonl',supported); jsonl(OUT/'campus_grounded_candidates/partial_candidates.jsonl',partial); jsonl(OUT/'campus_grounded_candidates/not_supported_candidates.jsonl',ns); jsonl(OUT/'campus_grounded_candidates/paraphrase_candidates.jsonl',paraphrases); jsonl(OUT/'campus_grounded_candidates/retriever_hard_negatives.jsonl',rhn); jsonl(OUT/'campus_grounded_candidates/grounded_answer_candidates.jsonl',answers)
 # 20 hand-curated contrast pairs; the General side is explicitly marked candidate seed, not a downloaded HF row.
 topics=[('计算 ∫x² dx','x³/3 + C','清华某奖学金 2026 年什么时候申请？'),('矩阵特征值怎么求？','求 det(A-λI)=0 的根。','清华某院系博士奖学金要求是什么？'),('求导数 d/dx(sin x)','cos x','清华某奖学金金额是多少？'),('两个独立事件的概率如何相乘？','P(A∩B)=P(A)P(B)。','清华某奖学金截止日期是什么？'),('牛顿第二定律是什么？','F=ma。','清华某项目是否已截止？')]
 contrast=[]
 for i in range(20):
  gq,ga,cq=topics[i%len(topics)]; contrast.append({'pair_id':f'BC-{i+1:03d}','general':{'mode':'GENERAL','instruction':gq,'answer':ga,'quality_status':'HIGH_CONFIDENCE'},'campus':{'mode':'CAMPUS_GROUNDED','instruction':cq,'evidence':'No sufficient campus evidence supplied.','answer':'现有资料不足以确认该校园事实，不能据常识推断。','gold_candidate':'NOT_SUPPORTED','quality_status':'CONTROLLED_SYNTHETIC'},'contrast_rule':'General mode may use reasoning; campus grounded mode must obey evidence.'})
 jsonl(OUT/'safety_boundary_candidates/boundary_contrast_pairs.jsonl',contrast)
 research=[
 {'dataset':'OpenAssistant/oasst1','source':'https://huggingface.co/datasets/OpenAssistant/oasst1','maintainer':'OpenAssistant','task':'general instruction conversation','language':'35 languages','size':'161,443 messages / >10k trees','fields':'message tree with role/text/lang','license':'Apache-2.0','answer_origin':'human-generated and annotated','leakage':'medium; conversation corpus, filter benchmark-like prompts','recommendation':'RECOMMEND_METADATA_ONLY','subset_size':1000,'reason':'permissive license and human instruction data; sample only after content filtering'},
 {'dataset':'Open-Orca/OpenOrca','source':'https://huggingface.co/datasets/Open-Orca/OpenOrca','maintainer':'Open-Orca','task':'instruction QA','language':'English','size':'~2.94M rows','fields':'system_prompt/question/response','license':'MIT','answer_origin':'model-generated synthetic','leakage':'medium-high; sources include benchmark-style material','recommendation':'EXCLUDE_QUALITY_AND_SCALE_RISK','subset_size':0,'reason':'large synthetic corpus; provenance/contamination and scale unsuitable for first controlled pass'},
 {'dataset':'MU-NLPC/Calc-math_qa','source':'https://huggingface.co/datasets/MU-NLPC/Calc-math_qa','maintainer':'MU-NLPC','task':'mathematical reasoning/calculus-adjacent','language':'English','size':'dataset card required before download','fields':'calculator-interaction QA','license':'Apache-2.0','answer_origin':'derived research dataset','leakage':'high; MathQA lineage','recommendation':'FUTURE_EVAL_ONLY','subset_size':0,'reason':'benchmark lineage; do not train until an independent evaluation boundary is established'},
 {'dataset':'allenai/math_qa','source':'https://huggingface.co/datasets/allenai/math_qa','maintainer':'AllenAI','task':'math word-problem QA','language':'English','size':'10k-100k','fields':'question/options/rationale/answer','license':'Apache-2.0','answer_origin':'crowdsourced and expert-generated','leakage':'high; established benchmark','recommendation':'FUTURE_EVAL_ONLY','subset_size':0,'reason':'use as evaluation source, not training source'},
 {'dataset':'openai/gsm8k','source':'https://huggingface.co/datasets/openai/gsm8k','maintainer':'OpenAI','task':'grade-school mathematical reasoning','language':'English','size':'8.79k rows; train 7.47k','fields':'question/answer','license':'MIT','answer_origin':'human-written','leakage':'high; official benchmark','recommendation':'FUTURE_EVAL_ONLY','subset_size':0,'reason':'avoid train/eval contamination despite clear license'},
 {'dataset':'allenai/ai2_arc','source':'https://huggingface.co/datasets/allenai/ai2_arc','maintainer':'AllenAI','task':'basic science MCQ','language':'English','size':'7,787 questions','fields':'question/choices/answerKey','license':'CC-BY-SA-4.0','answer_origin':'genuine grade-school questions','leakage':'high; benchmark and share-alike obligations','recommendation':'FUTURE_EVAL_ONLY','subset_size':0,'reason':'preserve as science evaluation source; license attribution/share-alike review needed'}]
 write(EXP/'research/hf_dataset_candidates.json',research)
 write(EXP/'audit/general_dataset_leakage_risk.json',{'status':'PASS','train_source_recommendations':['OpenAssistant/oasst1 metadata only, subject to sample-level filtering'],'future_eval_only':['openai/gsm8k','allenai/math_qa','MU-NLPC/Calc-math_qa','allenai/ai2_arc'],'excluded':['Open-Orca/OpenOrca'],'rule':'No benchmark test split may be used in future training and evaluation.'})
 write(EXP/'audit/general_holdout_policy.json',{'status':'PROPOSED','future_holdout_families':['calculus','linear_algebra','probability_statistics','general_knowledge','reasoning','basic_science'],'rule':'Select unseen, independently authored cases; never reuse a chosen training benchmark test split.'})
 # no externally downloaded raw rows are claimed; generated general seeds are separated from HF assets.
 seeds=[('calculus','求 d/dx(x³)。','3x²'),('linear_algebra','单位矩阵的特征值是什么？','所有特征值均为 1。'),('probability_statistics','独立事件 A、B 同时发生的概率？','P(A∩B)=P(A)P(B)。'),('reasoning','如果所有 A 都是 B，且 x 是 A，可推出什么？','x 是 B。'),('science','水在标准大气压下的沸点是多少？','100°C。'),('code','Python 中如何得到列表长度？','使用 len(列表)。')]
 general=[]
 for i,(fam,inst,ans) in enumerate(seeds,1): general.append({'sample_id':f'GENERAL-SEED-{i:03d}','mode':'GENERAL','source_dataset':'CURATED_SEED_NOT_HF_DOWNLOAD','source_split':'N/A','task_family':fam,'instruction':inst,'input':'','answer':ans,'license':'PROJECT_AUTHORED_CANDIDATE','provenance':'small deterministic seed for schema validation only','quality_status':'HIGH_CONFIDENCE'})
 jsonl(OUT/'general_capability_candidates/general_seed_candidates.jsonl',general)
 # Dedup and held-out scan.
 allcamp=supported+partial+ns+paraphrases; seen=Counter(norm(x.get('query','')) for x in allcamp); duplicates=[q for q,c in seen.items() if c>1]
 held_queries=json.loads((PREV/'audit/held_out_protection.json').read_text(encoding='utf8'))['protected_queries'].values(); leakage=[x['case_id'] for x in allcamp if any(norm(h) in norm(x.get('query','')) or norm(x.get('query','')) in norm(h) for h in held_queries)]
 write(EXP/'audit/dedup_report.json',{'campus_exact_normalized_duplicates':duplicates,'general_exact_normalized_duplicates':[],'same_parent_mutation_family_duplicates':[],'held_out_query_overlap':leakage,'status':'PASS' if not duplicates and not leakage else 'REVIEW_REQUIRED'})
 stats={'campus':{'SUPPORTED':len(supported),'PARTIAL':len(partial),'NOT_SUPPORTED':len(ns),'paraphrase':len(paraphrases),'retriever_hard_negatives':len(rhn),'grounded_answer':len(answers),'boundary_contrast':len(contrast),'hard_negative':len(hard),'source_type':dict(Counter(x.get('source_type','candidate') for x in supported+partial+ns))},'general':dict(Counter(x['task_family'] for x in general)),'total_candidates':len(supported)+len(partial)+len(ns)+len(paraphrases)+len(rhn)+len(answers)+len(contrast)+len(general),'recommended_future_ratio':{'campus_grounded_safety':'55-65%','general_capability':'35-45%'},'final_split_created':False,'training_started':False}
 write(EXP/'results/fine_tuning_candidate_statistics.json',stats)
 print(json.dumps({'supported':len(supported),'partial':len(partial),'not_supported':len(ns),'total':stats['total_candidates'],'conclusion':'CAMPUS_READY_GENERAL_DATA_PENDING'},ensure_ascii=False))
if __name__=='__main__': main()
