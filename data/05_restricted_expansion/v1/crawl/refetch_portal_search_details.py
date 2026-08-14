from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(r'D:\python_projects\tsinghua_ai'); BASE=ROOT/'data_second'/'restricted_expansion_v1'; Q=BASE/'planning'/'targeted_fetch_queue.jsonl'; OUT=BASE/'crawl'/'portal_search_refetch_results.jsonl'; SAFE=BASE/'safety_gate'/'private_sensitive_gate_refetch.jsonl'
PERSONAL=re.compile(r'(我的课表|我的成绩|个人成绩|选课结果|申请状态|校园卡消费|余额查询|个人病历|个人处方|住宿房间|身份证号|学号[:：]|我的申请)')
SECURITY=re.compile(r'(Authorization Header|CAS Ticket|Session ID|绕过认证|漏洞利用|后台密码|服务器口令)',re.I)
SENSITIVE=re.compile(r'(内部通讯录|全校通讯录|人员名单及联系方式|身份证件信息)')
def clean(t):
 lines=[re.sub(r'\s+',' ',x).strip() for x in (t or '').splitlines()]
 common={'清华主页','清华新闻','清华党建','English','学生版','怀念老门户','首页','校内资讯','活动日程','登录门户','意见 建议','帮助','手机浏览器'}
 return '\n'.join(x for x in lines if x and x not in common)
def gate(title,body):
 x=title+'\n'+body
 if SECURITY.search(x):return 'credential_or_security','security pattern'
 if PERSONAL.search(x):return 'individualized_private','personal instance pattern'
 if SENSITIVE.search(x):return 'sensitive_internal','sensitive internal pattern'
 if len(body)<180:return 'unclear','body below 180 after networkidle'
 return 'safe_general_content','general reusable content'

items=[json.loads(x) for x in Q.read_text(encoding='utf-8').splitlines() if x.strip() and json.loads(x).get('queue_source')=='portal_search']
rows=[json.loads(x) for x in OUT.read_text(encoding='utf-8').splitlines() if x.strip()] if OUT.exists() else []; safety=[json.loads(x) for x in SAFE.read_text(encoding='utf-8').splitlines() if x.strip()] if SAFE.exists() else []; done={x.get('url') for x in rows}; existing=list((BASE/'extracted').glob('RESV1-*.md')); n=max([int(x.stem.split('-')[-1]) for x in existing]+[0])
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]; portal=next(x for x in c.pages if '清华大学信息门户' in x.title()); prefix=portal.url.split('/f/',1)[0]
 for item in items:
  if item['url'] in done: continue
  pg=c.new_page(); direct=item['url']; u=urlsplit(direct); target=prefix+u.path+(('?'+u.query) if u.query else '')
  try:
   resp=pg.goto(target,wait_until='domcontentloaded',timeout=35000); pg.wait_for_timeout(7000); title=pg.title().strip() or item['title_hint'][:120]; body=clean(pg.locator('body').inner_text(timeout=10000));
   if len(body)>30000:body=body[:30000]
   st,reason=gate(title,body); rid='';sf='';ch=''
   if st=='safe_general_content':
    n+=1;rid=f'RESV1-{n:04d}';sf=f'extracted/{rid}.md';content=f"# {title}\n\n- Source: {direct}\n- Auth: existing_sso_session via WebVPN\n- Discovery: portal_search / {item['discovery_category']}\n\n{body}\n";(BASE/sf).write_text(content,encoding='utf-8',newline='\n');ch=hashlib.sha256(re.sub(r'\s+',' ',content.strip()).encode()).hexdigest()
   links=pg.locator('a').count(); rec={'restricted_id':rid,'title':title,'title_hint':item['title_hint'],'url':direct,'category':item['discovery_category'],'priority':item['priority'],'http_status':resp.status if resp else None,'fetch_status':'fetched','private_sensitive_status':st,'reason':reason,'body_length':len(body),'link_count':links,'source_file':sf,'content_hash':ch,'crawl_timestamp':datetime.now(timezone.utc).isoformat()};rows.append(rec);safety.append({k:rec.get(k) for k in ['restricted_id','title','url','private_sensitive_status','reason','source_file']})
  except Exception as e:rows.append({'title_hint':item['title_hint'],'url':direct,'category':item['discovery_category'],'fetch_status':'failed','error_type':type(e).__name__})
  finally:pg.close()
  OUT.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8');SAFE.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in safety),encoding='utf-8')
 b.close()
from collections import Counter
print(json.dumps({'processed':len(rows),'fetch':dict(Counter(x.get('fetch_status') for x in rows)),'safety':dict(Counter(x.get('private_sensitive_status') for x in rows)),'saved':sum(bool(x.get('source_file')) for x in rows)},ensure_ascii=False))
