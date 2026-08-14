from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


ROOT=Path(r"D:\python_projects\tsinghua_ai")
OUT=ROOT/"data_second"/"restricted_expansion_v1"/"crawl"/"visible_safe_page_links.jsonl"
SAFE_TITLES={"清华大学后勤综合服务平台","清华大学医院","就医指南","体检指南","报销指南","妇儿保健","疫苗接种","公疗政策","医保政策","学校规定","管理细则"}
BLOCK=re.compile(r"(我的|个人|消费|余额|邮箱|密码|账号|成绩|课表|申请状态|房间|病历|处方|缴费记录|通讯录)")

with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    out=[]
    for c in b.contexts:
        for pg in c.pages:
            try:
                title=pg.title()
                if title not in SAFE_TITLES: continue
                anchors=pg.locator("a").evaluate_all("""els=>els.map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.href||''}))""")
                for a in anchors:
                    text=(a.get('text') or '')[:180]; href=a.get('href') or ''
                    if not text or not href.startswith(('http://','https://')): continue
                    u=urlsplit(href)
                    out.append({'discovered_at':datetime.now(timezone.utc).isoformat(),'directory_title':title,'directory_url':pg.url,'link_text':text,'url':href,'origin':f'{u.scheme}://{u.netloc}','pre_safety_status':'excluded_personal_or_sensitive_link' if BLOCK.search(text) else 'eligible_general_link'})
            except Exception: pass
    seen=set(); unique=[]
    for r in out:
        k=(r['directory_title'],r['link_text'],r['url'])
        if k not in seen: seen.add(k);unique.append(r)
    OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in unique),encoding='utf-8')
    b.close()
    print(json.dumps({'links':len(unique),'titles':sorted(set(r['directory_title'] for r in unique))},ensure_ascii=False))
