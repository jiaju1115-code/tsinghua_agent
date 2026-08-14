from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(r"D:\python_projects\tsinghua_ai")
STATE = ROOT / "data_first" / "data" / "auth" / "storage_state.json"
OUT = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "auth_status.json"


def main():
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "auth_method_type": "authenticated_browser",
        "credential_material_copied_to_reports": False,
        "auth_status": "NEED_MANUAL_LOGIN",
        "reason": "authenticated_portal_page_not_found",
    }
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        found = False
        for context in browser.contexts:
            for page in context.pages:
                url = page.url.lower()
                title = page.title().lower()
                is_direct_portal = "info.tsinghua.edu.cn" in url
                is_webvpn_portal = "webvpn.tsinghua.edu.cn" in url and "清华大学信息门户" in title
                if (is_direct_portal or is_webvpn_portal) and "login" not in url and "统一身份认证" not in title:
                    context.storage_state(path=str(STATE))
                    result.update({
                        "auth_status": "AUTHENTICATED",
                        "reason": "authenticated_portal_page_verified",
                        "final_origin": "https://webvpn.tsinghua.edu.cn" if is_webvpn_portal else "https://info.tsinghua.edu.cn",
                    })
                    found = True
                    break
            if found:
                break
        browser.close()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"auth_status": result["auth_status"], "reason": result["reason"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
