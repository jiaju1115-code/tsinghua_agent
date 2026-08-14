import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 c=b.contexts[0]; pg=next(x for x in c.pages if '清华大学信息门户' in x.title())
 for eid in ['bgzn_show','gzzd_show','ggxxfw_show','wlxxfw_show']:
  try:
   a=pg.locator('#'+eid)
   a.click(timeout=10000); pg.wait_for_timeout(1200)
   info=a.evaluate("""a=>{let out=[];let e=a;for(let i=0;i<7&&e;i++,e=e.parentElement){out.push({tag:e.tagName,id:e.id||'',cls:e.className||'',text:(e.innerText||'').trim().replace(/\\s+/g,' ').slice(0,300)})}return out}""")
   visibles=pg.locator('div:visible').evaluate_all("""els=>els.map(e=>({id:e.id||'',cls:e.className||'',text:(e.innerText||'').trim().replace(/\\s+/g,' ').slice(0,500),links:e.querySelectorAll('a').length})).filter(x=>x.links>0&&x.text.length>10).sort((a,b)=>a.text.length-b.text.length).slice(0,25)""")
   print(json.dumps({'eid':eid,'ancestors':info,'visible_divs':visibles},ensure_ascii=False))
  except Exception as e: print(json.dumps({'eid':eid,'error':type(e).__name__}))
 b.close()
