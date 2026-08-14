from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(r'D:\python_projects\tsinghua_ai'); OUT=ROOT/'data_second'/'restricted_expansion_v1'/'crawl'/'p0_p1_search_results.jsonl'
TERMS=['住宿 办理','食堂 餐饮 服务','校园交通 班车','就医 报销 指南','奖学金 助学金 申请','就业 手续 办理','体育场地 预约','校园网 使用 指南','学生事务 办理','校园访问 入校']
BLOCK=re.compile(r'(我的|个人|成绩|课表|消费|余额|申请状态|房间|病历|处方|通讯录)')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]; portal=next(x for x in c.pages if '清华大学信息门户' in x.title()); rows=[]
 for term in TERMS:
  pg=c.new_page()
  try:
   pg.goto(portal.url,wait_until='domcontentloaded',timeout=45000); pg.locator('#searchText').fill(term); pg.locator('#searchBtn').click(); pg.wait_for_timeout(2200)
   anchors=pg.locator('a').evaluate_all("""els=>els.filter(a=>a.offsetParent!==null).map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.href||'',cls:a.className||''})).filter(x=>x.text&&x.href)""")
   for a in anchors:
    txt=a['text'][:220]; href=a['href']
    if 'template/detail' not in href and 'department' not in href: continue
    rows.append({'discovered_at':datetime.now(timezone.utc).isoformat(),'search_term':term,'title':txt,'url':href,'pre_safety_status':'excluded_personal_or_sensitive_link' if BLOCK.search(txt) else 'eligible_general_link'})
  except Exception as exc: rows.append({'search_term':term,'error_type':type(exc).__name__})
  finally: pg.close()
  OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
 seen=set();uniq=[]
 for r in rows:
  k=r.get('url') or (r.get('search_term'),r.get('error_type'))
  if k not in seen: seen.add(k);uniq.append(r)
 OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in uniq),encoding='utf-8'); b.close()
 from collections import Counter
 print(json.dumps({'unique':len(uniq),'by_term':dict(Counter(r.get('search_term') for r in uniq)),'excluded':sum(r.get('pre_safety_status')=='excluded_personal_or_sensitive_link' for r in uniq)},ensure_ascii=False))
