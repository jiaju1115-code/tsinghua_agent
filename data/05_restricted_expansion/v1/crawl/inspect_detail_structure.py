import json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(r'D:\python_projects\tsinghua_ai'); Q=ROOT/'data_second'/'restricted_expansion_v1'/'planning'/'targeted_fetch_queue.jsonl'
item=next(json.loads(x) for x in Q.read_text(encoding='utf-8').splitlines() if x.strip() and json.loads(x).get('discovery_category')=='医疗健康')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]; portal=next(x for x in c.pages if '清华大学信息门户' in x.title()); prefix=portal.url.split('/f/',1)[0]; u=urlsplit(item['url']); target=prefix+u.path+'?'+u.query; pg=c.new_page(); events=[]
 pg.on('response',lambda r: events.append({'path':urlsplit(r.url).path,'status':r.status,'type':r.request.resource_type}) if r.request.resource_type in {'xhr','fetch','document'} else None)
 pg.goto(target,wait_until='networkidle',timeout=60000); pg.wait_for_timeout(3000)
 frames=[]
 for i,fr in enumerate(pg.frames):
  try: frames.append({'i':i,'origin':f'{urlsplit(fr.url).scheme}://{urlsplit(fr.url).netloc}','path':urlsplit(fr.url).path,'body_length':len(fr.locator('body').inner_text(timeout=5000)),'iframes':fr.locator('iframe').count()})
  except Exception as e: frames.append({'i':i,'error':type(e).__name__})
 sels=[]
 for sel in ['article','.article','.content','.detail-content','.xxnr','.news-content','.main-content','main','.info-content','.content-box','.zw','.text','.TRS_Editor']:
  try:
   loc=pg.locator(sel); lens=[]
   for i in range(min(loc.count(),5)): lens.append(len(loc.nth(i).inner_text(timeout=3000)))
   if lens:sels.append({'selector':sel,'lengths':lens})
  except Exception:pass
 print(json.dumps({'title':pg.title(),'frames':frames,'selectors':sels,'events':events[-40:]},ensure_ascii=False)); pg.close(); b.close()
