import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(r'D:\python_projects\tsinghua_ai')
OUT=ROOT/'data_second'/'restricted_expansion_v1'/'crawl'/'dynamic_section_links_clean.jsonl'
sections=[('办公指南','bgzn_show','#xinxizhinanzhidu .tab-pane.active'),('规章制度','gzzd_show','#xinxizhinanzhidu .tab-pane.active'),('公共信息服务','ggxxfw_show','#xinxifuwugongkai .tab-pane.active'),('网络信息服务','wlxxfw_show','#xinxifuwugongkai .tab-pane.active')]
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]
 pg=next(x for x in c.pages if '清华大学信息门户' in x.title()); rows=[]
 for section,eid,sel in sections:
  pg.locator('#'+eid).click(); pg.wait_for_timeout(1200)
  cont=pg.locator(sel)
  data=cont.locator('a').evaluate_all("""els=>els.filter(a=>a.offsetParent!==null).map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.getAttribute('href')||'',url:a.href||''}))""")
  for x in data:
   if x['text'] and x['href'] and not x['href'].startswith(('javascript:','#','mailto:')):
    rows.append({'section':section,**x})
 OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
 print(json.dumps({'count':len(rows),'rows':rows},ensure_ascii=False))
 b.close()
