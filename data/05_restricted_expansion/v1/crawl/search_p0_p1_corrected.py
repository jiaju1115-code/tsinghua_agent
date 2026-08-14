from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote,urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(r'D:\python_projects\tsinghua_ai'); BASE=ROOT/'data_second'/'restricted_expansion_v1'; OUT=BASE/'crawl'/'p0_p1_search_results_corrected.jsonl'
TERMS=['住宿办理','食堂餐饮','校园交通班车','就医报销','奖学金助学金','就业手续','体育场地','校园网指南','学生事务','校园访问']
BLOCK=re.compile(r'(我的|个人|成绩|课表|消费|余额|申请状态|房间|病历|处方|通讯录|工资|薪酬)')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]; portal=next(x for x in c.pages if '清华大学信息门户' in x.title()); prefix=portal.url.split('/f/',1)[0]; rows=[]
 for term in TERMS:
  pg=c.new_page()
  try:
   target=prefix+'/f/info/portal_fg/common/yyfwsearch?searchParam='+quote(term)
   resp=pg.goto(target,wait_until='domcontentloaded',timeout=45000); pg.wait_for_timeout(1800)
   body=pg.locator('body').inner_text(timeout=5000)
   anchors=pg.locator('a').evaluate_all("""els=>els.filter(a=>a.offsetParent!==null).map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.href||'',cls:a.className||''})).filter(x=>x.text&&x.href)""")
   kept=0
   for a in anchors:
    txt=a['text'][:260]; href=a['href']
    if txt in {'首页','清华主页','English','登录门户'}: continue
    if not any(x in href for x in ['/f/','/b/','tsinghua.edu.cn']): continue
    rows.append({'discovered_at':datetime.now(timezone.utc).isoformat(),'search_term':term,'result_page_title':pg.title()[:160],'result_body_length':len(body),'title':txt,'url':href,'pre_safety_status':'excluded_personal_or_sensitive_link' if BLOCK.search(txt) else 'eligible_general_link','http_status':resp.status if resp else None}); kept+=1
   if kept==0: rows.append({'search_term':term,'result_page_title':pg.title()[:160],'result_body_length':len(body),'result_status':'no_candidate_links','http_status':resp.status if resp else None})
  except Exception as exc: rows.append({'search_term':term,'error_type':type(exc).__name__})
  finally: pg.close()
  OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
 seen=set();uniq=[]
 for r in rows:
  k=(r.get('search_term'),r.get('url') or r.get('result_status') or r.get('error_type'))
  if k not in seen: seen.add(k);uniq.append(r)
 OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in uniq),encoding='utf-8'); b.close()
 from collections import Counter
 print(json.dumps({'rows':len(uniq),'links':sum(bool(r.get('url')) for r in uniq),'by_term':dict(Counter(r.get('search_term') for r in uniq)),'excluded':sum(r.get('pre_safety_status')=='excluded_personal_or_sensitive_link' for r in uniq)},ensure_ascii=False))
