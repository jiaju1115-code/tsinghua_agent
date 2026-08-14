from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT=Path(r'D:\python_projects\tsinghua_ai')
BASE=ROOT/'data_second'/'restricted_expansion_v1'
META=BASE/'crawl'/'portal_core_fetch_results.jsonl'
STAGING=ROOT/'data_second'/'staging_public_baseline_v1'/'public_staging_manifest.jsonl'
OUT=BASE/'quality_gate'/'restricted_quality_gate_results.jsonl'

def norm_url(url):
 p=urlsplit(url or ''); q=urlencode(sorted((k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in {'ticket','token','session'})); path=re.sub('/+','/',p.path or '/');
 return urlunsplit((p.scheme.lower(),p.netloc.lower(),path.rstrip('/') or '/',q,''))
def tk(x): return re.sub(r'[\W_]+','',(x or '').lower())
def body_from_markdown(p):
 text=p.read_text(encoding='utf-8'); return text.split('\n\n',2)[-1].strip() if '\n\n' in text else text

pub=[json.loads(x) for x in STAGING.read_text(encoding='utf-8').splitlines() if x.strip()]
pub_urls={norm_url(x['url']) for x in pub}; pub_hash={x['content_hash'] for x in pub}; pub_titles=[(tk(x['title']),x['id']) for x in pub]
rows=[json.loads(x) for x in META.read_text(encoding='utf-8').splitlines() if x.strip()]
out=[]
for r in rows:
 q={k:r.get(k) for k in ['restricted_id','title','seed_title','url','category','source_file','content_hash','private_sensitive_status','http_status','body_length','selector_used','crawl_timestamp']}
 q.update({'quality_gate_pass':False,'quality_class':'','diagnostic_reason':'','duplicate_status':'not_checked','duplicate_of':''})
 if r.get('fetch_status')=='pre_safety_excluded': q.update(quality_class='not_eligible',diagnostic_reason='private_sensitive_pre_excluded')
 elif r.get('fetch_status')=='failed': q.update(quality_class='extraction_failed',diagnostic_reason='fetch_failed')
 elif r.get('private_sensitive_status')!='safe_general_content': q.update(quality_class='not_eligible',diagnostic_reason='private_sensitive_gate_not_safe')
 else:
  path=BASE/r['source_file']; body=body_from_markdown(path) if path.exists() else ''
  text=re.sub(r'\s+',' ',body).strip(); links=r.get('outbound_links') or []; title=r.get('title','')
  # Quality: short landing/navigation pages are not detail content.
  if len(text)<180: qc,reason='thin_content','cleaned_body_below_180'
  elif len(text)>12000 and len(links)>=20: qc,reason='list_page','large_multi_link_directory'
  elif len(links)>=25 and len(text)<2500: qc,reason='list_page','navigation_heavy'
  elif any(x in title for x in ['用户电子身份服务系统']) and len(text)<500: qc,reason='navigation_only','external_system_entry'
  elif len(text)>300: qc,reason='detail_content','stable_general_content'
  else: qc,reason='thin_content','insufficient_detail'
  q.update(quality_class=qc,diagnostic_reason=reason)
  nu=norm_url(r.get('url',''))
  if nu in pub_urls: q.update(duplicate_status='duplicate_url',duplicate_of='public_staging')
  elif r.get('content_hash') in pub_hash: q.update(duplicate_status='duplicate_hash',duplicate_of='public_staging')
  else:
   best=(0,'')
   a=tk(title)
   if len(a)>=8:
    for b,pid in pub_titles:
     if len(b)>=8:
      s=SequenceMatcher(None,a,b).ratio()
      if s>best[0]: best=(s,pid)
   if best[0]>=.94: q.update(duplicate_status='duplicate_title',duplicate_of=best[1])
   else: q.update(duplicate_status='unique')
  q['quality_gate_pass']=qc=='detail_content' and q['duplicate_status']=='unique'
 out.append(q)
OUT.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out),encoding='utf-8')
from collections import Counter
print(json.dumps({'rows':len(out),'quality':dict(Counter(x['quality_class'] for x in out)),'dedup':dict(Counter(x['duplicate_status'] for x in out)),'pass':sum(x['quality_gate_pass'] for x in out)},ensure_ascii=False))
