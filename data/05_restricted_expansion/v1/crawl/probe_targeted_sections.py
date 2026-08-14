from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


ROOT = Path(r"D:\python_projects\tsinghua_ai")
NAV = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "portal_navigation_links.jsonl"
OUT = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "targeted_section_probe.jsonl"

TARGET_TEXTS = {
    "师生综合服务大厅", "部门单位服务信息导引", "办公指南", "规章制度", "办事程序",
    "公共信息服务", "网络信息服务", "就医指南", "信息化用户服务", "后勤综合服务平台",
}


def proxy_url(current: str, direct: str) -> str:
    if "webvpn.tsinghua.edu.cn" not in current or "/f/" not in current:
        return direct
    p = urlsplit(direct)
    if p.hostname == "info.tsinghua.edu.cn":
        prefix = current.split("/f/", 1)[0]
        return prefix + p.path + (("?" + p.query) if p.query else "")
    return direct


def main():
    nav = [json.loads(x) for x in NAV.read_text(encoding="utf-8").splitlines() if x.strip()]
    selected = []
    for r in nav:
        if r["link_text"] in TARGET_TEXTS:
            selected.append(r)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        portal = next(pg for pg in context.pages if "清华大学信息门户" in pg.title())
        rows = []
        for item in selected:
            page = context.new_page()
            target = proxy_url(portal.url, item["url"])
            try:
                resp = page.goto(target, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(1500)
                title = page.title()
                body = re.sub(r"\s+", " ", page.locator("body").inner_text(timeout=10000)).strip()
                links = page.locator("a").count()
                rows.append({
                    "entry_text": item["link_text"], "requested_origin": item["origin"],
                    "final_origin": f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}",
                    "title": title[:160], "http_status": resp.status if resp else None,
                    "body_length": len(body), "link_count": links,
                    "login_page": "统一身份认证" in title or "用户登录" in body[:500],
                })
            except Exception as exc:
                rows.append({"entry_text": item["link_text"], "error_type": type(exc).__name__})
            finally:
                page.close()
        OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        browser.close()
    print(json.dumps({"probed": len(rows), "rows": rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
