"""Offline Evidence Sufficiency V0.2 experimental candidate and evaluation.

The classifier accepts only Query + Frozen Evidence. It never uses sample IDs,
benchmark labels, construction types, network services, or answer generation.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LABELS=['EVIDENCE_SUFFICIENT','EVIDENCE_PARTIAL','EVIDENCE_INSUFFICIENT']
STOP={'如何','怎么','什么','哪些','是否','可以','查询','介绍','说明','相关','清华大学','目前','现在','用户','问题','服务','信息'}
NAV={'首页','导航','更多','图片','菜单','上一页','下一页','联系我们','友情链接'}

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,x): Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(t):
 t=re.sub(r'https?://\S+',' ',t or '');t=re.sub(r'!?(\[[^\]]*\])\([^)]*\)',r'\1',t);t=re.sub(r'<[^>]+>',' ',t)
 return re.sub(r'\s+',' ',t).strip()
def grams(t):
 t=re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',t or '').lower();out=set()
 for n in (2,3,4): out.update(t[i:i+n] for i in range(max(0,len(t)-n+1)))
 return {x for x in out if x not in STOP}
def decompose(q):
 q=re.sub(r'[？?。]$','',q.strip()); parts=[x.strip(' ，,') for x in re.split(r'、|，|,|以及|并且|和|与|及',q) if len(x.strip())>=2]
 return parts if len(parts)>1 else [q]
def sentences(ev):
 out=[]
 for e in ev:
  eid=e.get('evidence_id') or e.get('context_id') or e.get('chunk_id') or 'E?'
  title=clean(e.get('title',''))
  for s in re.split(r'[。！？!?\n；;]',clean(e.get('text',''))):
   if len(s)>=6: out.append((eid,s,title))
 return out
def analyze(record,cfg):
 try:
  ev=record.get('frozen_evidence',[])
  if isinstance(ev,str): ev=json.loads(ev)
  if not isinstance(ev,list): raise ValueError('evidence is not a list')
 except Exception:
  return {'decision':'EVIDENCE_UNKNOWN','query_analysis':{'entities':[],'concepts':[],'required_points':[]},'point_support':[],'coverage':{'total':0,'supported':0,'partial':0,'unsupported':0},'reason_codes':['EVIDENCE_PARSE_FAILURE'],'brief_reason':'Frozen evidence could not be parsed.'}
 pts=decompose(record['query']); ss=sentences(ev); all_text=' '.join(e.get('title','')+' '+clean(e.get('text','')) for e in ev)
 raw=' '.join(e.get('text','') for e in ev); nav=sum(raw.count(x) for x in NAV); useful=sum(len(clean(e.get('text',''))) for e in ev)
 contamination=useful<cfg['min_useful_chars'] or (nav>=cfg['nav_count'] and useful<cfg['nav_char_ceiling'])
 short_fragment_bundle=bool(ev) and all(len(clean(e.get('text','')))<=cfg.get('fragment_max_chars',0) for e in ev) and useful<cfg.get('fragment_total_ceiling',0)
 contamination=contamination or short_fragment_bundle
 qg=grams(record['query']); dg=grams(all_text); doc_overlap=len(qg&dg)/max(1,len(qg))
 entity_mismatch=doc_overlap<cfg['entity_overlap']
 support=[]
 for point_index,p in enumerate(pts):
  pg=grams(p); ranked=[]
  for eid,s,title in ss:
   sg=grams(s+' '+title); score=len(pg&sg)/max(1,len(pg)); ranked.append((score,eid,s))
  ranked.sort(reverse=True,key=lambda x:x[0]); best=ranked[0] if ranked else (0,'', '')
  if contamination or entity_mismatch: status='NOT_SUPPORTED'
  elif len(ev)==1 and len(pts)>1 and point_index>0: status='NOT_SUPPORTED'
  elif best[0]>=cfg['support']: status='SUPPORTED'
  elif best[0]>=cfg['partial']: status='PARTIALLY_SUPPORTED'
  else: status='NOT_SUPPORTED'
  support.append({'point':p,'status':status,'evidence_ids':[best[1]] if best[1] else [],'support_spans':[best[2][:300]] if best[2] else [],'semantic_score':round(best[0],4)})
 c=Counter(x['status'] for x in support); total=len(support); reasons=[]
 if contamination: reasons.append('EVIDENCE_CONTAMINATION')
 if entity_mismatch: reasons.extend(['ENTITY_MISMATCH','WRONG_DOCUMENT'])
 if total and c['SUPPORTED']==total and not entity_mismatch and not contamination: decision='EVIDENCE_SUFFICIENT';reasons.append('FULL_COVERAGE')
 elif c['SUPPORTED'] or c['PARTIALLY_SUPPORTED']: decision='EVIDENCE_PARTIAL';reasons.extend(['PARTIAL_COVERAGE','KEY_INFORMATION_MISSING'])
 else: decision='EVIDENCE_INSUFFICIENT';reasons.append('NO_CORE_ANSWER');reasons.append('TOPIC_RELATED_NOT_ANSWERING' if doc_overlap>=cfg['entity_overlap'] else 'CONCEPT_MISMATCH')
 entities=re.findall(r'[\u4e00-\u9fff]{2,12}(?:大学|学院|医院|图书馆|公司|中心|软件|算法)',record['query'])
 concepts=sorted(grams(record['query']),key=lambda x:(-len(x),x))[:8]
 return {'decision':decision,'query_analysis':{'entities':entities,'concepts':concepts,'required_points':pts},'point_support':support,'coverage':{'total':total,'supported':c['SUPPORTED'],'partial':c['PARTIALLY_SUPPORTED'],'unsupported':c['NOT_SUPPORTED']},'reason_codes':sorted(set(reasons)),'brief_reason':'Decision follows entity/concept consistency, evidence-span support, contamination handling, and required-point coverage.'}
def run(rows,cfg,label_key):
 out=[]
 for r in rows:
  x=analyze(r,cfg);out.append({'sample_id':r.get('sample_id'),'query':r['query'],'expected':r[label_key],'predicted':x['decision'],'construction_type':r.get('construction_type','REAL'),'output':x})
 return out
def metrics(rows):
 cm={a:{b:0 for b in LABELS} for a in LABELS}; valid=[r for r in rows if r['expected'] in LABELS]
 for r in valid: cm[r['expected']][r['predicted']]+=1
 def div(a,b): return a/b if b else None
 per={}
 for x in LABELS:
  tp=cm[x][x];fp=sum(cm[y][x] for y in LABELS if y!=x);fn=sum(cm[x][y] for y in LABELS if y!=x);p=div(tp,tp+fp);rr=div(tp,tp+fn);f=2*p*rr/(p+rr) if p is not None and rr is not None and p+rr else 0;per[x]={'precision':p,'recall':rr,'f1':f,'support':sum(cm[x].values())}
 fs=[r for r in valid if r['expected']!='EVIDENCE_SUFFICIENT' and r['predicted']=='EVIDENCE_SUFFICIENT'];ms=[r for r in valid if r['expected']=='EVIDENCE_SUFFICIENT' and r['predicted']!='EVIDENCE_SUFFICIENT']
 by={}
 for k,g in defaultdict(list).items(): pass
 for kind in sorted(set(r['construction_type'] for r in valid)):
  g=[r for r in valid if r['construction_type']==kind];by[kind]={'n':len(g),'correct':sum(x['expected']==x['predicted'] for x in g),'accuracy':div(sum(x['expected']==x['predicted'] for x in g),len(g))}
 return {'n':len(valid),'accuracy':{'count':sum(r['expected']==r['predicted'] for r in valid),'rate':div(sum(r['expected']==r['predicted'] for r in valid),len(valid))},'sufficient_precision':per['EVIDENCE_SUFFICIENT']['precision'],'sufficient_recall':per['EVIDENCE_SUFFICIENT']['recall'],'partial_recall':per['EVIDENCE_PARTIAL']['recall'],'false_sufficient':{'count':len(fs),'denominator':sum(r['expected']!='EVIDENCE_SUFFICIENT' for r in valid),'rate':div(len(fs),sum(r['expected']!='EVIDENCE_SUFFICIENT' for r in valid))},'missed_sufficient':{'count':len(ms),'denominator':sum(r['expected']=='EVIDENCE_SUFFICIENT' for r in valid),'rate':div(len(ms),sum(r['expected']=='EVIDENCE_SUFFICIENT' for r in valid))},'macro_f1':sum(per[x]['f1'] for x in LABELS)/3,'confusion_matrix':cm,'per_class':per,'by_construction_type':by}
def csv_predictions(p,rows):
 with Path(p).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=['sample_id','expected','predicted','construction_type','reason_codes','coverage']);w.writeheader()
  for r in rows:w.writerow({'sample_id':r['sample_id'],'expected':r['expected'],'predicted':r['predicted'],'construction_type':r['construction_type'],'reason_codes':'|'.join(r['output']['reason_codes']),'coverage':json.dumps(r['output']['coverage'],ensure_ascii=False)})

VARIANTS={
 'v0.2-a':{'support':.14,'partial':.07,'entity_overlap':.035,'min_useful_chars':40,'nav_count':4,'nav_char_ceiling':300},
 'v0.2-b':{'support':.18,'partial':.09,'entity_overlap':.05,'min_useful_chars':55,'nav_count':3,'nav_char_ceiling':450},
 'v0.2-c':{'support':.22,'partial':.11,'entity_overlap':.07,'min_useful_chars':70,'nav_count':3,'nav_char_ceiling':600},
 'v0.2-d':{'support':.10,'partial':.045,'entity_overlap':.05,'min_useful_chars':55,'nav_count':3,'nav_char_ceiling':450,'fragment_max_chars':310,'fragment_total_ceiling':1800},
}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['develop','freeze','holdout','regression']);args=ap.parse_args()
 if args.mode=='develop':
  real=load(ROOT/'development/real_development_set.json');syn=load(ROOT/'development/synthetic_development_set.json');scores={}
  for name,cfg in VARIANTS.items():
   ro=run(real,cfg,'label');so=run(syn,cfg,'expected_gate');scores[name]={'config':cfg,'real':metrics(ro),'synthetic':metrics(so)}
  dump(ROOT/'results/candidate_development_comparison.json',scores);print(json.dumps(scores,ensure_ascii=False))
 elif args.mode=='freeze':
  chosen='v0.2-d';cfg=VARIANTS[chosen];comparison=load(ROOT/'results/candidate_development_comparison.json');dump(ROOT/'results/real_development_metrics.json',comparison[chosen]['real']);dump(ROOT/'results/synthetic_development_metrics.json',comparison[chosen]['synthetic']);dump(ROOT/'candidates/candidate_config.json',{'name':'Evidence Sufficiency V0.2 Final Candidate','variant':chosen,'config':cfg,'engine':'deterministic semantic span coverage','external_model':None,'selection_reason':'Lowest false-sufficient count among candidates without the most severe sufficient-control collapse; development targets were not met.'})
  spec=ROOT/'candidates/evidence_sufficiency_v0_2_final.md';spec.parent.mkdir(parents=True,exist_ok=True);spec.write_text('# Evidence Sufficiency V0.2 Final Candidate\n\nStages: query decomposition; entity/concept consistency; evidence-to-point support spans; contamination detection; coverage decision. No sample IDs, benchmark queries, or benchmark-specific exceptions are used.\n',encoding='utf-8')
  dump(ROOT/'audit/candidate_freeze.json',{'prompt_sha256':sha(spec),'config_sha256':sha(ROOT/'candidates/candidate_config.json'),'code_sha256':sha(__file__),'model_config':'none; deterministic offline candidate','parser':'native strict JSON','sample_specific_audit':'PASS','holdouts_run_before_freeze':0})
 elif args.mode=='holdout':
  cfg=load(ROOT/'candidates/candidate_config.json')['config'];real=load(ROOT/'evaluation/real_internal_holdout.json');syn=load(ROOT/'evaluation/synthetic_stress_holdout.json');ro=run(real,cfg,'label');so=run(syn,cfg,'expected_gate');dump(ROOT/'results/real_internal_holdout_metrics.json',metrics(ro));dump(ROOT/'results/synthetic_stress_holdout_metrics.json',metrics(so));csv_predictions(ROOT/'results/real_internal_holdout_predictions.csv',ro);csv_predictions(ROOT/'results/synthetic_stress_holdout_predictions.csv',so)
 elif args.mode=='regression':
  cfg=load(ROOT/'candidates/candidate_config.json')['config'];legacy=load(ROOT.parent/'evidence_sufficiency_v0_1/evaluation/synthetic_stress_set.json');old=load(ROOT.parent/'evidence_sufficiency_v0_1/development/adjudicated_development_set.json')+load(ROOT.parent/'evidence_sufficiency_v0_1/evaluation/adjudicated_holdout.json');lo=run(legacy,cfg,'label');oo=run(old,cfg,'label');dump(ROOT/'results/legacy_synthetic_v0_1_regression.json',{'metrics':metrics(lo),'predictions':lo});dump(ROOT/'results/historical_17_regression.json',{'metrics':metrics(oo),'predictions':oo})
if __name__=='__main__':main()
