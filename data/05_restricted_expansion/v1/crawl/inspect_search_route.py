import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]; pg=next(x for x in c.pages if '清华大学信息门户' in x.title())
 scripts=pg.locator('script[src]').evaluate_all("els=>els.map(e=>e.src)")
 out=[]
 for src in scripts:
  if any(x in src for x in ['xnzxIndex','search','suggest']):
   try:
    txt=pg.evaluate("async u=>await (await fetch(u)).text()",src)
    hits=[]
    for needle in ['searchBtn','searchText','search/info','window.location','location.href']:
     start=0
     while True:
      i=txt.find(needle,start)
      if i<0: break
      hits.append(txt[max(0,i-350):min(len(txt),i+650)])
      start=i+len(needle)
    out.append({'src':src,'hits':hits[:12]})
   except Exception as e: out.append({'src':src,'error':type(e).__name__})
 print(json.dumps(out,ensure_ascii=False)); b.close()
