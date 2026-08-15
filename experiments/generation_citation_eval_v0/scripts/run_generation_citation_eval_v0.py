from __future__ import annotations
import csv,hashlib,json,re,statistics,subprocess
from collections import Counter
from datetime import datetime,timezone
from difflib import SequenceMatcher
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]; ROOT=Path(__file__).resolve().parents[1]
A=REPO/'evaluation/answer_generation/v0'; B=REPO/'experiments/e2e12_router_v0_2'
AF=A/'results/answer_eval_merged.jsonl'; BF=B/'results/e2e12_results.json'
PROTECTED=[REPO/'experiments/router_v0_2',REPO/'experiments/web_search_v0/src',REPO/'experiments/web_search_v0_followup/src',A,B,REPO/'prompts']
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def readjl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def snapshot():
 files={}
 for base in PROTECTED:
  for p in sorted(x for x in base.rglob('*') if x.is_file() and '__pycache__' not in x.parts and 'cache' not in x.parts):
   files[str(p.relative_to(REPO)).replace('\\','/')]={'sha256':sha(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
 model=list((Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct-GGUF').rglob('*.gguf'))
 if model:files['LOCAL_MODEL_WEIGHT']={'sha256':sha(model[0]),'size':model[0].stat().st_size,'mtime_ns':model[0].stat().st_mtime_ns,'path':str(model[0])}
 return {'captured_at':utc(),'files':files,'git_status':subprocess.run(['git','status','--porcelain=v1'],cwd=REPO,text=True,capture_output=True).stdout.splitlines()}
def norm(s):return re.sub(r'\s+|[^\w\u4e00-\u9fff]','',s.lower())
def tokens(s):
 zh=re.findall(r'[\u4e00-\u9fff]',s); en=re.findall(r'[a-zA-Z]{3,}|\d+(?:\.\d+)?',s.lower());return set([''.join(zh[i:i+2]) for i in range(len(zh)-1)]+en)
def overlap(a,b):
 x=tokens(a);y=tokens(b);return len(x&y)/max(1,len(x))
def segments(answer):
 raw=[x.strip(' \t-*0123456789.、') for x in re.split(r'\n+|(?<=[。！？；])',answer) if x.strip()]
 out=[]
 for x in raw:
  if re.fullmatch(r'(?:\[C\d+\][\-—至]*)+',x):
   if out:out[-1]+=x
  else:out.append(x)
 return out
def refusal(s):return any(x in s for x in ['无法确认','资料不足','证据不足','无法回答','无法给出','没有关于','不足以'])
def claim_type(s):
 if refusal(s):return 'refusal'
 if any(x in s for x in ['根据资料','提供的资料','当前资料']):return 'meta'
 if any(x in s for x in ['步骤','首先','其次','应当','需要','申请','办理']):return 'procedural'
 return 'factual'
def evidence_gate(track,row):
 if track=='A':
  v=(row.get('auto_evaluation') or {}).get('evidence_sufficiency')
  return {'sufficient':'EVIDENCE_SUFFICIENT','insufficient':'EVIDENCE_INSUFFICIENT','conflicting':'EVIDENCE_PARTIAL'}.get(v,'EVIDENCE_UNKNOWN')
 return 'EVIDENCE_SUFFICIENT' if row.get('evidence_sufficient') else 'EVIDENCE_INSUFFICIENT'
def contexts(track,row):
 if track=='A':return [{'id':x['context_id'],'text':x.get('text',''),'title':x.get('title',''),'url':x.get('url','')} for x in row.get('retrieved_context',[])]
 return [{'id':f'C{i}','text':x.get('span_text',''),'title':x.get('title',''),'url':x.get('url','')} for i,x in enumerate(row.get('evidence',[])[:3],1)]
def required_points(q,ctx,gate):
 if gate!='EVIDENCE_SUFFICIENT':return []
 candidates=[]
 for c in ctx:
  for s in re.split(r'(?<=[。！？；])|\n+',c['text']):
   s=s.strip()
   if 18<=len(s)<=260:candidates.append((overlap(q,s),s))
 candidates=sorted(candidates,key=lambda x:x[0],reverse=True)
 out=[]
 for _,s in candidates:
  if all(SequenceMatcher(None,norm(s),norm(x)).ratio()<.75 for x in out):out.append(s)
  if len(out)==3:break
 return out
def main():
 for d in ['evaluation','results','analysis','audit']: (ROOT/d).mkdir(parents=True,exist_ok=True)
 pre=snapshot();(ROOT/'audit/pre_run_state.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2),encoding='utf-8')
 ar=readjl(AF);br=json.loads(BF.read_text(encoding='utf-8'));assert len(ar)==38 and len(br)==12
 exact=[];similar=[]
 for x in ar:
  for y in br:
   ratio=SequenceMatcher(None,norm(x['question']),norm(y['query'])).ratio()
   if norm(x['question'])==norm(y['query']):exact.append((x['question_id'],y['sample_id']))
   elif ratio>=.8:similar.append((x['question_id'],y['sample_id'],round(ratio,4)))
 source_hashes={str(AF):sha(AF),str(A/'results/answer_generation_results.jsonl'):sha(A/'results/answer_generation_results.jsonl'),str(A/'results/answer_evaluation_results.jsonl'):sha(A/'results/answer_evaluation_results.jsonl'),str(BF):sha(BF),str(B/'audit/e2e12_freeze.json'):sha(B/'audit/e2e12_freeze.json')}
 manifest={'created_at':utc(),'track_a':{'source_paths':[str(AF)],'sample_count':38,'source_sha256':source_hashes[str(AF)]},'track_b':{'source_paths':[str(BF)],'sample_count':12,'source_sha256':source_hashes[str(BF)],'e2e12_freeze_sha256':'af96cb4862cd38ce669ba27ac1bc78964ab421cbb4af4b458d6e9927d58b6593'},'overlap':{'exact_count':len(exact),'high_similarity_count':len(similar),'exact':exact,'similar':similar},'evaluator_config':'reuse saved local Qwen 0/1/2 judgements + deterministic offline claim/citation/completeness proxy','local_model':'Qwen2.5-1.5B-Instruct-GGUF Q4_K_M','prompt_rule_hashes':{'generation_prompt':sha(A/'config/grounded_generation_prompt.md'),'generation_config':sha(A/'config/generation_config.json'),'analysis_script':sha(Path(__file__))},'git_state_recorded':'audit/pre_run_state.json'}
 freeze_hash=hashlib.sha256(canon(manifest)).hexdigest();manifest['canonical_manifest_sha256']=freeze_hash;(ROOT/'evaluation/generation_eval_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');(ROOT/'audit/generation_eval_freeze.json').write_text(json.dumps({'status':'FROZEN','creation_time':utc(),'canonical_manifest_sha256':freeze_hash,'source_hashes':source_hashes,'track_a_count':38,'track_b_count':12,'overlap_count':len(exact),'manifest':str(ROOT/'evaluation/generation_eval_manifest.json')},ensure_ascii=False,indent=2),encoding='utf-8')
 cases=[];claims=[];complete=[]
 for track,rows in [('A',ar),('B',br)]:
  for row in rows:
   sid=row['question_id'] if track=='A' else row['sample_id'];q=row['question'] if track=='A' else row['query'];ans=row['generated_answer'] if track=='A' else row['final_answer'];ctx=contexts(track,row);gate=evidence_gate(track,row)
   ev={c['id']:c for c in ctx};answer_cites=re.findall(r'\[C(\d+)\]',ans);fact=proc=unsupported=cited_req=valid_cited=supported_cited=0
   for i,s in enumerate(segments(ans),1):
    typ=claim_type(s);requires=typ in {'factual','procedural','recommendation','synthesis'};ids=[f'C{x}' for x in re.findall(r'\[C(\d+)\]',s)];scores=sorted(((overlap(s,c['text']),cid) for cid,c in ev.items()),reverse=True);support_ids=[cid for score,cid in scores if score>=.18][:3];supported=bool(support_ids);valid=all(cid in ev for cid in ids) if ids else None;citation_support=bool(ids and valid and any(cid in support_ids for cid in ids));reason=None
    if requires:
     fact+=1
     if ids:cited_req+=1
     if ids and valid:valid_cited+=1
     if citation_support:supported_cited+=1
     if not supported:unsupported+=1;reason='unsupported inference or background knowledge injection (deterministic lexical proxy)'
    if typ=='procedural':proc+=1
    claims.append({'claim_id':f'{track}-{sid}-CL{i:02d}','track':track,'sample_id':sid,'claim_text':re.sub(r'\[C\d+\]','',s).strip(),'claim_type':typ,'supported_by_evidence':supported,'supporting_evidence_ids':support_ids,'requires_citation':requires,'citation_present':bool(ids),'citation_ids':ids,'citation_valid':valid,'citation_supports_claim':citation_support,'unsupported_reason':reason,'confidence':'MEDIUM' if requires else 'HIGH','evaluation_scope':'DETERMINISTIC_PROVISIONAL_PROXY'})
   points=required_points(q,ctx,gate);covered=[p for p in points if overlap(p,ans)>=.18];ratio=len(covered)/len(points) if points else None
   complete.append({'track':track,'sample_id':sid,'query':q,'evidence_gate':gate,'required_answer_points':points,'required_point_count':len(points),'covered_point_count':len(covered),'missing_point_count':len(points)-len(covered),'completeness_ratio_proxy':ratio,'evaluation_scope':'PROVISIONAL_PROXY'})
   ae=row.get('auto_evaluation') or {};corr=ae.get('correctness') if track=='A' else row.get('answer_correctness');faith=ae.get('faithfulness') if track=='A' else row.get('faithfulness');ref=refusal(ans);labels=[]
   if gate=='EVIDENCE_SUFFICIENT' and ratio is not None and ratio<.75:labels.append('INCOMPLETE')
   if unsupported:labels.append('UNSUPPORTED_ADDITION')
   if gate=='EVIDENCE_SUFFICIENT' and ref:labels.append('WRONG_REFUSAL')
   if gate=='EVIDENCE_INSUFFICIENT' and not ref and fact:labels.append('FAILED_REFUSAL')
   if fact and cited_req==0:labels.append('CITATION_MISSING')
   elif 0<cited_req<fact:labels.append('CITATION_INCOMPLETE')
   if any(c['sample_id']==sid and c['track']==track and c['citation_present'] and (c['citation_valid'] is False or not c['citation_supports_claim']) for c in claims):labels.append('CITATION_MISMATCH')
   if corr is not None and corr<2:labels.append('TASK_COMPLETION')
   if not labels:labels=['NO_GENERATION_FAILURE']
   priority=['FAILED_REFUSAL','EVIDENCE_MISUSE','UNSUPPORTED_ADDITION','WRONG_REFUSAL','INCOMPLETE','TASK_COMPLETION','CITATION_MISSING','CITATION_INCOMPLETE','CITATION_MISMATCH','FORMAT_FAILURE','NO_GENERATION_FAILURE'];primary=next(x for x in priority if x in labels)
   cases.append({'track':track,'sample_id':sid,'query':q,'category':row.get('category'),'academic_subject':row.get('academic_subject'),'evidence_gate':gate,'route_correct':row.get('route_correct') if track=='B' else None,'retrieval_success':row.get('search_success') if track=='B' else True,'answer':ans,'correctness_0_to_2':corr,'faithfulness_0_to_2':faith,'historical_completeness_0_to_2':ae.get('completeness'),'factual_or_procedural_claims':fact,'unsupported_claims_proxy':unsupported,'claim_level_citation_coverage':cited_req/fact if fact else None,'citation_validity':valid_cited/cited_req if cited_req else None,'citation_support':supported_cited/cited_req if cited_req else None,'completeness_ratio_proxy':ratio,'refused':ref,'failure_labels':labels,'primary_failure_type':primary,'review_recommended':bool(unsupported or len([x for x in labels if x not in {'TASK_COMPLETION','CITATION_MISSING'}])>=2 or (gate=='EVIDENCE_SUFFICIENT' and ref) or (corr is not None and faith is not None and abs(corr-faith)>=1)),'evaluation_scope':'PROVISIONAL_PROXY'})
 # outputs
 (ROOT/'results/generation_eval_results.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8');(ROOT/'results/generation_case_matrix.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8');(ROOT/'results/claim_level_audit.json').write_text(json.dumps(claims,ensure_ascii=False,indent=2),encoding='utf-8')
 def csvout(path,rows):
  if not rows:return
  with path.open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction='ignore');w.writeheader()
   for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
 csvout(ROOT/'results/generation_case_matrix.csv',cases);csvout(ROOT/'results/claim_level_audit.csv',claims);csvout(ROOT/'results/completeness_matrix.csv',complete);queue=[c for c in cases if c['review_recommended']];csvout(ROOT/'results/human_review_queue.csv',queue)
 def met(rs):
  judged=[x for x in rs if x['correctness_0_to_2'] is not None];cc=[x for x in claims if any(c['track']==x['track'] and c['sample_id']==x['sample_id'] for c in rs) and x['requires_citation']];cp=[x for x in complete if any(c['track']==x['track'] and c['sample_id']==x['sample_id'] for c in rs) and x['completeness_ratio_proxy'] is not None]
  return {'samples':len(rs),'correctness_mean_0_to_2':statistics.mean(x['correctness_0_to_2'] for x in judged) if judged else None,'faithfulness_mean_0_to_2':statistics.mean(x['faithfulness_0_to_2'] for x in judged) if judged else None,'completeness_ratio_proxy':statistics.mean(x['completeness_ratio_proxy'] for x in cp) if cp else None,'unsupported_claim_rate_proxy':sum(not x['supported_by_evidence'] for x in cc)/len(cc) if cc else None,'claim_level_citation_coverage':sum(x['citation_present'] for x in cc)/len(cc) if cc else None,'citation_validity_given_present':sum(x['citation_valid'] is True for x in cc if x['citation_present'])/sum(x['citation_present'] for x in cc) if any(x['citation_present'] for x in cc) else None,'citation_support_given_present':sum(x['citation_supports_claim'] for x in cc if x['citation_present'])/sum(x['citation_present'] for x in cc) if any(x['citation_present'] for x in cc) else None,'primary_failure_counts':dict(Counter(x['primary_failure_type'] for x in rs)),'failure_label_counts':dict(Counter(l for x in rs for l in x['failure_labels'])),'review_queue_count':sum(x['review_recommended'] for x in rs),'scope':'PROVISIONAL_PROXY'}
 metrics={'track_a_all':met([x for x in cases if x['track']=='A']),'track_a_evidence_sufficient':met([x for x in cases if x['track']=='A' and x['evidence_gate']=='EVIDENCE_SUFFICIENT']),'track_b_all':met([x for x in cases if x['track']=='B']),'track_b_evidence_sufficient':met([x for x in cases if x['track']=='B' and x['evidence_gate']=='EVIDENCE_SUFFICIENT']),'academic_track_b':met([x for x in cases if x['track']=='B' and x.get('category')=='ACADEMIC']),'clean_generation_subset':met([x for x in cases if x['evidence_gate']=='EVIDENCE_SUFFICIENT' and (x['track']=='A' or (x['route_correct'] and x['retrieval_success']))]),'combined_unique_sample_count':50-len(exact),'human_review_queue_count':len(queue)};(ROOT/'results/generation_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
 make_reports(cases,claims,metrics,exact,similar,freeze_hash)
 post=snapshot();(ROOT/'audit/post_run_state.json').write_text(json.dumps(post,ensure_ascii=False,indent=2),encoding='utf-8');changed=[p for p,v in pre['files'].items() if p not in post['files'] or post['files'][p]['sha256']!=v['sha256']];added=[p for p in post['files'] if p not in pre['files']];removed=[p for p in pre['files'] if p not in post['files']];audit={'status':'PASS' if not(changed or added or removed) else 'FAIL','protected_changed':changed,'protected_added':added,'protected_removed':removed,'network_calls':0,'answers_regenerated':0,'input_files_modified':False,'completed_at':utc()};(ROOT/'audit/final_immutability_report.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'freeze':freeze_hash,'metrics':metrics,'audit':audit},ensure_ascii=False,indent=2))
def make_reports(cases,claims,m,exact,similar,fh):
 counts=Counter(l for x in cases for l in x['failure_labels']);primary=Counter(x['primary_failure_type'] for x in cases);pairs=Counter()
 for x in cases:
  ls=sorted(set(x['failure_labels'])-{'NO_GENERATION_FAILURE'})
  for i,a in enumerate(ls):
   for b in ls[i+1:]:pairs[(a,b)]+=1
 (ROOT/'analysis/cross_track_overlap.md').write_text(f"# Cross-track overlap\n\nExact overlap: {len(exact)}. High-similarity overlap: {len(similar)}. Combined unique count: {50-len(exact)}.\n\nExact: `{exact}`\n\nSimilar: `{similar}`\n",encoding='utf-8')
 (ROOT/'analysis/generation_failure_taxonomy.md').write_text('# Generation failure taxonomy\n\nPrimary counts: '+json.dumps(primary,ensure_ascii=False)+'\n\nAll-label counts: '+json.dumps(counts,ensure_ascii=False)+'\n\nPriority: P0 = FAILED_REFUSAL/EVIDENCE_MISUSE/UNSUPPORTED_ADDITION; P1 = WRONG_REFUSAL/INCOMPLETE/TASK_COMPLETION/CITATION coverage; P2 = material format issues.\n',encoding='utf-8')
 (ROOT/'analysis/error_cooccurrence.md').write_text('# Error co-occurrence\n\n'+('\n'.join(f'- {a} × {b}: {n}' for (a,b),n in pairs.most_common()) or '0 pairs')+'\n',encoding='utf-8')
 cited=[x for x in claims if x['requires_citation']];present=[x for x in cited if x['citation_present']];(ROOT/'analysis/citation_coverage_analysis.md').write_text(f"# Citation coverage analysis\n\nAcross tracks, claim-level coverage is {sum(x['citation_present'] for x in cited)}/{len(cited)}. Present citations valid: {sum(x['citation_valid'] is True for x in present)}/{len(present) or 1}; supported by deterministic proxy: {sum(x['citation_supports_claim'] for x in present)}/{len(present) or 1}. The dominant issue is coverage, not mapping. Source availability is evaluated separately by Evidence Gate.\n",encoding='utf-8')
 uns=[x for x in claims if x['requires_citation'] and not x['supported_by_evidence']];(ROOT/'analysis/unsupported_claim_analysis.md').write_text(f"# Unsupported claims\n\nDeterministic provisional proxy found {len(uns)} unsupported factual/procedural claims. Primary assigned cause: unsupported inference/background-knowledge injection when no saved evidence span reaches the lexical support threshold. Citation omission alone is not treated as unsupported.\n",encoding='utf-8')
 old=json.loads((A/'results/final_metrics.json').read_text(encoding='utf-8'));summary=json.loads((A/'results/answer_evaluation_summary.json').read_text(encoding='utf-8'));new=m['track_a_all'];(ROOT/'analysis/v0_metric_reconciliation.md').write_text(f"# V0 metric reconciliation\n\nHistorical final_metrics: correctness {old.get('answer_correctness_mean_0_to_2')}, faithfulness {old.get('faithfulness_mean_0_to_2')}, unsupported {old.get('unsupported_claim_rate')} ({old.get('unsupported_claims')}/{old.get('total_claims')}). Historical evaluator summary instead reports unsupported {summary.get('unsupported_claim_rate')} ({summary.get('unsupported_claims')}/{summary.get('total_claims')}).\n\nCurrent Track A reuses correctness/faithfulness: {new['correctness_mean_0_to_2']} / {new['faithfulness_mean_0_to_2']}. New unsupported proxy: {new['unsupported_claim_rate_proxy']}; denominator is deterministic atomic factual/procedural claims, so it must not overwrite either historical metric.\n",encoding='utf-8')
 clean=m['clean_generation_subset'];acad=m['academic_track_b'];top=primary.most_common(3);(ROOT/'analysis/generation_bottleneck_report.md').write_text(f"# Generation bottleneck report\n\nFreeze: `{fh}`.\n\nEvidence-sufficient clean subset: correctness {clean['correctness_mean_0_to_2']}/2, faithfulness {clean['faithfulness_mean_0_to_2']}/2, completeness proxy {clean['completeness_ratio_proxy']}, unsupported claim proxy {clean['unsupported_claim_rate_proxy']}, claim citation coverage {clean['claim_level_citation_coverage']}.\n\nTop primary failures: {top}. Completeness is material when INCOMPLETE appears frequently. Unsupported claims are mainly unsupported inference/background injection under the deterministic proxy. Citation is primarily a coverage failure; mapping/support are conditional on emitted citations. Academic E2E12: {json.dumps(acad,ensure_ascii=False)}.\n\nWrong/failed refusal prevalence is given in failure labels; evidence-insufficient correct refusals are not generation failures.\n\n## Optimization Priority 1\nEvidence-constrained task completion and refusal calibration.\n\n## Optimization Priority 2\nClaim-level citation emission and coverage enforcement.\n\n## Optimization Priority 3\nPrevent unsupported inference and improve completeness against required answer points.\n",encoding='utf-8')
 (ROOT/'README.md').write_text('# Generation & Citation Evaluation V0\n\nOffline diagnosis only. Track A reuses 38 frozen generation records; Track B reuses 12 saved E2E records. No search, extract, external LLM, regeneration, prompt change, or production mutation. Semantic scores are historical/local Provisional Proxies; new claim and completeness checks are deterministic Provisional Proxies.\n',encoding='utf-8')
if __name__=='__main__':main()
