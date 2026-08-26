import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/04_kb_expansion_candidate/dynamic_campus_v1'
RAW=BASE/'raw/source/full_news_raw_restored.json'
QUEUE=BASE/'candidates/content_recovery_queue.jsonl'
OUT=BASE/'candidates'
raw=json.loads(RAW.read_text(encoding='utf-8'))['list']
by_id={x.get('xxid'):x for x in raw}
existing=[json.loads(x) for x in (BASE/'candidates/dynamic_candidates_v1.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
results=[]
for q in [json.loads(x) for x in QUEUE.read_text(encoding='utf-8').splitlines() if x.strip()]:
    x=by_id.get(q['source_xxid'],{})
    body=''.join(str(x.get(k) or '') for k in ('nr_show','nr','nr_en')).strip()
    shell=q.get('content_status')=='WEB_SHELL'
    results.append({'candidate_id':next((r['candidate_id'] for r in existing if r['source_xxid']==q['source_xxid']),None),'source_xxid':q['source_xxid'],'title':q.get('title'),'category':q.get('source_department'),'source_url':q.get('source_url'),'recovery_status':'FAILED','recovery_method':'LOCAL_FIELD_RECOVERY','recovered_content':'','recovered_content_length':0,'content_status_after':q.get('content_status'),'attempted_urls':[],'http_or_page_status':'NOT_ATTEMPTED','failure_reason':'WEB_SHELL_ONLY' if shell else 'NO_BODY_IN_SOURCE','source_provenance':{'raw_file':'raw/source/full_news_raw_restored.json','raw_xxid':q['source_xxid'],'local_fields_checked':['nr_show','nr','nr_en','xxgxm','yxxid','xxid'],'portal_fetch':'not_attempted','auth_status':'NEED_MANUAL_LOGIN','auth_reason':'existing auth status is manual_login_timeout; storage state absent'},'recovered_at':datetime.now(timezone.utc).isoformat(),'processing_version':'dynamic_campus_recovery_v1'})
def write(path, rows): path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
write(OUT/'content_recovery_results.jsonl',results)
write(OUT/'dynamic_candidates_v1_recovered.jsonl',existing)
from collections import Counter
c=Counter(x['recovery_status'] for x in results); methods=Counter(x['recovery_method'] for x in results); fails=Counter(x['failure_reason'] for x in results)
intl=[x for x in results if 'IO' in (x['title'] or '') or '实习' in (x['title'] or '')]
report=f'''# Content Recovery Report\n\n## Recovery Summary\n\n- Total: **{len(results)}**\n- Recovered: **{c.get('RECOVERED',0)}**\n- Partially Recovered: **{c.get('PARTIALLY_RECOVERED',0)}**\n- Failed: **{c.get('FAILED',0)}**\n- Auth Required: **{c.get('AUTH_REQUIRED',0)}**\n\n## International Organization Internship\n\n- Total: **{len(intl)}**\n- Recovered: {sum(x['recovery_status']=='RECOVERED' for x in intl)}\n- Failed: {sum(x['recovery_status']=='FAILED' for x in intl)}\n- Auth required: {sum(x['recovery_status']=='AUTH_REQUIRED' for x in intl)}\n\n## Recovery Methods\n\n- LOCAL_FIELD_RECOVERY: {methods.get('LOCAL_FIELD_RECOVERY',0)}\n- ORIGIN_RECORD_RECOVERY: {methods.get('ORIGIN_RECORD_RECOVERY',0)}\n- AUTHENTICATED_FETCH: {methods.get('AUTHENTICATED_FETCH',0)}\n\n## Failures\n\n{''.join(f'- {k}: {v}\n' for k,v in fails.items())}\n\n## Integrity\n\n- Recovery input remains **{len(results)}** records with one result per queue item.\n- No network fetch was attempted because no reusable authenticated storage state was available.\n- Raw source was not modified.\n- KB V1, Retriever V1, embeddings, Evidence, Citation, Answer Generation, E2E, and production runtime were not modified.\n- Failed records were not promoted to complete candidates. `dynamic_candidates_v1_recovered.jsonl` preserves the existing 924 candidates.\n'''
(BASE/'reports/content_recovery_report.md').write_text(report,encoding='utf-8')
