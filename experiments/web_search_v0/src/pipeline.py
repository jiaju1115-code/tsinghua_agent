from __future__ import annotations
import json, time
from pathlib import Path
from .cache import JsonCache
from .config import ROOT, load_settings
from .evidence_span import extract_spans
from .query_rewriter import direct_answer_search_guard, rewrite_academic_query
from .ranking import rank_sources
from .router import SearchMode, route_query
from .source_quality import assess_source
from .tavily_client import TavilyWebClient

class WebSearchPipeline:
    def __init__(self, root: Path = ROOT):
        self.root=root; self.client=TavilyWebClient(load_settings()); self.cache=JsonCache(root / "cache")
    def retrieve(self, query: str) -> dict:
        began=time.perf_counter(); request_count_before=self.client.request_count; route=route_query(query)
        output={"query":query,"mode":route.mode.value,"router_reason":route.reason,"errors":[],"sources":[],"evidence_spans":[],"request_count":0,"search_latency_seconds":0.0,"extract_latency_seconds":0.0,"search_cache_hits":0}
        if route.mode in {SearchMode.NO_WEB_NEEDED, SearchMode.UNCERTAIN}:
            output["status"]="SKIPPED"; return output
        queries=[query]; rewrite=None
        if route.mode == SearchMode.ACADEMIC_RETRIEVAL:
            rewrite=rewrite_academic_query(query); queries=rewrite.knowledge_queries; output["academic_rewrite"]=rewrite.__dict__
        for search_query in queries[:2]:
            include=["tsinghua.edu.cn"] if route.mode == SearchMode.CAMPUS_PUBLIC else None
            key={"kind":"search","query":search_query,"mode":route.mode.value,"include_domains":include,"max_results":5}
            cached=self.cache.get(key)
            try:
                if cached:
                    raw=cached["records"]; output["search_cache_hits"] += 1
                else:
                    search_started=time.perf_counter()
                    raw=self.client.search_web(search_query,route.mode.value,5,include)
                    output["search_latency_seconds"] += time.perf_counter()-search_started
                    raw=self.cache.put(key,{"records":raw})["records"]
            except Exception as exc:
                output["errors"].append(self._safe_error(exc)); continue
            output["sources"].extend(raw)
        output["sources"]=rank_sources(output["sources"],route.mode.value,query)
        # Campus fallback is only used when official results are insufficient.
        if route.mode == SearchMode.CAMPUS_PUBLIC and len(output["sources"]) < 2:
            try:
                search_started=time.perf_counter()
                output["sources"].extend(self.client.search_web(query,route.mode.value,5))
                output["search_latency_seconds"] += time.perf_counter()-search_started
            except Exception as exc: output["errors"].append(self._safe_error(exc))
            output["sources"]=rank_sources(output["sources"],route.mode.value,query)
        selected=output["sources"][:3]
        try:
            extract_started=time.perf_counter()
            pages=self.client.extract([source["url"] for source in selected])
            output["extract_latency_seconds"] = time.perf_counter()-extract_started
        except Exception as exc: pages={}; output["errors"].append(self._safe_error(exc))
        for source in selected:
            content=pages.get(source["url"], "")
            assessment=assess_source(source["url"],content)
            source.update({"content":content,"source_domain":source["url"].split("/")[2] if "/" in source["url"] else "","source_title":source["title"],"source_url":source["url"],"source_authority_level":assessment.authority,"content_length":len(content),"extraction_status":assessment.verdict,"quality_reasons":assessment.reasons})
            if rewrite and direct_answer_search_guard(query,source["title"],content): source["possible_direct_answer_flag"]="POSSIBLE_DIRECT_ANSWER_SOURCE"
            if assessment.verdict != "REJECT" and not source.get("possible_direct_answer_flag"):
                output["evidence_spans"].extend(extract_spans(content,query=query,mode=route.mode.value,url=source["url"],title=source["title"],authority=assessment.authority))
        output.update({"status":"SUCCESS" if output["evidence_spans"] else "NO_USABLE_EVIDENCE","request_count":self.client.request_count-request_count_before,"search_latency_seconds":round(output["search_latency_seconds"],3),"extract_latency_seconds":round(output["extract_latency_seconds"],3),"total_latency_seconds":round(time.perf_counter()-began,3)})
        return output

    def _safe_error(self, exc: Exception) -> str:
        """Keep logs actionable while never persisting a configured API secret."""
        message = str(exc)
        key = self.client.settings.api_key
        if key:
            message = message.replace(key, key[:7] + "****************")
        return message[:500]

def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False)+"\n")
