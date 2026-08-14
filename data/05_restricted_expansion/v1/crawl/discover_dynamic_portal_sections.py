from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT=Path(r"D:\python_projects\tsinghua_ai")
OUT=ROOT/"data_second"/"restricted_expansion_v1"/"crawl"/"dynamic_portal_sections.jsonl"
SECTIONS=[("办公指南","bgzn_show"),("规章制度","gzzd_show"),("公共信息服务","ggxxfw_show"),("网络信息服务","wlxxfw_show")]
BLOCK=re.compile(r"(我的|个人|消费|余额|邮箱|密码|账号|成绩|课表|申请状态|房间|病历|处方|缴费记录|通讯录)")

with sync_playwright() as p:
    b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    c=b.contexts[0]
    pg=next(x for x in c.pages if '清华大学信息门户' in x.title())
    rows=[]
    for section,element_id in SECTIONS:
        try:
            pg.locator('#'+element_id).click(timeout=10000)
            pg.wait_for_timeout(1800)
            anchors=pg.locator('a').evaluate_all("""els=>els.map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.getAttribute('href')||'',abs:a.href||'',id:a.id||'',cls:a.className||''}))""")
            for a in anchors:
                text=(a.get('text') or '')[:180]
                href=a.get('href') or ''
                if not text or not href: continue
                # Keep only links visible after the section switch and likely attached to content.
                loc=pg.locator(f'a[href="{href.replace(chr(34), chr(92)+chr(34))}"]')
                visible=False
                for i in range(min(loc.count(),5)):
                    try:
                        if loc.nth(i).is_visible(): visible=True; break
                    except Exception: pass
                if not visible: continue
                rows.append({'discovered_at':datetime.now(timezone.utc).isoformat(),'section':section,'link_text':text,'href':href,'url':a.get('abs') or href,'element_id':a.get('id'),'class':a.get('cls'),'pre_safety_status':'excluded_personal_or_sensitive_link' if BLOCK.search(text) else 'eligible_general_link'})
        except Exception as exc:
            rows.append({'section':section,'error_type':type(exc).__name__})
    seen=set();uniq=[]
    for r in rows:
        k=(r.get('section'),r.get('link_text'),r.get('href'))
        if k not in seen: seen.add(k);uniq.append(r)
    OUT.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in uniq),encoding='utf-8')
    b.close()
    from collections import Counter
    print(json.dumps({'links':len(uniq),'by_section':dict(Counter(r.get('section') for r in uniq)),'excluded':sum(r.get('pre_safety_status')=='excluded_personal_or_sensitive_link' for r in uniq)},ensure_ascii=False))
