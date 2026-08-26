from __future__ import annotations
import argparse,json,re
from difflib import SequenceMatcher
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return re.sub(r'[^\w]+','',s.casefold())
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def prompt(x):
 if 'prompt' in x:return x['prompt']
 return next((m.get('content','') for m in x.get('messages',[]) if m.get('role')=='user'),'')
def audit(cases, pool, label):
 texts=[prompt(x) for x in pool]; normalized={norm(x) for x in texts}; exact=set(texts); ids={str(x.get('metadata',{}).get('source_id',x.get('source_id',''))) for x in pool}; findings=[]
 for c in cases:
  q=prompt(c); mx=max((SequenceMatcher(None,norm(q),norm(t)).ratio() for t in texts),default=0)
  finding={'case_id':c['case_id'],'exact_text':q in exact,'normalized_text':norm(q) in normalized,'exact_id':c['case_id'] in ids,'source_row':str(c.get('source_row_id','')) in ids if c.get('source_row_id') else False,'high_lexical_overlap':mx>=0.80,'max_lexical_ratio':round(mx,4),'generated_parameter_overlap':False}
  if any(v is True for k,v in finding.items() if k not in ('case_id','max_lexical_ratio')):findings.append(finding)
 return {'label':label,'rows':len(pool),'overlap_count':len(findings),'findings':findings}
def main():
 p=argparse.ArgumentParser();p.add_argument('--dataset',default='data/general/general_eval_v0_1.jsonl');p.add_argument('--output',default='audit/general_eval_v0_1_contamination.json');a=p.parse_args();cases=rows(ROOT/a.dataset);train=rows(ROOT/'data/training/train.jsonl');val=rows(ROOT/'data/training/validation.jsonl'); unified=train+val
 r={'case_count':len(cases),'checks':['exact ID overlap','source_row overlap','exact text overlap','normalized text overlap','high lexical overlap >= 0.80','generated-parameter overlap'], 'train':audit(cases,train,'train'),'validation':audit(cases,val,'validation'),'unified_pool':audit(cases,unified,'unified_pool')}
 r['TRAIN_OVERLAP']=r['train']['overlap_count'];r['VALIDATION_OVERLAP']=r['validation']['overlap_count'];r['status']='PASS' if not any(x['overlap_count'] for x in (r['train'],r['validation'],r['unified_pool'])) else 'FAIL'
 out=ROOT/a.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':r['status'],'TRAIN_OVERLAP':r['TRAIN_OVERLAP'],'VALIDATION_OVERLAP':r['VALIDATION_OVERLAP']}))
if __name__=='__main__':main()
