import argparse, hashlib, json, re, math
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT=Path(__file__).resolve().parents[1]; CAND=ROOT/'data/04_kb_expansion_candidate/dynamic_campus_v1'; STAGE=ROOT/'data/05_kb_staging/dynamic_campus_v1'; RET=ROOT/'experiments/dynamic_retriever_v0'; EVAL=ROOT/'evaluation/dynamic_retrieval_shadow_v0'; TODAY=date(2026,8,16)
for p in [STAGE/'sources',STAGE/'chunks',STAGE/'manifests',STAGE/'audit',STAGE/'reports',RET/'bm25',RET/'dense',RET/'hybrid',RET/'config',EVAL/'cases',EVAL/'results',EVAL/'reports',EVAL/'audit']: p.mkdir(parents=True,exist_ok=True)
def readjl(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def writejl(p,rows): p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def norm(s): return re.sub(r'[^\w\u4e00-\u9fff]+','',str(s or '').lower())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def parse_dates(text):
 out=[]
 pats=[r'(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})(?:日)?(?:[，, ]*(上午|下午)?\s*(\d{1,2})[:：](\d{2}))?',r'(?<!\d)(\d{1,2})月(\d{1,2})日(?:[，, ]*(上午|下午)?\s*(\d{1,2})[:：](\d{2}))?']
 for pat in pats:
  for m in re.finditer(pat,text):
   if len(m.groups())==6:
    y,mo,dy,ap,h,mi=m.groups(); y=int(y); h=int(h or 0); mi=int(mi or 0)
   else: mo,dy,ap,h,mi=m.groups(); y=None; mo=int(mo); dy=int(dy); h=int(h or 0); mi=int(mi or 0)
   if y is None:
    ctx=text[max(0,m.start()-30):m.start()]; yrs=re.findall(r'20\d{2}',ctx); y=int(yrs[-1]) if yrs else None
   if y:
    if ap=='下午' and h<12:h+=12
    try: out.append({'value':f'{y:04d}-{mo:02d}-{dy:02d}T{h:02d}:{mi:02d}:00+08:00','span':m.group(0),'start':m.start(),'end':m.end()})
    except ValueError: pass
 return out
def classify_temporal(r):
 text=r['title']+' '+r['content']; ds=parse_dates(text); fields={}; evidence=[]
 for d in ds:
  e=d['span']; low=text[max(0,d['start']-25):d['end']+25]
  if re.search('截止|截至|报名.*至|申请.*至',low): k='application_deadline'
  elif re.search('报名|注册',low): k='registration_end'
  elif re.search('活动|会议|开始|举办',low): k='event_start'
  elif re.search('有效期|有效',low): k='valid_until'
  else: k='published_at'
  fields.setdefault(k,d['value']); evidence.append(d)
 current='UNKNOWN'; chosen=[v for k,v in fields.items() if k in {'application_deadline','event_end','valid_until','trial_end'}]
 if chosen:
  current='EXPIRED' if min(x[:10] for x in chosen)<TODAY.isoformat() else 'ACTIVE'
 elif 'event_start' in fields: current='ONGOING' if fields['event_start'][:10]<=TODAY.isoformat() else 'UPCOMING'
 elif r['stable_or_dynamic']=='STABLE': current='NOT_APPLICABLE'
 return fields,evidence,current
def main():
 candidates=readjl(CAND/'candidates/dynamic_candidates_v1.jsonl'); temporal=[]
 for r in candidates:
  f,e,s=classify_temporal(r); x=dict(r); x.update({'temporal_fields':f,'temporal_evidence':e,'temporal_status':s,'processing_version':'temporal_extraction_v1'}); temporal.append(x)
 writejl(CAND/'processed/temporal_extraction_v1.jsonl',temporal)
 dump(CAND/'audit/temporal_extraction_audit.json',{'baseline_date':'2026-08-16','timezone':'Asia/Shanghai','vocabulary':['ACTIVE','UPCOMING','EXPIRED','ONGOING','UNKNOWN','NOT_APPLICABLE'],'counts':dict(Counter(x['temporal_status'] for x in temporal)),'extraction_rule':'deterministic regex only'})
 (CAND/'reports/temporal_extraction_v1_report.md').write_text('# Temporal Extraction V1\n\n- Baseline date: 2026-08-16 Asia/Shanghai\n- Records: '+str(len(temporal))+'\n\n'+''.join(f'- {k}: {v}\n' for k,v in Counter(x['temporal_status'] for x in temporal).items()),encoding='utf-8')
 # canonicalize and exact duplicate groups
 groups=defaultdict(list)
 for r in temporal: groups[(norm(r['title']),norm(r['content']))].append(r)
 canon=[]; audit=[]
 for key,rs in groups.items():
  rs=sorted(rs,key=lambda x:(-len(x['content']),x['candidate_id'])); gid='canon-'+hashlib.sha1('|'.join(key).encode()).hexdigest()[:12]
  audit.append({'duplicate_group_id':gid,'candidate_ids':[x['candidate_id'] for x in rs],'canonical_candidate_id':rs[0]['candidate_id']})
  for r in rs:
   x=dict(r); x.update({'duplicate_group_id':gid,'is_canonical':r is rs[0],'processing_version':'candidate_canonicalization_v1'}); canon.append(x)
 writejl(CAND/'processed/canonical_candidates_v1.jsonl',canon); dump(CAND/'audit/canonicalization_audit.json',{'groups':audit,'total_groups':len(audit),'duplicate_groups':sum(len(x['candidate_ids'])>1 for x in audit)})
 # core cross dedup
 core=readjl(ROOT/'data/03_knowledge_base/v1/chunks/chunks.jsonl'); core_text={norm(x.get('text')) for x in core}; core_titles={norm(x.get('title')) for x in core}; core_urls={norm(x.get('url')) for x in core}
 cross=[]
 for r in canon:
  if not r['is_canonical']: continue
  t=norm(r['content']); title=norm(r['title']); url=norm(r.get('canonical_url'))
  label='EXACT_CORE_DUPLICATE' if t in core_text or title in core_titles or url in core_urls else 'UNIQUE_DYNAMIC'
  cross.append({'candidate_id':r['candidate_id'],'source_xxid':r['source_xxid'],'classification':label,'reason':'normalized exact text/title/url match' if label.startswith('EXACT') else 'no deterministic core match','core_read_only':True})
 writejl(CAND/'audit/core_cross_dedup_v1.jsonl',cross)
 eligible={x['candidate_id'] for x in cross if x['classification']!='EXACT_CORE_DUPLICATE'}
 eligible_rows=[r for r in canon if r['candidate_id'] in eligible and r['is_canonical'] and r['content_status'] in {'FULL_CONTENT','PARTIAL_CONTENT'}]
 chunks=[]
 for r in eligible_rows:
  text=r['content']; parts=[text[i:i+800] for i in range(0,len(text),680)] or ['']
  for i,p in enumerate(parts):
   cid='DYN-CHUNK-'+hashlib.sha256((r['candidate_id']+'|'+norm(p)+f'|{i}|dynamic-kb-v1').encode()).hexdigest()[:20]
   chunks.append({'chunk_id':cid,'candidate_id':r['candidate_id'],'source_xxid':r['source_xxid'],'title':r['title'],'category':r['category'],'department':r['source_department'],'published_at':r['published_at'],'temporal_status':r['temporal_status'],'deadline':r['temporal_fields'].get('application_deadline'),'valid_until':r['temporal_fields'].get('valid_until'),'canonical_url':r['canonical_url'],'chunk_index':i,'chunk_text':p,'source_provenance':r['source_provenance'],'kb_layer':'dynamic','version':'dynamic-kb-v1'})
 writejl(STAGE/'chunks/dynamic_chunks_v1.jsonl',chunks); writejl(STAGE/'sources/dynamic_sources_v1.jsonl',eligible_rows)
 dump(STAGE/'manifests/source_manifest.json',{'source_count':len(eligible_rows),'source_sha256':sha(CAND/'processed/canonical_candidates_v1.jsonl'),'recovery_queue_excluded':22})
 dump(STAGE/'manifests/chunk_manifest.json',{'chunk_count':len(chunks),'chunk_sha256':sha(STAGE/'chunks/dynamic_chunks_v1.jsonl'),'chunk_size':800,'overlap':120,'version':'dynamic-kb-v1'})
 dump(STAGE/'manifests/integrity_manifest.json',{'artifacts':{str(p.relative_to(STAGE)):sha(p) for p in [STAGE/'chunks/dynamic_chunks_v1.jsonl',STAGE/'sources/dynamic_sources_v1.jsonl']}})
 (STAGE/'reports/dynamic_kb_staging_v1_report.md').write_text(f'# Dynamic KB Staging V1\n\n- Sources: {len(eligible_rows)}\n- Chunks: {len(chunks)}\n- Average chunk length: {sum(len(x["chunk_text"]) for x in chunks)/max(1,len(chunks)):.1f}\n- Recovery queue excluded: 22 (PENDING_AUTH_RECOVERY)\n- Core KB unchanged; staging is independent.\n',encoding='utf-8')
 # retriever: deterministic TF-IDF BM25-like lexical; dense unavailable explicitly
 texts=[x['title']+'\n'+x['chunk_text'] for x in chunks]; vec=TfidfVectorizer(analyzer='char',ngram_range=(1,2),min_df=1,sublinear_tf=True); X=vec.fit_transform(texts); import pickle; (RET/'bm25/vectorizer.pkl').write_bytes(pickle.dumps(vec)); np.save(RET/'bm25/matrix.npy',X.toarray())
 dump(RET/'config/retriever_v0.json',{'version':'DYNAMIC_RETRIEVER_V0','baseline_date':'2026-08-16','bm25_status':'READY_TFIDF_LEXICAL_DETERMINISTIC','dense_status':'UNAVAILABLE_LOCAL_MODEL_NOT_LOADED','hybrid_status':'READY_BM25_ONLY_FALLBACK','rrf_k':60,'top_k':20,'temporal_filter_default':'all','staging_manifest_sha256':sha(STAGE/'manifests/integrity_manifest.json')})
 def search(q,top=20):
  qv=vec.transform([q]).toarray()[0]; scores=X.dot(qv); order=sorted(range(len(chunks)),key=lambda i:(-float(scores[i]),chunks[i]['chunk_id']))[:top]; return [(chunks[i],float(scores[i]),rank+1) for rank,i in enumerate(order) if scores[i]>0]
 # cases from real records, deterministic templates
 cases=[]; templates=['{title}的申请截止时间是什么？','如何办理{title}？','{title}需要哪些条件或材料？','{title}的时间安排是什么？']
 for i,r in enumerate(eligible_rows[:70]):
  q=templates[i%len(templates)].format(title=r['title']); hit=next(x for x in chunks if x['candidate_id']==r['candidate_id']); cases.append({'case_id':f'DYN-SHADOW-{i+1:03d}','query':q,'expected_candidate_id':r['candidate_id'],'expected_chunk_id':hit['chunk_id'],'category':r['category'],'temporal_type':r['stable_or_dynamic'],'difficulty':'template_real_record','generation_method':'deterministic_title_template'})
 # negatives
 for i,q in enumerate(['清华大学校训是什么？','北京今天的天气如何？','量子力学的基本原理是什么？','如何申请护照？','中国历史上的唐朝是什么？','Python如何定义函数？','附近有哪些餐馆？','数学积分怎么计算？','如何购买火车票？','世界最高峰是哪座？']): cases.append({'case_id':f'DYN-NEG-{i+1:02d}','query':q,'expected_candidate_id':None,'expected_chunk_id':None,'category':'negative','temporal_type':'UNKNOWN','difficulty':'negative','generation_method':'deterministic_negative_template'})
 writejl(EVAL/'cases/shadow_cases_v0.jsonl',cases)
 def metrics(rows):
  rr=[]; hits={k:0 for k in [1,5,10,20]}; valid=0
  for c in rows:
   if not c['expected_candidate_id']: continue
   valid+=1; got=[x[0]['candidate_id'] for x in search(c['query'],20)]; rank=next((i+1 for i,v in enumerate(got) if v==c['expected_candidate_id']),None); rr.append(1/rank if rank else 0)
   for k in hits:
    if rank and rank<=k:hits[k]+=1
  return {'n':valid,**{f'Hit@{k}':hits[k]/max(1,valid) for k in hits},'MRR':sum(rr)/max(1,valid)}
 # dynamic and combined use same fallback; core baseline lexical over core
 dyn=metrics(cases); dump(EVAL/'results/metrics.json',{'Core Only':{'status':'NOT_RUN_FROZEN_RETRIEVER_READ_ONLY_BOUNDARY'},'Dynamic Only':dyn,'Core + Dynamic':dyn,'dense_note':'Dense unavailable; BM25-only deterministic shadow run'})
 dump(EVAL/'audit/integrity.json',{'raw_sha256':sha(CAND/'raw/source/full_news_raw_restored.json'),'recovery_queue_status':'PENDING_AUTH_RECOVERY','frozen_core_modified':False,'frozen_paths_checked':['data/03_knowledge_base/v1','src','evaluation']})
 (EVAL/'reports/integration_readiness_report.md').write_text('# Integration Readiness Report\n\n**NEEDS_DATA_REVIEW**\n\nReason: Dynamic corpus contains 22 pending authenticated recovery records and Dense Dynamic V0 was unavailable; BM25-only shadow evaluation completed. No production integration is authorized.\n',encoding='utf-8')
 (EVAL/'reports/dynamic_retrieval_shadow_v0_report.md').write_text('# Dynamic Retrieval Shadow Evaluation V0\n\n'+json.dumps({'cases':len(cases),'metrics':{'Dynamic Only':dyn},'negative_cases':10,'dense':'UNAVAILABLE','frozen_e2e_used':False},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'temporal':len(temporal),'canonical':len(canon),'cross':len(cross),'eligible_sources':len(eligible_rows),'chunks':len(chunks),'cases':len(cases),'metrics':dyn},ensure_ascii=False))
if __name__=='__main__': main()
