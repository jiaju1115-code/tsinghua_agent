"""User-authenticated portal crawl with the repository's privacy deny rules."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "01_public_baseline"
RUN_ROOT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2" / "portal_crawl_v1"
if str(BASELINE) not in sys.path:
    sys.path.insert(0, str(BASELINE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from crawler.runner import now_iso
from playwright.sync_api import Error as PlaywrightError
from portal.runner import PortalCrawler


class ResilientPortalCrawler(PortalCrawler):
    """Retry transient SPA navigation races without weakening privacy gates."""

    def _process(self, page, row):
        host = (urlsplit(row["url"]).hostname or "").lower()
        if re.match(r"^\d", host):
            stamp = now_iso()
            self.state.finish(row["url"], "skipped", stamp, "opaque_numeric_subdomain")
            self.log.write("portal_skipped.csv", {
                "url": row["url"], "title": row.get("anchor_text", ""),
                "reason": "opaque_numeric_subdomain", "timestamp": stamp,
            })
            self.stats.skipped += 1
            return None
        for attempt in range(3):
            try:
                return super()._process(page, row)
            except PlaywrightError as exc:
                if "navigat" not in str(exc).lower() or attempt == 2:
                    if attempt == 2 and "navigat" in str(exc).lower():
                        stamp = now_iso()
                        self.state.finish(row["url"], "failed", stamp, "unstable_navigation")
                        self.log.write("portal_failed.csv", {
                            "url": row["url"], "error_type": "unstable_navigation",
                            "error_message": str(exc), "timestamp": stamp,
                        })
                        self.stats.failed += 1
                        return None
                    raise
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=10_000)
                    page.wait_for_timeout(1200 * (attempt + 1))
                except PlaywrightError:
                    time.sleep(attempt + 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect non-personal campus-affairs pages after the user logs in manually.")
    parser.add_argument("--max-pages", type=int, default=300)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--login-timeout", type=int, default=900)
    args = parser.parse_args()
    if args.max_pages < 1 or args.max_pages > 1000:
        raise SystemExit("--max-pages must be between 1 and 1000")
    config = {
        "portal_url": "https://info.tsinghua.edu.cn/",
        "allowed_domain": "tsinghua.edu.cn",
        "portal_test_mode": False,
        "portal_test_max_pages": args.max_pages,
        "portal_max_pages": args.max_pages,
        "max_portal_depth": args.max_depth,
        "portal_navigation_timeout_ms": 30_000,
        "portal_login_timeout_seconds": args.login_timeout,
        "portal_headless": False,
        "portal_cdp_ports": [9222, 9223],
        "tracking_parameters": ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "spm", "from"],
        "min_content_chars": 120,
        "possible_duplicate_threshold": 0.92,
    }
    for relative in ("data", "logs", "knowledge"):
        (RUN_ROOT / relative).mkdir(parents=True, exist_ok=True)
    stats = ResilientPortalCrawler(config, RUN_ROOT).run()
    summary = {
        "version": "TRUSTED_CAMPUS_V2_PORTAL_CRAWL_V1",
        "candidate_only": True,
        "access_level": "campus_authenticated",
        "personal_data_collection": False,
        "finished_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "stats": asdict(stats),
    }
    (RUN_ROOT / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
