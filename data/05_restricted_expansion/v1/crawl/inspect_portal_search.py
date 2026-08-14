import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); c=b.contexts[0]
 pg=next(x for x in c.pages if '清华大学信息门户' in x.title())
 inputs=pg.locator('input').evaluate_all("""els=>els.map(e=>({type:e.type,name:e.name,id:e.id,placeholder:e.placeholder,value:e.value,cls:e.className,outer:e.outerHTML.slice(0,500)}))""")
 forms=pg.locator('form').evaluate_all("""els=>els.map(e=>({action:e.action,method:e.method,id:e.id,cls:e.className,html:e.outerHTML.slice(0,1200)}))""")
 buttons=pg.locator('button').evaluate_all("""els=>els.map(e=>({text:(e.innerText||'').trim(),type:e.type,id:e.id,cls:e.className,outer:e.outerHTML.slice(0,500)}))""")
 print(json.dumps({'inputs':inputs,'forms':forms,'buttons':buttons},ensure_ascii=False,indent=2)); b.close()
