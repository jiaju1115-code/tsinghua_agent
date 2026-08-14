from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


ROOT = Path(r"D:\python_projects\tsinghua_ai")
OUT = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "portal_navigation_links.jsonl"


def safe_url(url: str) -> bool:
    lower = (url or "").lower()
    blocked = ["logout", "password", "token=", "ticket=", "session=", "userinfo", "profile", "mail"]
    return url.startswith(("http://", "https://")) and not any(x in lower for x in blocked)


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    rows = []
    for context in browser.contexts:
        for page in context.pages:
            try:
                if "清华大学信息门户" not in page.title():
                    continue
                page.wait_for_timeout(1500)
                anchors = page.locator("a").evaluate_all("""els => els.map(a => ({text:(a.innerText||a.textContent||'').trim().replace(/\\s+/g,' '), href:a.href||''}))""")
                for a in anchors:
                    text = (a.get("text") or "")[:160]
                    href = a.get("href") or ""
                    if not text or not safe_url(href):
                        continue
                    parts = urlsplit(href)
                    rows.append({
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "source": "authenticated_portal_home",
                        "link_text": text,
                        "url": href,
                        "origin": f"{parts.scheme}://{parts.netloc}",
                    })
            except Exception:
                continue
    seen = set()
    unique = []
    for r in rows:
        key = (r["link_text"], r["url"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in unique), encoding="utf-8")
    browser.close()
    print(json.dumps({"links": len(unique), "output": str(OUT)}, ensure_ascii=False))
