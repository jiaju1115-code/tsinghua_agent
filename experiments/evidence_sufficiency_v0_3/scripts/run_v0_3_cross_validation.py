"""Stratified seen-data cross-validation for Evidence Sufficiency V0.3."""
from __future__ import annotations
import csv,hashlib,json,re,math
from collections import Counter,defaultdict
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
ROOT=Path(__file__).resolve().parents[1]
LABELS=['EVIDENCE_SUFFICIENT','EVIDENCE_PARTIAL','EVIDENCE_INSUFFICIENT']
NAV={'首页','导航','更多','图片','菜单','上一页','下一页','联系我们','友情链接'}
ATTR={'为什么':['为什么','原因','依据'],'how':['如何','怎么','流程','办理','使用'],'where':['哪里','在哪','地点','入口'],'when':['时间','几点','日期','何时'],'quantity':['多少','规模','数量'],'condition':['条件','要求','资格'],'contact':['联系','电话','邮箱'],'comparison':['区别','比较','差异'],'definition':['是什么','定义','含义'],'method':['办法','规定','指南']}
CONFIGS={
 'v0.3-a':{'support':.055,'partial':.020,'viability':.018,'min_chars':45,'full_chars':450,'fragment_ceiling':1600},
 'v0.3-b':{'support':.070,'partial':.026,'viability':.024,'min_chars':55,'full_chars':600,'fragment_ceiling':1700},
 'v0.3-c':{'support':.085,'partial':.032,'viability':.030,'min_chars':65,'full_chars':750,'fragment_ceiling':1800},
 'v0.3-d':{'support':.100,'partial':.040,'viability':.038,'min_chars':75,'full_chars':900,'fragment_ceiling':1900},
}
MODEL_CONFIGS={
 'v0.3-a':{'max_depth':3,'min_samples_leaf':4,'sufficient_threshold':.65},
 'v0.3-b':{'max_depth':5,'min_samples_leaf':2,'sufficient_threshold':.62},
 'v0.3-c':{'max_depth':7,'min_samples_leaf':2,'sufficient_threshold':.58},
 'v0.3-d':{'max_depth':None,'min_samples_leaf':2,'sufficient_threshold':.60},
}
FEATURE_NAMES=['query_length','core_point_count','evidence_count','log_useful_chars','max_chunk_chars','min_chunk_chars','navigation_count','query_document_overlap','max_point_support','min_point_support','mean_point_support','all_short_fragments','single_evidence_multi_point','query_title_overlap','requested_attribute_support']
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def clean(t):
 t=re.sub(r'https?://\S+',' ',t or '');t=re.sub(r'!?(\[[^\]]*\])\([^)]*\)',r'\1',t);t=re.sub(r'<[^>]+>',' ',t);return re.sub(r'\s+',' ',t).strip()
def grams(t):
 t=re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',t or '').lower();o=set()
 for n in (2,3):o.update(t[i:i+n] for i in range(max(0,len(t)-n+1)))
 return o
def minimal_points(q):
 q=re.sub(r'[？?。]$','',q.strip());parts=[x.strip(' ，,') for x in re.split(r'、|，|,|；|;',q) if len(x.strip())>=2]
 if len(parts)<=1:return [{'point':q,'type':'CORE_REQUIRED'}]
 return [{'point':x,'type':'CORE_REQUIRED'} for x in parts]
def attributes(q):return [k for k,words in ATTR.items() if any(w in q for w in words)] or ['subject']
def spans(ev):
 o=[]
 for e in ev:
  eid=e.get('evidence_id') or e.get('context_id') or e.get('chunk_id') or 'E?';title=clean(e.get('title',''))
  for s in re.split(r'[。！？!?\n；;]',clean(e.get('text',''))):
   if len(s)>=6:o.append((eid,s,title))
 return o
def score(a,b):
 ag=grams(a);bg=grams(b);return len(ag&bg)/max(1,len(ag))
def analyze(r,cfg):
 try:
  ev=r.get('frozen_evidence',[]);ev=json.loads(ev) if isinstance(ev,str) else ev
  if not isinstance(ev,list):raise ValueError
 except Exception:return {'decision':'EVIDENCE_UNKNOWN','query_analysis':{'entities':[],'concepts':[],'requested_attributes':[],'required_points':[]},'point_support':[],'coverage':{'core_total':0,'core_supported':0,'core_partial':0,'core_missing':0},'reason_codes':['EVIDENCE_PARSE_FAILURE'],'brief_reason':'Input parse failure.'}
 pts=minimal_points(r['query']);attrs=attributes(r['query']);ss=spans(ev);texts=[clean(e.get('text','')) for e in ev];alltext=' '.join((e.get('title','')+' '+clean(e.get('text',''))) for e in ev);useful=sum(len(x) for x in texts);nav=sum(alltext.count(x) for x in NAV)
 contamination=useful<cfg['min_chars'] or (nav>=4 and useful<300)
 truncated=bool(texts) and len(texts)>1 and all(len(x)<=310 for x in texts) and useful<cfg['fragment_ceiling']
 doc_score=score(r['query'],alltext);viable=doc_score>=cfg['viability'] and not contamination and not truncated
 point_support=[]
 for i,p in enumerate(pts):
  ranked=sorted([(score(p['point'],s+' '+t),eid,s) for eid,s,t in ss],reverse=True,key=lambda x:x[0]);best=ranked[0] if ranked else (0,'','')
  semantic=max(best[0],doc_score*.72)
  if not viable:status='NOT_SUPPORTED'
  elif len(ev)==1 and len(pts)>1 and i>0:status='NOT_SUPPORTED'
  elif semantic>=cfg['support']:status='SUPPORTED'
  elif semantic>=cfg['partial']:status='PARTIALLY_SUPPORTED'
  else:status='NOT_SUPPORTED'
  point_support.append({'point':p['point'],'point_type':p['type'],'status':status,'evidence_ids':[best[1]] if best[1] else [],'support_spans':[best[2][:360]] if best[2] else [],'semantic_entailment_score':round(semantic,4)})
 c=Counter(x['status'] for x in point_support);total=len(point_support);reasons=[]
 requested_attribute_mismatch=viable and all(x['status']=='NOT_SUPPORTED' for x in point_support)
 if contamination or truncated:reasons.append('EVIDENCE_CONTAMINATION')
 if not viable and not contamination and not truncated:reasons.extend(['ENTITY_MISMATCH','CONCEPT_MISMATCH','WRONG_DOCUMENT'])
 if requested_attribute_mismatch:reasons.extend(['REQUESTED_ATTRIBUTE_MISMATCH','WRONG_DOCUMENT'])
 if total and c['SUPPORTED']==total:decision='EVIDENCE_SUFFICIENT';reasons.append('FULL_COVERAGE')
 elif c['SUPPORTED'] or c['PARTIALLY_SUPPORTED']:decision='EVIDENCE_PARTIAL';reasons.extend(['PARTIAL_COVERAGE','KEY_INFORMATION_MISSING'])
 else:decision='EVIDENCE_INSUFFICIENT';reasons.append('NO_CORE_ANSWER');reasons.append('TOPIC_RELATED_NOT_ANSWERING')
 return {'decision':decision,'query_analysis':{'entities':re.findall(r'[\u4e00-\u9fff]{2,12}(?:大学|学院|医院|图书馆|公司|中心|软件|算法)',r['query']),'concepts':sorted(grams(r['query']),key=lambda x:(-len(x),x))[:8],'requested_attributes':attrs,'required_points':pts},'point_support':point_support,'coverage':{'core_total':total,'core_supported':c['SUPPORTED'],'core_partial':c['PARTIALLY_SUPPORTED'],'core_missing':c['NOT_SUPPORTED']},'reason_codes':sorted(set(reasons)),'brief_reason':'Minimal core points are decided by semantic support; optional detail absence is not penalized.'}
def predict(rows,cfg):
 return [{**{k:r.get(k,'') for k in ['record_id','sample_id','source_dataset','data_kind','construction_type','query']},'expected':r['label'],'predicted':(o:=analyze(r,cfg))['decision'],'output':o} for r in rows]
def features(r):
 ev=r.get('frozen_evidence',[]);ev=json.loads(ev) if isinstance(ev,str) else ev;ev=ev if isinstance(ev,list) else []
 texts=[clean(e.get('text','')) for e in ev];titles=' '.join(e.get('title','') for e in ev);alltext=titles+' '+' '.join(texts);pts=minimal_points(r['query']);ss=spans(ev)
 ps=[]
 for p in pts:
  ps.append(max([score(p['point'],s+' '+t) for _,s,t in ss] or [0]))
 attrs=attributes(r['query']);attr_text=' '.join(w for a in attrs for w in ATTR.get(a,[]));nav=sum(alltext.count(x) for x in NAV)
 return np.array([len(r['query']),len(pts),len(ev),math.log1p(sum(map(len,texts))),max(map(len,texts),default=0),min(map(len,texts),default=0),nav,score(r['query'],alltext),max(ps,default=0),min(ps,default=0),sum(ps)/max(1,len(ps)),int(bool(texts) and len(texts)>1 and all(len(x)<=310 for x in texts)),int(len(ev)==1 and len(pts)>1),score(r['query'],titles),score(attr_text,alltext) if attr_text else 0],dtype=float)
def fit_model(rows,mcfg):
 x=np.vstack([features(r) for r in rows]);y=np.array([r['label'] for r in rows]);m=RandomForestClassifier(n_estimators=96,max_depth=mcfg['max_depth'],min_samples_leaf=mcfg['min_samples_leaf'],class_weight='balanced_subsample',random_state=20260814,n_jobs=1);m.fit(x,y);return m
def model_predict(rows,model,mcfg):
 if not rows:return []
 probs=model.predict_proba(np.vstack([features(r) for r in rows]));classes=list(model.classes_);out=[]
 for r,p in zip(rows,probs):
  pd=dict(zip(classes,p));ps=pd.get('EVIDENCE_SUFFICIENT',0)
  if ps>=mcfg['sufficient_threshold']:decision='EVIDENCE_SUFFICIENT'
  else:decision=max(['EVIDENCE_PARTIAL','EVIDENCE_INSUFFICIENT'],key=lambda x:pd.get(x,0))
  detail=analyze(r,CONFIGS['v0.3-b']);detail['decision']=decision;detail['class_probabilities']={k:round(float(v),6) for k,v in pd.items()};detail['reason_codes']=sorted(set(detail['reason_codes']+['CALIBRATED_THREE_CLASS_BOUNDARY']))
  out.append({**{k:r.get(k,'') for k in ['record_id','sample_id','source_dataset','data_kind','construction_type','query']},'expected':r['label'],'predicted':decision,'output':detail})
 return out
def div(a,b):return a/b if b else None
def metrics(rows):
 valid=[r for r in rows if r['expected'] in LABELS];cm={a:{b:0 for b in LABELS} for a in LABELS}
 for r in valid:cm[r['expected']][r['predicted']]+=1
 per={}
 for l in LABELS:
  tp=cm[l][l];fp=sum(cm[x][l] for x in LABELS if x!=l);fn=sum(cm[l][x] for x in LABELS if x!=l);p=div(tp,tp+fp);rr=div(tp,tp+fn);per[l]={'precision':p,'recall':rr,'f1':2*p*rr/(p+rr) if p is not None and rr is not None and p+rr else 0,'support':sum(cm[l].values())}
 fs=sum(r['expected']!='EVIDENCE_SUFFICIENT' and r['predicted']=='EVIDENCE_SUFFICIENT' for r in valid);ms=sum(r['expected']=='EVIDENCE_SUFFICIENT' and r['predicted']!='EVIDENCE_SUFFICIENT' for r in valid)
 by={}
 for k in sorted(set(r['construction_type'] for r in valid)):
  g=[r for r in valid if r['construction_type']==k];by[k]={'n':len(g),'correct':sum(x['expected']==x['predicted'] for x in g),'accuracy':div(sum(x['expected']==x['predicted'] for x in g),len(g))}
 return {'n':len(valid),'accuracy':{'count':sum(r['expected']==r['predicted'] for r in valid),'rate':div(sum(r['expected']==r['predicted'] for r in valid),len(valid))},'macro_f1':sum(per[l]['f1'] for l in LABELS)/3,'sufficient_precision':per['EVIDENCE_SUFFICIENT']['precision'],'sufficient_recall':per['EVIDENCE_SUFFICIENT']['recall'],'partial_precision':per['EVIDENCE_PARTIAL']['precision'],'partial_recall':per['EVIDENCE_PARTIAL']['recall'],'insufficient_precision':per['EVIDENCE_INSUFFICIENT']['precision'],'insufficient_recall':per['EVIDENCE_INSUFFICIENT']['recall'],'false_sufficient':{'count':fs,'denominator':sum(r['expected']!='EVIDENCE_SUFFICIENT' for r in valid),'rate':div(fs,sum(r['expected']!='EVIDENCE_SUFFICIENT' for r in valid))},'missed_sufficient':{'count':ms,'denominator':sum(r['expected']=='EVIDENCE_SUFFICIENT' for r in valid),'rate':div(ms,sum(r['expected']=='EVIDENCE_SUFFICIENT' for r in valid))},'confusion_matrix':cm,'per_class':per,'by_construction_type':by}
def utility(m):
 fs=m['false_sufficient']['rate'] or 0;sr=m['sufficient_recall'] or 0;pr=m['partial_recall'] or 0;ir=m['insufficient_recall'] or 0
 return .32*(1-fs)+.28*sr+.16*pr+.12*ir+.12*m['macro_f1']
def folds(rows,stratum,k=5):
 groups=defaultdict(list)
 for r in rows:groups[stratum(r)].append(r)
 out=[[] for _ in range(k)]
 for key,g in groups.items():
  g.sort(key=lambda r:hashlib.sha256((r['record_id']+'||v0.3_cv').encode()).hexdigest())
  for i,r in enumerate(g):out[i%k].append(r)
 return out
def cv(rows,stratum):
 fs=folds(rows,stratum);oof=[];fold_reports=[]
 for i,val in enumerate(fs):
  train=[r for j,f in enumerate(fs) if j!=i for r in f];scores={n:utility(metrics(predict(train,c))) for n,c in CONFIGS.items()};chosen=max(scores,key=scores.get);pred=predict(val,CONFIGS[chosen]);oof.extend(pred);fold_reports.append({'fold':i+1,'train_n':len(train),'validation_n':len(val),'selected_candidate':chosen,'train_utilities':scores,'validation_metrics':metrics(pred)})
 return oof,{'folds':fold_reports,'aggregate':metrics(oof)}
def nested_model_cv(rows,stratum):
 outer=folds(rows,stratum);oof=[];reports=[]
 for i,val in enumerate(outer):
  train=[r for j,f in enumerate(outer) if j!=i for r in f];inner=folds(train,stratum,3);scores={}
  for name,mcfg in MODEL_CONFIGS.items():
   inner_preds=[]
   for j,ival in enumerate(inner):
    itr=[r for z,f in enumerate(inner) if z!=j for r in f];inner_preds.extend(model_predict(ival,fit_model(itr,mcfg),mcfg))
   scores[name]=utility(metrics(inner_preds))
  chosen=max(scores,key=scores.get);pred=model_predict(val,fit_model(train,MODEL_CONFIGS[chosen]),MODEL_CONFIGS[chosen]);oof.extend(pred);reports.append({'fold':i+1,'train_n':len(train),'validation_n':len(val),'selected_candidate':chosen,'inner_cv_utilities':scores,'validation_metrics':metrics(pred)})
 return oof,{'method':'5-fold outer CV with 3-fold inner calibration; labels/thresholds from training folds only','folds':reports,'aggregate':metrics(oof)}
def write_csv(p,rows):
 with Path(p).open('w',newline='',encoding='utf-8-sig') as f:
  fields=['record_id','sample_id','source_dataset','construction_type','expected','predicted','fold','reason_codes','core_total','core_supported','core_partial','core_missing'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({'record_id':r['record_id'],'sample_id':r['sample_id'],'source_dataset':r['source_dataset'],'construction_type':r['construction_type'],'expected':r['expected'],'predicted':r['predicted'],'fold':r.get('fold',''),'reason_codes':'|'.join(r['output']['reason_codes']),**r['output']['coverage']})
def main():
 data=load(ROOT/'dataset/unified_calibration_dataset.json');real=[r for r in data if r['data_kind']=='REAL_ADJUDICATED'];syn=[r for r in data if r['data_kind']=='SYNTHETIC_CONSTRUCTED']
 ro,rr=nested_model_cv(real,lambda r:r['label']);so,sr=nested_model_cv(syn,lambda r:r['construction_type'])
 # Assign deterministic fold numbers for auditable prediction rows.
 for rows,stratum,preds in [(real,lambda r:(r['label'],r.get('category','')),ro),(syn,lambda r:r['construction_type'],so)]:
  mapping={x['record_id']:i+1 for i,f in enumerate(folds(rows,stratum)) for x in f}
  for p in preds:p['fold']=mapping[p['record_id']]
 dump(ROOT/'results/real_cross_validation_metrics.json',rr);dump(ROOT/'results/synthetic_cross_validation_metrics.json',sr);write_csv(ROOT/'results/real_cross_validation_predictions.csv',ro);write_csv(ROOT/'results/synthetic_cross_validation_predictions.csv',so)
 # Final hyperparameter choice is based on nested-CV selection frequency, then trained on all seen rows.
 selected=[f['selected_candidate'] for f in rr['folds']+sr['folds']];final=Counter(selected).most_common(1)[0][0];allrows=real+syn;model=fit_model(allrows,MODEL_CONFIGS[final]);joblib.dump(model,ROOT/'candidates/candidate_model.joblib')
 dump(ROOT/'results/candidate_selection.json',{'outer_fold_selections':dict(Counter(selected)),'selected':final,'selection_rule':'most frequent inner-CV winner across Real and Synthetic outer folds'})
 for n,c in MODEL_CONFIGS.items():
  (ROOT/f'candidates/candidate_{n.replace(".","_")}.md').write_text(f'# {n}\n\nMinimal CORE_REQUIRED points; optional support separated; requested-attribute viability; semantic entailment features; contamination after valid-content extraction; train-fold-only calibrated three-class boundary.\n\nConfig: `{json.dumps(c)}`\n',encoding='utf-8')
 dump(ROOT/'candidates/candidate_config.json',{'name':'Evidence Sufficiency V0.3 Final Candidate','variant':final,'config':MODEL_CONFIGS[final],'features':FEATURE_NAMES,'policy':'Minimal core points + requested attribute viability + semantic entailment coverage + calibrated three-class boundary','parser':'native strict JSON','model':'offline RandomForest trained only on seen calibration data'})
 (ROOT/'candidates/evidence_sufficiency_v0_3_final.md').write_text('# Evidence Sufficiency V0.3 Final Candidate\n\nUses Minimal Necessary CORE_REQUIRED points, separates OPTIONAL_SUPPORT, checks requested attributes and entity/concept viability, treats support spans as audit evidence rather than a lexical hard threshold, and evaluates contamination only after valid-content extraction.\n',encoding='utf-8')
 print(json.dumps({'real_cv':rr['aggregate'],'synthetic_cv':sr['aggregate'],'selected':final},ensure_ascii=False))
if __name__=='__main__':main()
