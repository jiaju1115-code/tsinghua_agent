from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


ROOT = Path(r"D:\python_projects\tsinghua_ai")
SAFE = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "safe_entry_links.jsonl"
OUT = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "curated_directory_links.jsonl"
TARGETS = {
    ("后勤综合服务平台", "服务指南"),
    ("就医指南", "就医指南"), ("就医指南", "体检指南"), ("就医指南", "报销指南"),
    ("就医指南", "妇儿保健"), ("就医指南", "疫苗接种"), ("就医指南", "公疗政策"),
    ("就医指南", "医保政策"), ("就医指南", "学校规定"), ("就医指南", "管理细则"),
}
BLOCK = re.compile(r"(我的|个人|消费|余额|邮箱|密码|账号|成绩|课表|申请状态|房间|病历|处方|缴费记录|通讯录)")


def main():
    rows = [json.loads(x) for x in SAFE.read_text(encoding="utf-8").splitlines() if x.strip()]
    selected = []
    seen = set()
    for r in rows:
        key = (r.get("source_entry"), r.get("link_text"))
        if key in TARGETS and key not in seen:
            selected.append(r); seen.add(key)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        out = []
        for item in selected:
            pg = context.new_page()
            try:
                pg.goto(item["parent_url"], wait_until="domcontentloaded", timeout=45000)
                pg.wait_for_timeout(1200)
                loc = pg.get_by_role("link", name=item["link_text"], exact=True)
                if loc.count() == 0:
                    loc = pg.locator("a", has_text=item["link_text"])
                if loc.count() == 0:
                    out.append({"directory": item["link_text"], "error": "link_not_found"}); pg.close(); continue
                before = len(context.pages)
                try:
                    loc.first.click(timeout=15000)
                except Exception:
                    pg.goto(item["url"], wait_until="domcontentloaded", timeout=45000)
                pg.wait_for_timeout(1800)
                target_page = context.pages[-1] if len(context.pages) > before else pg
                anchors = target_page.locator("a").evaluate_all("""els => els.map(a => ({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.href||''}))""")
                for a in anchors:
                    text = (a.get("text") or "")[:180]
                    href = a.get("href") or ""
                    if not text or not href.startswith(("http://", "https://")):
                        continue
                    parts = urlsplit(href)
                    out.append({
                        "source_entry": item["source_entry"], "directory": item["link_text"],
                        "directory_title": target_page.title()[:160], "directory_url": target_page.url,
                        "link_text": text, "url": href, "origin": f"{parts.scheme}://{parts.netloc}",
                        "pre_safety_status": "excluded_personal_or_sensitive_link" if BLOCK.search(text) else "eligible_general_link",
                    })
                if target_page is not pg: target_page.close()
            except Exception as exc:
                out.append({"source_entry": item.get("source_entry"), "directory": item.get("link_text"), "error_type": type(exc).__name__})
            finally:
                if not pg.is_closed(): pg.close()
        uniq=[]; keys=set()
        for r in out:
            k=(r.get("directory"),r.get("link_text"),r.get("url"))
            if k not in keys: keys.add(k); uniq.append(r)
        OUT.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in uniq),encoding="utf-8")
        browser.close()
    from collections import Counter
    print(json.dumps({"directories":len(selected),"links":len(uniq),"by_directory":dict(Counter(r.get("directory") for r in uniq)),"errors":sum(bool(r.get("error") or r.get("error_type")) for r in uniq)},ensure_ascii=False))


if __name__ == "__main__": main()
