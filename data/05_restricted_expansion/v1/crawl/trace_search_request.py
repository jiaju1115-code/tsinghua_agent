import json
from urllib.parse import urlsplit, parse_qsl
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]
 portal=next(x for x in c.pages if '清华大学信息门户' in x.title()); pg=c.new_page(); events=[]
 def note(req):
  u=urlsplit(req.url)
  if u.scheme in {'http','https'}:
   events.append({'kind':'request','origin':f'{u.scheme}://{u.netloc}','path':u.path,'query_keys':[k for k,v in parse_qsl(u.query,keep_blank_values=True)],'method':req.method,'resource_type':req.resource_type})
 pg.on('request',note)
 pg.goto(portal.url,wait_until='domcontentloaded',timeout=45000); pg.locator('#searchText').fill('住宿 办理');
 try: pg.locator('#searchBtn').click(); pg.wait_for_timeout(3500)
 except Exception: pass
 u=urlsplit(pg.url); result={'final_origin':f'{u.scheme}://{u.netloc}','final_path':u.path,'final_query_keys':[k for k,v in parse_qsl(u.query,keep_blank_values=True)],'title':pg.title(),'events':events[-60:]}
 print(json.dumps(result,ensure_ascii=False)); pg.close(); b.close()
