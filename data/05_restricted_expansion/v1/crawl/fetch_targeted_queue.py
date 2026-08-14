from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(r'D:\python_projects\tsinghua_ai'); BASE=ROOT/'data_second'/'restricted_expansion_v1'; QUEUE=BASE/'planning'/'targeted_fetch_queue.jsonl'; META=BASE/'crawl'/'targeted_fetch_results.jsonl'; SAFETY=BASE/'safety_gate'/'private_sensitive_gate_targeted.jsonl'
PERSONAL=re.compile(r'(我的课表|我的成绩|个人成绩|选课结果|申请状态|校园卡消费|余额查询|个人病历|个人处方|住宿房间|身份证号|学号[:：]|我的申请|个人简历)')
SECURITY=re.compile(r'(Authorization Header|CAS Ticket|Session ID|绕过认证|漏洞利用|后台密码|服务器口令)',re.I)
SENSITIVE=re.compile(r'(内部通讯录|全校通讯录|人员名单及联系方式|身份证件信息)')
NEWS=re.compile(r'(举行|启动仪式|获奖|佳绩|交流会|活动回顾|新闻)')
def clean(text): return '\n'.join(re.sub(r'\s+',' ',x).strip() for x in (text or '').splitlines() if re.sub(r'\s+',' ',x).strip())
def gate(title,body):
 x=title+'\n'+body
 if SECURITY.search(x): return 'credential_or_security','security pattern'
 if PERSONAL.search(x): return 'individualized_private','personal instance pattern'
 if SENSITIVE.search(x): return 'sensitive_internal','sensitive internal pattern'
 if len(body)<160: return 'unclear','body below 160 characters'
 return 'safe_general_content','general reusable content'

queue=[json.loads(x) for x in QUEUE.read_text(encoding='utf-8').splitlines() if x.strip()]
meta=[json.loads(x) for x in META.read_text(encoding='utf-8').splitlines() if x.strip()] if META.exists() else []; safety=[json.loads(x) for x in SAFETY.read_text(encoding='utf-8').splitlines() if x.strip()] if SAFETY.exists() else []
done={x.get('url') for x in meta}; existing=list((BASE/'extracted').glob('RESV1-*.md')); n=max([int(x.stem.split('-')[-1]) for x in existing]+[0])
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]; portal=next(x for x in c.pages if '清华大学信息门户' in x.title()); prefix=portal.url.split('/f/',1)[0]
 for item in queue:
  direct=item['url']
  if direct in done: continue
  pg=c.new_page()
  try:
   u=urlsplit(direct)
   target=prefix+u.path+(('?'+u.query) if u.query else '') if u.hostname in {'info.tsinghua.edu.cn','career.tsinghua.edu.cn'} else direct
   resp=pg.goto(target,wait_until='domcontentloaded',timeout=35000); pg.wait_for_timeout(1000)
   title=pg.title().strip() or item['title_hint'][:120]; final=pg.url; text=clean(pg.locator('body').inner_text(timeout=8000));
   if len(text)>25000:text=text[:25000]
   is_login='id.tsinghua.edu.cn' in final or '统一身份认证' in title or ('用户登录' in text[:500] and len(text)<1000)
   if is_login: st,reason='unclear','session_or_permission_insufficient'; fetch_status='login_required_after_auth'; body=''
   else: body=text; st,reason=gate(title,body); fetch_status='fetched'
   rid=''; sf=''; ch=''
   if st=='safe_general_content':
    n+=1; rid=f'RESV1-{n:04d}'; sf=f'extracted/{rid}.md'; content=f"# {title}\n\n- Source: {direct}\n- Auth: existing_sso_session via WebVPN\n- Discovery: {item['queue_source']} / {item['discovery_category']}\n\n{body}\n"; (BASE/sf).write_text(content,encoding='utf-8',newline='\n'); ch=hashlib.sha256(re.sub(r'\s+',' ',content.strip()).encode()).hexdigest()
   links=[]
   if st=='safe_general_content':
    try: links=pg.locator('a').evaluate_all("""els=>els.map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.href||''})).filter(x=>x.text&&x.href).slice(0,100)""")
    except Exception: pass
   rec={'restricted_id':rid,'seed_id':item.get('seed_id',''),'queue_source':item['queue_source'],'title_hint':item['title_hint'],'title':title,'url':direct,'final_origin':f'{urlsplit(final).scheme}://{urlsplit(final).netloc}','discovery_category':item['discovery_category'],'priority':item['priority'],'fetch_status':fetch_status,'http_status':resp.status if resp else None,'private_sensitive_status':st,'reason':reason,'body_length':len(body),'link_count':len(links),'outbound_links':links,'source_file':sf,'content_hash':ch,'crawl_timestamp':datetime.now(timezone.utc).isoformat()}; meta.append(rec); safety.append({k:rec.get(k) for k in ['restricted_id','seed_id','title','url','private_sensitive_status','reason','source_file']})
  except Exception as exc: meta.append({'url':direct,'seed_id':item.get('seed_id',''),'title_hint':item['title_hint'],'discovery_category':item['discovery_category'],'fetch_status':'failed','error_type':type(exc).__name__})
  finally: pg.close()
  META.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in meta),encoding='utf-8'); SAFETY.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in safety),encoding='utf-8')
 b.close()
from collections import Counter
print(json.dumps({'processed':len(meta),'fetch':dict(Counter(x.get('fetch_status') for x in meta)),'safety':dict(Counter(x.get('private_sensitive_status') for x in meta)),'saved':sum(bool(x.get('source_file')) for x in meta)},ensure_ascii=False))
