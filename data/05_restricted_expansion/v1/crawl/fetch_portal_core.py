from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


ROOT=Path(r"D:\python_projects\tsinghua_ai")
BASE=ROOT/"data_second"/"restricted_expansion_v1"
INP=BASE/"crawl"/"dynamic_section_links_clean.jsonl"
META=BASE/"crawl"/"portal_core_fetch_results.jsonl"
SAFETY=BASE/"safety_gate"/"private_sensitive_gate_results.jsonl"
EXTRACTED=BASE/"extracted"
EXTRACTED.mkdir(parents=True,exist_ok=True)

PRE_EXCLUDE={"网费查询":("individualized_private","账户查询入口"),"电话查询":("sensitive_internal","可能涉及未公开内部通讯录")}
PERSONAL=re.compile(r"(我的课表|我的成绩|个人成绩|选课结果|申请状态|校园卡消费|余额查询|个人病历|个人处方|住宿房间|身份证号|学号[:：]|我的申请)")
SECURITY=re.compile(r"(Authorization Header|CAS Ticket|Session ID|绕过认证|漏洞利用|后台密码|服务器口令)",re.I)
SENSITIVE=re.compile(r"(内部通讯录|全校通讯录|人员名单及联系方式|身份证件信息)")

def clean(text):
    lines=[re.sub(r"\s+"," ",x).strip() for x in (text or '').splitlines()]
    drop={"首页","清华主页","清华新闻","清华党建","English","学生版","怀念老门户","意见 建议","帮助","手机浏览器"}
    return "\n".join(x for x in lines if x and x not in drop)

def classify(title,body):
    sample=title+'\n'+body
    if SECURITY.search(sample): return 'credential_or_security','命中凭据或安全内部信息模式'
    if PERSONAL.search(sample): return 'individualized_private','命中个人实例数据模式'
    if SENSITIVE.search(sample): return 'sensitive_internal','命中敏感内部信息模式'
    if len(body)<120: return 'unclear','正文过短，无法确认通用知识属性'
    return 'safe_general_content','通用规则、服务说明或资源导航；未发现个人/敏感字段'

def category(title,section):
    if title in {'本科生专业','研究生专业'}: return '教务与学籍'
    if title in {'校园地图'}: return '校园访问'
    if title in {'就医指南'}: return '医疗健康'
    if title in {'出境指南'}: return '国际事务与签证'
    if title in {'信息化用户服务'}: return '网络与信息化'
    if title in {'实验室管理'}: return '科研参与与资源导航'
    if title in {'教职工发展'}: return '教学与培养'
    return '校园综合服务'

with sync_playwright() as p:
    browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222'); context=browser.contexts[0]
    portal=next(x for x in context.pages if '清华大学信息门户' in x.title())
    prefix=portal.url.split('/f/',1)[0]
    rows=[json.loads(x) for x in INP.read_text(encoding='utf-8').splitlines() if x.strip()]
    meta=[json.loads(x) for x in META.read_text(encoding='utf-8').splitlines() if x.strip()] if META.exists() else []
    safety=[json.loads(x) for x in SAFETY.read_text(encoding='utf-8').splitlines() if x.strip()] if SAFETY.exists() else []
    done={(x.get('seed_title') or x.get('title'),x.get('url')) for x in meta}
    n=max([int(x.get('restricted_id','').split('-')[-1]) for x in meta if x.get('restricted_id','').startswith('RESV1-')]+[0])
    for row in rows:
        title0=row['text']
        if (title0,row['url']) in done:
            continue
        if title0 in PRE_EXCLUDE:
            st,reason=PRE_EXCLUDE[title0]
            safety.append({'restricted_id':'','title':title0,'url':row['url'],'private_sensitive_status':st,'reason':reason,'source_group':'portal_dynamic_section','saved_body':False})
            meta.append({'title':title0,'url':row['url'],'fetch_status':'pre_safety_excluded','private_sensitive_status':st})
            continue
        pg=context.new_page(); direct=row['url']; u=urlsplit(direct); target=prefix+u.path+(('?'+u.query) if u.query else '')
        try:
            resp=pg.goto(target,wait_until='domcontentloaded',timeout=45000); pg.wait_for_timeout(1200)
            title=pg.title().strip() or title0
            selectors=['article','.article','.content','.detail-content','.xxnr','.news-content','.main-content','main','body']
            candidates=[]; chosen='body'
            for sel in selectors:
                try:
                    loc=pg.locator(sel)
                    for i in range(min(loc.count(),3)):
                        txt=clean(loc.nth(i).inner_text(timeout=3000))
                        if txt: candidates.append((len(txt),sel,txt))
                except Exception: pass
            candidates.sort(reverse=True)
            body=candidates[0][2] if candidates else ''
            # Body fallback can include full template; keep only once and cap pathological pages.
            if len(body)>30000: body=body[:30000]
            chosen=candidates[0][1] if candidates else 'none'
            st,reason=classify(title,body)
            rid=''
            saved=False
            source_file=''
            ch=''
            if st=='safe_general_content':
                n+=1; rid=f'RESV1-{n:04d}'; source_file=f'extracted/{rid}.md'; path=BASE/source_file
                content=f"# {title}\n\n- Source: {direct}\n- Auth: existing_sso_session via WebVPN\n- Discovery: {row['section']}\n\n{body}\n"
                path.write_text(content,encoding='utf-8',newline='\n'); ch=hashlib.sha256(re.sub(r'\s+',' ',content.strip()).encode()).hexdigest(); saved=True
            safety.append({'restricted_id':rid,'title':title,'url':direct,'private_sensitive_status':st,'reason':reason,'source_group':'portal_dynamic_section','saved_body':saved})
            anchors=[]
            if st=='safe_general_content':
                try:
                    anchors=pg.locator('a').evaluate_all("""els=>els.map(a=>({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.href||''})).filter(x=>x.text&&x.href)""")[:80]
                except Exception: pass
            meta.append({'restricted_id':rid,'title':title,'seed_title':title0,'url':direct,'authenticated_url_origin':'https://webvpn.tsinghua.edu.cn','http_status':resp.status if resp else None,'body_length':len(body),'link_count':len(anchors),'outbound_links':anchors,'fetch_status':'fetched','private_sensitive_status':st,'source_file':source_file,'content_hash':ch,'selector_used':chosen,'discovery_category':row['section'],'category':category(title0,row['section']),'crawl_timestamp':datetime.now(timezone.utc).isoformat()})
        except Exception as exc:
            meta.append({'title':title0,'url':direct,'fetch_status':'failed','error_type':type(exc).__name__})
        finally: pg.close()
        META.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in meta),encoding='utf-8')
        SAFETY.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in safety),encoding='utf-8')
    browser.close()
    from collections import Counter
    print(json.dumps({'fetched':sum(x.get('fetch_status')=='fetched' for x in meta),'saved_safe':sum(x.get('private_sensitive_status')=='safe_general_content' for x in meta),'safety':dict(Counter(x.get('private_sensitive_status') for x in safety)),'failed':sum(x.get('fetch_status')=='failed' for x in meta)},ensure_ascii=False))
