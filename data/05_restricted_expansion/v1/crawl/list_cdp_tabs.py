from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    for context in browser.contexts:
        for page in context.pages:
            parts = urlsplit(page.url)
            origin = f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else page.url
            try:
                title = page.title()
            except Exception:
                title = ""
            print(f"{origin}\t{title[:120]}")
    browser.close()
