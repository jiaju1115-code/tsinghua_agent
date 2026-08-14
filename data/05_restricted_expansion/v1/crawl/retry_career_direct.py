import json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(r'D:\python_projects\tsinghua_ai'); BASE=ROOT/'data_second'/'restricted_expansion_v1'; Q=BASE/'planning'/'targeted_fetch_queue.jsonl'; OUT=BASE/'crawl'/'career_direct_probe.jsonl'
items=[json.loads(x) for x in Q.read_text(encoding='utf-8').splitlines() if x.strip() and json.loads(x).get('seed_id')]
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]; rows=[]
 for item in items[:3]:
  pg=c.new_page()
  try:
   resp=pg.goto(item['url'],wait_until='domcontentloaded',timeout=40000); pg.wait_for_timeout(1500); body=pg.locator('body').inner_text(timeout=5000); u=urlsplit(pg.url)
   rows.append({'seed_id':item['seed_id'],'url':item['url'],'final_origin':f'{u.scheme}://{u.netloc}','title':pg.title()[:160],'http_status':resp.status if resp else None,'body_length':len(body),'login_or_auth_page':u.hostname=='id.tsinghua.edu.cn' or '统一身份认证' in pg.title() or '用户登录' in body[:500]})
  except Exception as e: rows.append({'seed_id':item['seed_id'],'url':item['url'],'error_type':type(e).__name__})
  finally: pg.close()
 OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8'); b.close(); print(json.dumps(rows,ensure_ascii=False))
