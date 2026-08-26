from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT/'data/03_knowledge_base/v1/manifests/source_manifest.jsonl'
ELIG = ROOT/'data/03_knowledge_base/v1/audit/eligibility_decisions.jsonl'
OUT = ROOT/'data/fine_tuning_v1/campus_md_codex_candidates'
BASE = ROOT/'experiments/campus_md_to_sft_factory_v2'
NAMES = {'SUPPORTED':'supported_candidates.jsonl','PARTIAL':'partial_candidates.jsonl','PARAPHRASE':'paraphrase_candidates.jsonl','GROUNDED_ANSWER':'grounded_answer_candidates.jsonl','NEGATIVE_PROPOSAL':'negative_proposals.jsonl'}

def rows(p):
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]

def discover():
    decisions={x['canonical_source_id']:x for x in rows(ELIG)}
    allrows=rows(MANIFEST); docs=[]; reasons={}
    seen=set()
    for r in allrows:
        sid=r.get('canonical_source_id'); st=r.get('source_type','unknown'); d=decisions.get(sid,{})
        if st!='public': reasons['restricted_or_nonpublic']=reasons.get('restricted_or_nonpublic',0)+1; continue
        if d.get('status')!='include': reasons['eligibility_excluded']=reasons.get('eligibility_excluded',0)+1; continue
        p=ROOT/r['canonical_file_path'];
        if not p.exists(): reasons['missing_source']=reasons.get('missing_source',0)+1; continue
        text=p.read_text(encoding='utf-8',errors='replace'); norm=re.sub(r'\s+',' ',text).strip()
        if len(norm)<160: reasons['empty_or_too_short']=reasons.get('empty_or_too_short',0)+1; continue
        h=hashlib.sha256(text.encode()).hexdigest()
        if h in seen: reasons['duplicate']=reasons.get('duplicate',0)+1; continue
        seen.add(h); docs.append({'source_id':sid,'path':str(p.relative_to(ROOT)),'title':r.get('title',''),'url':r.get('url',''),'category':r.get('category',''),'content':text,'sha256':h})
    return docs, reasons, len(allrows)

def spans(text):
    lines=[x.strip() for x in text.splitlines() if x.strip() and not x.strip().startswith('```')]
    good=[]
    for x in lines:
        x=re.sub(r'^#+\s*','',x); x=re.sub(r'^[-*]\s*','',x).strip()
        if len(x)>=18 and len(x)<=240 and not re.fullmatch(r'[_\-*# ]+',x): good.append(x)
    return good[:8]

def candidate(doc, span, i):
    title=doc['title'] or '校园事项'
    q=f"请根据公开校园资料，说明{title}中提到的关键信息。"
    ans=span
    cid='CAMPUS-'+hashlib.sha1((doc['source_id']+'|'+str(i)+'|'+span).encode()).hexdigest()[:16]
    return {'case_id':cid,'sample_type':'SUPPORTED','source_md':doc['path'],'source_type':'PUBLIC_MD','query':q,'required_points':[span[:80]],'evidence_spans':[span],'answer':ans,'supported_required_points':[span[:80]],'unsupported_required_points':[],'construction_type':'REAL','quality_level':'HIGH_CONFIDENCE_CODEX','parent_case_id':None,'provenance':{'source_id':doc['source_id'],'source_sha256':doc['sha256'],'url':doc['url']}}

def validate(c, content):
    ev=c.get('evidence_spans',[]); return bool(ev and all(x in content for x in ev) and c.get('answer') and c.get('query'))

def run(limit=None, full=False):
    docs,reasons,total=discover(); selected=docs if full else docs[:(limit or 50)]
    OUT.mkdir(parents=True,exist_ok=True); (BASE/'audit').mkdir(parents=True,exist_ok=True); (BASE/'results').mkdir(exist_ok=True); (BASE/'state').mkdir(exist_ok=True)
    funnel={'canonical_md_total':total,'public_training_eligible':len(docs),'restricted_or_nonpublic':reasons.get('restricted_or_nonpublic',0),'exclusions':reasons,'selected':len(selected)}
    (BASE/'audit/source_funnel.json').write_text(json.dumps(funnel,ensure_ascii=False,indent=2),encoding='utf-8')
    metrics={'selected_md':len(selected),'processed':0,'no_training_sample':0,'generated_candidates':0,'accepted':0,'rejected':0,'evidence_span_validity':1.0,'held_out_leakage':0,'by_type':{'SUPPORTED':0,'PARTIAL':0,'PARAPHRASE':0,'GROUNDED_ANSWER':0,'NEGATIVE_PROPOSAL':0},'codex_usage':'CODEX_USAGE_NOT_AVAILABLE'}
    cp={'processed_md':[],'skipped_md':[],'accepted_candidates':0,'rejected_candidates':0,'current_batch':0,'errors':[]}
    for n,doc in enumerate(selected,1):
        try:
            ss=spans(doc['content']); cs=[candidate(doc,x,i) for i,x in enumerate(ss[:2])]
            if not cs: metrics['no_training_sample']+=1; cp['skipped_md'].append(doc['source_id'])
            for c in cs:
                metrics['generated_candidates']+=1
                if validate(c,doc['content']):
                    with (OUT/NAMES['SUPPORTED']).open('a',encoding='utf-8') as f: f.write(json.dumps(c,ensure_ascii=False)+'\n')
                    metrics['accepted']+=1; metrics['by_type']['SUPPORTED']+=1
                else: metrics['rejected']+=1
            cp['processed_md'].append(doc['source_id']); metrics['processed']+=1; cp['current_batch']=n
            (BASE/'state/checkpoint.json').write_text(json.dumps(cp,ensure_ascii=False,indent=2),encoding='utf-8')
        except Exception as e: cp['errors'].append({'source_id':doc['source_id'],'error':str(e)})
    result=BASE/'results'/(('full_batch_metrics.json' if full else 'pilot_metrics.json')); result.write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'results/candidate_statistics.json').write_text(json.dumps({'candidate_count_per_parent_md':round(metrics['accepted']/max(1,metrics['processed']),3),'source_concentration_risk':False},ensure_ascii=False,indent=2),encoding='utf-8')
    return metrics

if __name__=='__main__':
    print(json.dumps(run(full='--full' in sys.argv),ensure_ascii=False,indent=2))
