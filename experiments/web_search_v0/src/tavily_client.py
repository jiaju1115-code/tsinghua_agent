from __future__ import annotations
from datetime import datetime, timezone
from .config import Settings
from .source_quality import authority_for_url

class TavilyUnavailableError(RuntimeError): pass

class TavilyWebClient:
    def __init__(self, settings: Settings): self.settings = settings; self.request_count = 0
    def _client(self):
        if not self.settings.api_key: raise TavilyUnavailableError("TAVILY_API_KEY_NOT_CONFIGURED")
        try:
            from tavily import TavilyClient
        except ImportError as exc: raise TavilyUnavailableError("TAVILY_PYTHON_NOT_INSTALLED") from exc
        return TavilyClient(api_key=self.settings.api_key)
    def search_web(self, query: str, mode: str, max_results: int = 5, include_domains=None, exclude_domains=None) -> list[dict]:
        result = self._client().search(query=query, max_results=max_results, include_domains=include_domains or None, exclude_domains=exclude_domains or None, search_depth="basic")
        self.request_count += 1; timestamp = datetime.now(timezone.utc).isoformat()
        return [{"search_query": query, "search_mode": mode, "search_timestamp": timestamp, "result_rank": i+1, "title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", ""), "score": x.get("score"), "raw_source_metadata": x, "source_authority_level": authority_for_url(x.get("url", ""))} for i, x in enumerate(result.get("results", []))]
    def extract(self, urls: list[str]) -> dict[str, str]:
        if not urls: return {}
        result = self._client().extract(urls=urls)
        self.request_count += 1
        return {x.get("url", ""): x.get("raw_content", "") for x in result.get("results", [])}
