from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(r"D:\python_projects\tsinghua_ai")
STATE = ROOT / "data_first" / "data" / "auth" / "storage_state.json"
OUT = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "auth_status.json"
PORTAL = "https://info.tsinghua.edu.cn/"
LOGIN_FALLBACK = "https://id.tsinghua.edu.cn/"


def is_authenticated(url: str, title: str) -> bool:
    text = f"{url} {title}".lower()
    login_markers = ["id.tsinghua.edu.cn", "/login", "统一身份认证", "用户登录"]
    return "info.tsinghua.edu.cn" in url.lower() and not any(x in text for x in login_markers)


def write_status(status: str, reason: str, **extra):
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "portal": PORTAL,
        "auth_method_type": "authenticated_browser",
        "auth_status": status,
        "reason": reason,
        "credential_material_copied_to_reports": False,
        **extra,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False)
        kwargs = {"ignore_https_errors": True}
        if STATE.exists():
            kwargs["storage_state"] = str(STATE)
        context = browser.new_context(**kwargs)
        page = context.new_page()
        try:
            page.goto(PORTAL, wait_until="commit", timeout=45000)
        except Exception:
            # Keep the visible browser alive so the user can retry from the address bar.
            pass
        print("PORTAL_WINDOW_OPENED", flush=True)
        deadline = time.time() + 1800
        while time.time() < deadline:
            for current_page in list(context.pages):
                try:
                    url, title = current_page.url, current_page.title()
                    if is_authenticated(url, title):
                        # Update only the existing project auth state; never print its contents.
                        context.storage_state(path=str(STATE))
                        write_status("AUTHENTICATED", "manual_login_verified", final_origin="https://info.tsinghua.edu.cn")
                        print("AUTHENTICATED", flush=True)
                        time.sleep(2)
                        context.close()
                        browser.close()
                        return
                except Exception:
                    pass
            time.sleep(2)
        write_status("NEED_MANUAL_LOGIN", "manual_login_timeout")
        print("NEED_MANUAL_LOGIN_TIMEOUT", flush=True)
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
