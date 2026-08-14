from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(r"D:\python_projects\tsinghua_ai")
STATE = ROOT / "data_first" / "data" / "auth" / "storage_state.json"
OUT = ROOT / "data_second" / "restricted_expansion_v1" / "crawl" / "auth_status.json"
PORTAL = "https://info.tsinghua.edu.cn/"


def classify(url: str, title: str) -> tuple[str, str]:
    text = f"{url} {title}".lower()
    login_markers = ["login", "auth", "id.tsinghua.edu.cn", "统一身份认证", "登录"]
    if any(x in text for x in login_markers):
        return "NEED_MANUAL_LOGIN", "existing_storage_state_redirected_to_login"
    if "info.tsinghua.edu.cn" in url.lower():
        return "AUTHENTICATED", "existing_storage_state_reached_portal"
    return "NEED_MANUAL_LOGIN", "existing_storage_state_did_not_reach_authenticated_portal"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "portal": PORTAL,
        "auth_method_type": "existing_sso_session",
        "storage_state_present": STATE.exists(),
        "credential_material_copied": False,
        "auth_status": "NEED_MANUAL_LOGIN",
        "reason": "storage_state_missing",
    }
    if not STATE.exists():
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"auth_status": result["auth_status"], "reason": result["reason"]}))
        return

    stage = "startup"
    try:
        with sync_playwright() as p:
            stage = "browser_launch"
            browser = p.chromium.launch(channel="msedge", headless=True)
            stage = "context_with_existing_storage"
            context = browser.new_context(storage_state=str(STATE), ignore_https_errors=True)
            page = context.new_page()
            stage = "portal_navigation"
            response = page.goto(PORTAL, wait_until="commit", timeout=45000)
            page.wait_for_timeout(2500)
            stage = "portal_classification"
            status, reason = classify(page.url, page.title())
            result.update({
                "auth_status": status,
                "reason": reason,
                "http_status": response.status if response else None,
                "final_origin": "https://" + page.url.split("/")[2] if "://" in page.url else "",
            })
            context.close()
            browser.close()
    except Exception as exc:
        result.update({
            "auth_status": "NEED_MANUAL_LOGIN",
            "reason": "auth_check_failed_without_credential_export",
            "error_type": type(exc).__name__,
            "failure_stage": stage,
        })
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result.get(k) for k in ["auth_status", "reason", "http_status", "final_origin", "error_type", "failure_stage"] if k in result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
