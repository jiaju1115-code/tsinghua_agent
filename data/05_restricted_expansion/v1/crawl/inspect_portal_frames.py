from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    for c in b.contexts:
        for pg in c.pages:
            try:
                title=pg.title()
                if '清华大学后勤综合服务平台' not in title and '清华大学医院' not in title: continue
                print('PAGE',urlsplit(pg.url).netloc,title)
                for i,fr in enumerate(pg.frames):
                    try:
                        print('FRAME',i,urlsplit(fr.url).netloc,fr.locator('a').count(),fr.locator('body').inner_text(timeout=3000)[:160].replace('\n',' '))
                    except Exception as e:
                        print('FRAME',i,urlsplit(fr.url).netloc,'ERR',type(e).__name__)
            except Exception: pass
    b.close()
