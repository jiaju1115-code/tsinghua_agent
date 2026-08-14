import json
from playwright.sync_api import sync_playwright

targets={"师生综合服务大厅","部门单位服务信息导引","办公指南","规章制度","办事程序","规章制度检索平台","公共信息服务","网络信息服务","校园地图","就医指南","信息化用户服务","体育场地预定","后勤综合服务平台"}
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 out=[]
 for c in b.contexts:
  for pg in c.pages:
   try:
    if '清华大学信息门户' not in pg.title(): continue
    rows=pg.locator('a').evaluate_all("""els=>els.map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.getAttribute('href')||'',onclick:a.getAttribute('onclick')||'',target:a.getAttribute('target')||'',id:a.id||'',cls:a.className||''}))""")
    for r in rows:
     if r['text'] in targets: out.append(r)
   except Exception: pass
 print(json.dumps(out,ensure_ascii=False,indent=2))
 b.close()
