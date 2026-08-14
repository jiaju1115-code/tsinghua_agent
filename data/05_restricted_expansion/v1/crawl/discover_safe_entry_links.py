from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


ROOT = Path(r"D:\python_projects\tsinghua_ai")
NAV = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "portal_navigation_links.jsonl"
OUT = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "safe_entry_links.jsonl"
TARGETS = {"部门单位服务信息导引", "办事程序", "就医指南", "后勤综合服务平台"}
BLOCK_TEXT = re.compile(r"(我的|个人|本人|查询结果|消费|余额|邮箱|邮件|密码|账号|工资|薪酬|成绩|课表|选课结果|申请状态|房间|病历|处方|缴费记录|通讯录)")
BLOCK_URL = re.compile(r"(logout|token=|ticket=|session=|userinfo|profile|mail|password)", re.I)


def proxify(portal_url: str, direct: str) -> str:
    if "webvpn.tsinghua.edu.cn" not in portal_url or "/f/" not in portal_url:
        return direct
    p = urlsplit(direct)
    if p.hostname == "info.tsinghua.edu.cn":
        return portal_url.split("/f/", 1)[0] + p.path + (("?" + p.query) if p.query else "")
    return direct


def main():
    nav = [json.loads(x) for x in NAV.read_text(encoding="utf-8").splitlines() if x.strip()]
    selected = []
    seen_select = set()
    for r in nav:
        if r["link_text"] in TARGETS and r["link_text"] not in seen_select:
            selected.append(r)
            seen_select.add(r["link_text"])
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        portal = next(pg for pg in context.pages if "清华大学信息门户" in pg.title())
        out = []
        for entry in selected:
            pg = context.new_page()
            try:
                pg.goto(proxify(portal.url, entry["url"]), wait_until="domcontentloaded", timeout=45000)
                pg.wait_for_timeout(1800)
                anchors = pg.locator("a").evaluate_all("""els => els.map(a => ({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '),href:a.href||''}))""")
                for a in anchors:
                    text = (a.get("text") or "")[:180]
                    href = a.get("href") or ""
                    if not text or not href.startswith(("http://", "https://")) or BLOCK_URL.search(href):
                        continue
                    safety = "excluded_personal_or_sensitive_link" if BLOCK_TEXT.search(text) else "eligible_general_link"
                    parts = urlsplit(href)
                    out.append({
                        "discovered_at": datetime.now(timezone.utc).isoformat(), "source_entry": entry["link_text"],
                        "parent_title": pg.title()[:160], "parent_url": pg.url, "link_text": text, "url": href,
                        "origin": f"{parts.scheme}://{parts.netloc}", "pre_safety_status": safety,
                    })
            except Exception as exc:
                out.append({"source_entry": entry["link_text"], "error_type": type(exc).__name__})
            finally:
                pg.close()
        seen = set()
        unique = []
        for r in out:
            key = (r.get("source_entry"), r.get("link_text"), r.get("url"))
            if key not in seen:
                seen.add(key); unique.append(r)
        OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in unique), encoding="utf-8")
        browser.close()
    from collections import Counter
    print(json.dumps({"links": len(unique), "by_entry": dict(Counter(r.get("source_entry") for r in unique)), "pre_safety": dict(Counter(r.get("pre_safety_status") for r in unique))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
