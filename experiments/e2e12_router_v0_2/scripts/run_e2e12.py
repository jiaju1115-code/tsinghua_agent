from __future__ import annotations
import csv,json,os,re,statistics,sys,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse

REPO=Path(__file__).resolve().parents[3]; ROOT=Path(__file__).resolve().parents[1]
ROUTER=REPO/'experiments/router_v0_2'; WEB=REPO/'experiments/web_search_v0'; FOLLOW=REPO/'experiments/web_search_v0_followup'
GEN=REPO/'evaluation/answer_generation/v0'; VENDOR=GEN/'vendor'
sys.path[:0]=[str(ROUTER),str(WEB),str(VENDOR)]
from src.router_v0_2 import route  # type: ignore
sys.path.pop(0); sys.modules.pop('src',None)
sys.path.insert(0,str(WEB))
from src.tavily_client import TavilyWebClient  # type: ignore
from src.config import load_settings  # type: ignore
from src.query_rewriter import rewrite_academic_query,direct_answer_search_guard  # type: ignore
from src.ranking import rank_sources  # type: ignore
from src.source_quality import assess_source  # type: ignore
from src.evidence_span import extract_spans  # type: ignore
from llama_cpp import Llama  # type: ignore

def utc(): return datetime.now(timezone.utc).isoformat()
def append(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(obj,ensure_ascii=False)+'\n')
def safe_error(exc,key=''):
 s=f'{type(exc).__name__}: {exc}'
 if key:s=s.replace(key,key[:4]+'****************')
 return s[:500]
def retry_call(kind,fn,key,trace,sample_id,query):
 for attempt in (1,2):
  started=time.perf_counter()
  try:
   val=fn(); trace.append({'sample_id':sample_id,'operation':kind,'query':query,'attempt':attempt,'success':True,'latency_ms':round((time.perf_counter()-started)*1000,3),'timestamp':utc()}); return val,attempt,None
  except Exception as exc:
   err=safe_error(exc,key); trace.append({'sample_id':sample_id,'operation':kind,'query':query,'attempt':attempt,'success':False,'error':err,'latency_ms':round((time.perf_counter()-started)*1000,3),'timestamp':utc()})
   transient=any(x in err.lower() for x in ['timeout','timed out','connection','temporar','429','502','503','504'])
   if attempt==2 or not transient:return None,attempt,err
 return None,2,'unknown failure'
def model_path():
 files=list((Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct-GGUF').rglob('*.gguf'))
 if not files: raise RuntimeError('LOCAL_QWEN_MODEL_NOT_FOUND')
 return files[0]
def generate(llm,question,evidence):
 context='\n\n'.join(f"[C{i}] {e['title']}\n{e['span_text'][:650]}" for i,e in enumerate(evidence[:3],1)) or '[NO_EVIDENCE]'
 prompt=f"资料如下：\n{context}\n\n问题：{question}\n只依据资料回答；事实主张后标注[C1]-[C3]。资料不足时明确拒答。答案不超过180字。"
 t=time.perf_counter(); resp=llm.create_chat_completion(messages=[{'role':'system','content':'你是证据约束型问答助手。不得使用未给出的外部知识。'},{'role':'user','content':prompt}],temperature=0,max_tokens=220,seed=20260813); latency=(time.perf_counter()-t)*1000
 return resp['choices'][0]['message']['content'].strip(),round(latency,3)
def judge(llm,question,answer,evidence):
 context='\n'.join(f"[C{i}] {e['span_text'][:500]}" for i,e in enumerate(evidence[:3],1)) or '[NO_EVIDENCE]'
 prompt=f'''仅依据证据评估回答，输出JSON。correctness与faithfulness取0/1/2；claim_count和unsupported_claim_count为整数；evidence_sufficient、citation_support为布尔值；reason不超过60字。\n问题:{question}\n回答:{answer}\n证据:{context}'''
 try:
  r=llm.create_chat_completion(messages=[{'role':'system','content':'你是本地证据评估器，只输出JSON。'},{'role':'user','content':prompt}],temperature=0,max_tokens=180,response_format={'type':'json_object'},seed=20260813)
  raw=json.loads(r['choices'][0]['message']['content']); return {'correctness':max(0,min(2,int(raw.get('correctness',0)))),'faithfulness':max(0,min(2,int(raw.get('faithfulness',0)))),'claim_count':max(0,int(raw.get('claim_count',0))),'unsupported_claim_count':max(0,int(raw.get('unsupported_claim_count',0))),'evidence_sufficient':bool(raw.get('evidence_sufficient')),'citation_support':bool(raw.get('citation_support')),'reason':str(raw.get('reason',''))[:120],'scope':'PROVISIONAL_PROXY_LOCAL_SELF_EVAL'}
 except Exception as exc:return {'correctness':None,'faithfulness':None,'claim_count':None,'unsupported_claim_count':None,'evidence_sufficient':None,'citation_support':None,'reason':safe_error(exc),'scope':'PROVISIONAL_PROXY_BLOCKED'}
def main():
 try:
  from dotenv import load_dotenv; load_dotenv(WEB/'.env')
 except ImportError: pass
 key=os.getenv('TAVILY_API_KEY','').strip()
 if not key: raise SystemExit('TAVILY_API_KEY_NOT_CONFIGURED')
 settings=load_settings(); client=TavilyWebClient(settings); llm=Llama(model_path=str(model_path()),n_ctx=4096,n_threads=12,n_threads_batch=16,n_batch=2048,n_ubatch=512,n_gpu_layers=0,verbose=False,seed=20260813)
 frozen=json.loads((ROOT/'evaluation/e2e12_set.json').read_text(encoding='utf-8'))['samples']
 runlog=ROOT/'logs/e2e12_run_log.jsonl'; tracelog=ROOT/'logs/search_extract_trace.jsonl'
 rows=[json.loads(x) for x in runlog.read_text(encoding='utf-8').splitlines() if x.strip()] if runlog.exists() else []
 completed={x['sample_id'] for x in rows}
 for sample in frozen:
  if sample['sample_id'] in completed: continue
  trace=[]
  began=time.perf_counter(); sid=sample['sample_id']; q=sample['query']; r=route(q).to_dict(); actual=r['mode']; expected=sample['expected_route']; search_expected=actual not in {'NO_WEB_NEEDED','UNCERTAIN'}
  search_queries=[]
  if search_expected:
   if actual=='ACADEMIC_RETRIEVAL': search_queries=rewrite_academic_query(q).knowledge_queries[:2]
   else: search_queries=[q]
  sources=[]; search_calls=extract_calls=0; errors=[]
  for sq in search_queries:
   include=['tsinghua.edu.cn'] if actual=='CAMPUS_PUBLIC' else None
   raw,attempts,err=retry_call('search',lambda sq=sq,include=include:client.search_web(sq,actual,5,include),key,trace,sid,sq); search_calls+=attempts
   if err: errors.append(err)
   else: sources.extend(raw or [])
  sources=rank_sources(sources,actual,q) if sources else []
  selected=sources[:3]; pages={}
  if selected:
   urls=[s['url'] for s in selected]; pages,attempts,err=retry_call('extract',lambda:client.extract(urls),key,trace,sid,' | '.join(urls)); extract_calls+=attempts
   if err: errors.append(err); pages={}
  evidence=[]; usable=0
  for s in selected:
   content=(pages or {}).get(s['url'],''); ass=assess_source(s['url'],content); direct=actual=='ACADEMIC_RETRIEVAL' and direct_answer_search_guard(q,s.get('title',''),content)
   s.update({'content':content,'source_domain':urlparse(s['url']).netloc,'source_title':s.get('title',''),'source_url':s['url'],'source_authority_level':ass.authority,'content_length':len(content),'extraction_status':ass.verdict,'possible_direct_answer_flag':bool(direct),'quality_reasons':ass.reasons})
   if ass.verdict!='REJECT' and not direct:
    usable+=1; evidence.extend(extract_spans(content,query=q,mode=actual,url=s['url'],title=s.get('title',''),authority=ass.authority))
  answer,gen_ms=generate(llm,q,evidence)
  proxy=judge(llm,q,answer,evidence)
  cites=sorted(set(re.findall(r'\[C([1-3])\]',answer))); valid=all(1<=int(x)<=min(3,len(evidence)) for x in cites) if cites else False
  refusal=bool(re.search(r'资料不足|无法确认|证据不足|无法根据',answer))
  infra=bool(errors) and not sources
  evidence_sufficient=bool(evidence) if proxy['evidence_sufficient'] is None else bool(proxy['evidence_sufficient'])
  primary=None
  if actual!=expected: primary='R'
  elif search_expected and not sources: primary='I' if infra else 'S'
  elif selected and not any(s['content_length']>=120 for s in selected): primary='X'
  elif search_expected and not evidence_sufficient: primary='E'
  elif proxy['correctness'] is not None and proxy['correctness']<2 and not (refusal and not evidence_sufficient): primary='G'
  elif evidence_sufficient and (not cites or not valid or not proxy.get('citation_support')): primary='C'
  row={**sample,'actual_route':actual,'route_correct':actual==expected,'router_reason':r['router_reason'],'search_expected':search_expected,'search_called':bool(search_queries),'search_provider':'Tavily' if search_queries else None,'search_query':search_queries,'search_call_count':search_calls,'search_success':bool(sources) if search_expected else None,'extract_called':bool(selected),'extract_call_count':extract_calls,'extract_success':any(s['content_length']>=120 for s in selected) if selected else None,'retrieved_source_count':len(sources),'usable_source_count':usable,'source_urls':[s['url'] for s in selected],'source_domains':[s['source_domain'] for s in selected],'source_titles':[s['source_title'] for s in selected],'sources':selected,'evidence':evidence,'evidence_sufficient':evidence_sufficient,'answer_generated':True,'final_answer':answer,'citation_count':len(cites),'citation_valid':valid,'citation_supports_claim':proxy.get('citation_support'),'answer_correctness':proxy.get('correctness'),'faithfulness':proxy.get('faithfulness'),'total_claims':proxy.get('claim_count'),'unsupported_claim_count':proxy.get('unsupported_claim_count'),'correct_refusal':refusal and not evidence_sufficient,'generation_latency_ms':gen_ms,'total_latency_ms':round((time.perf_counter()-began)*1000,3),'primary_failure_stage':primary,'secondary_failure_stage':None,'evaluation_scope':proxy['scope'],'evaluation_reason':proxy['reason'],'errors':errors,'retrieval_timestamp':utc()}
  rows.append(row); append(runlog,row)
  for t in trace: append(tracelog,t)
  print(json.dumps({'sample_id':sid,'route':actual,'search':row['search_success'],'extract':row['extract_success'],'failure':primary,'latency_ms':row['total_latency_ms']},ensure_ascii=False),flush=True)
 (ROOT/'results/e2e12_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8'); (ROOT/'results/e2e12_case_matrix.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 fields=['sample_id','category','academic_subject','query','expected_route','actual_route','route_correct','search_called','search_call_count','search_success','extract_called','extract_call_count','extract_success','retrieved_source_count','usable_source_count','evidence_sufficient','answer_generated','answer_correctness','faithfulness','total_claims','unsupported_claim_count','citation_count','citation_valid','citation_supports_claim','correct_refusal','total_latency_ms','primary_failure_stage','evaluation_scope','notes']
 with (ROOT/'results/e2e12_case_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
  for x in rows:w.writerow(x)
 def metrics(part):
  n=len(part); searches=[x for x in part if x['search_expected']]; extracts=[x for x in part if x['extract_called']]; claims=sum(x['total_claims'] or 0 for x in part); uns=sum(x['unsupported_claim_count'] or 0 for x in part); judged=[x for x in part if x['answer_correctness'] is not None]
  return {'count':n,'route_accuracy':sum(x['route_correct'] for x in part)/n if n else None,'search_trigger_rate':sum(x['search_called'] for x in part)/n if n else None,'search_success_rate':sum(bool(x['search_success']) for x in searches)/len(searches) if searches else None,'extract_success_rate':sum(bool(x['extract_success']) for x in extracts)/len(extracts) if extracts else None,'evidence_sufficiency_rate':sum(x['evidence_sufficient'] for x in part)/n if n else None,'answer_correctness_mean_0_to_2':sum(x['answer_correctness'] for x in judged)/len(judged) if judged else None,'faithfulness_mean_0_to_2':sum(x['faithfulness'] for x in judged)/len(judged) if judged else None,'unsupported_claim_rate':uns/claims if claims else 0.0,'citation_presence_rate':sum(x['citation_count']>0 for x in part)/n if n else None,'citation_validity_rate':sum(x['citation_valid'] for x in part)/n if n else None,'citation_support_rate':sum(bool(x['citation_supports_claim']) for x in part)/n if n else None,'correct_refusal_count':sum(x['correct_refusal'] for x in part),'mean_latency_ms':statistics.mean(x['total_latency_ms'] for x in part) if n else None,'median_latency_ms':statistics.median(x['total_latency_ms'] for x in part) if n else None,'false_academic':sum(x['actual_route']=='ACADEMIC_RETRIEVAL' and x['expected_route']!='ACADEMIC_RETRIEVAL' for x in part),'missed_academic':sum(x['actual_route']!='ACADEMIC_RETRIEVAL' and x['expected_route']=='ACADEMIC_RETRIEVAL' for x in part),'failure_stages':dict(Counter(x['primary_failure_stage'] for x in part if x['primary_failure_stage'])),'search_calls':sum(x['search_call_count'] for x in part),'extract_calls':sum(x['extract_call_count'] for x in part),'evaluation_scope':'PROVISIONAL_PROXY_LOCAL_SELF_EVAL'}
 out={'overall':metrics(rows)}
 for cat in ['ACADEMIC','CAMPUS','GENERAL','HARD_NEGATIVE']:out[cat.lower()]=metrics([x for x in rows if x['category']==cat])
 (ROOT/'results/e2e12_metrics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
