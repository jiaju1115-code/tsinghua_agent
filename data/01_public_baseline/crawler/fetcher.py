from __future__ import annotations

import email.utils
import random
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests

@dataclass
class FetchResult:
    response: requests.Response | None
    error: str = ""
    retries: int = 0

class Fetcher:
    def __init__(self, config):
        self.config, self.local = config, threading.local()
        self.domain_locks, self.last_request, self.robots = {}, {}, {}
        self.guard = threading.Lock()

    def session(self):
        if not hasattr(self.local, "session"):
            self.local.session = requests.Session(); self.local.session.headers.update({"User-Agent": self.config["user_agent"], "Accept": "text/html,application/xhtml+xml"})
        return self.local.session

    def _lock(self, host):
        with self.guard: return self.domain_locks.setdefault(host, threading.Lock())

    def allowed_by_robots(self, url):
        p = urlsplit(url); origin = f"{p.scheme}://{p.netloc}"
        with self.guard: rp = self.robots.get(origin)
        if rp is None:
            rp = RobotFileParser(); rp.set_url(origin + "/robots.txt")
            try:
                r = self.session().get(rp.url, timeout=self.config["timeout_seconds"])
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException: rp.parse([])
            with self.guard: self.robots[origin] = rp
        return rp.can_fetch(self.config["user_agent"], url)

    def fetch(self, url):
        host = urlsplit(url).netloc.lower(); delay = float(self.config["request_delay_seconds"])
        for attempt in range(int(self.config["max_retries"]) + 1):
            try:
                with self._lock(host):
                    wait = delay - (time.monotonic() - self.last_request.get(host, 0))
                    if wait > 0: time.sleep(wait)
                    response = self.session().get(url, timeout=self.config["timeout_seconds"], allow_redirects=True, stream=True)
                    self.last_request[host] = time.monotonic()
                if response.status_code == 429 or 500 <= response.status_code <= 503:
                    if attempt < self.config["max_retries"]:
                        retry_after = response.headers.get("Retry-After", "")
                        try: pause = min(30, float(retry_after))
                        except ValueError: pause = min(30, delay * (2 ** (attempt + 1)) + random.random())
                        time.sleep(pause); continue
                content = response.raw.read(int(self.config["max_response_bytes"]) + 1, decode_content=True)
                if len(content) > int(self.config["max_response_bytes"]): return FetchResult(None, "response_too_large", attempt)
                response._content = content; response._content_consumed = True
                return FetchResult(response, retries=attempt)
            except requests.RequestException as exc:
                if attempt >= self.config["max_retries"]: return FetchResult(None, f"{type(exc).__name__}: {exc}", attempt)
                time.sleep(min(30, delay * (2 ** (attempt + 1))))
        return FetchResult(None, "unknown_error", self.config["max_retries"])

