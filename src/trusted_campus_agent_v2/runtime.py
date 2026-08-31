from __future__ import annotations

import copy
import json
import time
import uuid
from collections import OrderedDict
from dataclasses import replace
from datetime import date
from typing import Any

from .answer_planner import GroundedAnswerPlannerV2
from .clarification import ClarificationPolicy
from .evidence_gate import EvidenceGateV2
from .query_planner import CampusQueryPlanner
from .retrieval import TrustedHybridRetrieverV2, build_public_retriever_v2, build_shadow_retriever_v2


class TrustedCampusAgentV2:
    VERSION = "TRUSTED_CAMPUS_AGENT_V2_CANDIDATE"

    def __init__(
        self,
        planner: Any | None = None,
        retriever: Any | None = None,
        gate: Any | None = None,
        composer: Any | None = None,
        use_shadow: bool = False,
        use_public_v2: bool = False,
        file_planner: Any | None = None,
        local_model: bool = False,
        cache_ttl_seconds: float = 300.0,
    ) -> None:
        self.planner = planner or CampusQueryPlanner()
        self.retriever = retriever or (
            build_shadow_retriever_v2() if use_shadow else
            build_public_retriever_v2() if use_public_v2 else
            TrustedHybridRetrieverV2()
        )
        self.gate = gate or EvidenceGateV2()
        if local_model and (composer is None or file_planner is None):
            from .local_model import LocalQwenFilePlanner, LocalQwenGroundedComposer

            composer = composer or LocalQwenGroundedComposer()
            file_planner = file_planner or LocalQwenFilePlanner()
        self.composer = composer or GroundedAnswerPlannerV2()
        self.file_planner = file_planner
        self.clarification = ClarificationPolicy()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()

    def ask(
        self,
        query: str,
        case_id: str | None = None,
        as_of: date | None = None,
        context: dict[str, Any] | None = None,
        path_override: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        case_id = case_id or f"LOCAL-{uuid.uuid4().hex[:12]}"
        as_of = as_of or date.today()
        context = context or {}
        context_text = "、".join(f"{key}={value}" for key, value in sorted(context.items()) if value)
        effective_query = f"{query}（已知用户信息：{context_text}）" if context_text else query
        normalized_override = path_override.upper() if path_override else None
        cache_key = json.dumps([effective_query, as_of.isoformat(), normalized_override], ensure_ascii=False)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] <= self.cache_ttl_seconds:
            result = copy.deepcopy(cached[1])
            result.update({"case_id": case_id, "query": query, "cache_hit": True})
            result["total_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
            return result
        stage_started = time.perf_counter()
        plan = self.planner.plan(effective_query, path_override=normalized_override)
        plan = replace(plan, original_query=query)
        planning_ms = (time.perf_counter() - stage_started) * 1000
        stage_started = time.perf_counter()
        retrieval = self.retriever.retrieve(plan, as_of=as_of)
        retrieval_ms = (time.perf_counter() - stage_started) * 1000
        stage_started = time.perf_counter()
        evidence = self.gate.evaluate(plan, retrieval, as_of=as_of)
        gate_ms = (time.perf_counter() - stage_started) * 1000
        stage_started = time.perf_counter()
        response = self.composer.compose(plan, evidence)
        compose_ms = (time.perf_counter() - stage_started) * 1000
        clarification = self.clarification.assess(
            query, status=evidence.status, topics=list(plan.metadata_filters.get("topics", [])),
            context=context, citations=response.get("citations", []),
        )
        response.update({
            "needs_clarification": clarification.needs_clarification,
            "clarification_questions": list(clarification.questions),
            "missing_slots": list(clarification.missing_slots),
            "search_guidance": list(clarification.search_guidance),
        })
        result = {
            "agent_version": self.VERSION, "case_id": case_id, "query": query,
            "as_of": as_of.isoformat(), "path": plan.path, "query_plan": plan.to_dict(),
            "path_selection": {"requested": normalized_override or "AUTO", "effective": plan.path},
            "evidence_status": evidence.status, "evidence": evidence.to_dict(),
            "response": response, "retrieval": retrieval,
            "total_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "stage_latency_ms": {"planning": round(planning_ms, 3), "retrieval": round(retrieval_ms, 3), "evidence_gate": round(gate_ms, 3), "compose": round(compose_ms, 3)},
            "cache_hit": False, "candidate_only": True, "published": False,
        }
        self._cache[cache_key] = (time.time(), copy.deepcopy(result))
        self._cache.move_to_end(cache_key)
        while len(self._cache) > 128:
            self._cache.popitem(last=False)
        return result

    def handle(
        self,
        query: str,
        *,
        uploaded_files: list[str] | None = None,
        file_options: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        path_override: str | None = None,
    ) -> dict[str, Any]:
        """Route ordinary questions to RAG and file intents to real file tools."""
        from .file_tools import CampusFileService, CampusToolRouter

        uploads = uploaded_files or []
        if uploads and any(marker in query for marker in ("检查材料", "材料齐全", "缺少什么", "缺什么材料", "完整性")):
            from .materials import MaterialInspector
            return MaterialInspector(self).inspect(query, uploads, context=context)
        route = CampusToolRouter().route(query, uploads)
        if route.route == "rag_qa":
            result = self.ask(query, context=context, path_override=path_override)
            result["tool_route"] = route.to_dict()
            return result
        needs_official_evidence = any(marker in query for marker in ("根据学校", "学校最新要求", "官方要求", "最新规定", "按学校要求"))
        if needs_official_evidence:
            preliminary = self.ask(query, context=context, path_override=path_override)
            if preliminary.get("response", {}).get("needs_clarification"):
                preliminary["tool_route"] = route.to_dict()
                preliminary["file_generation_deferred"] = True
                return preliminary
        options = dict(file_options or {})
        if uploads and "input_path" not in options:
            options["input_path"] = uploads[0]
        service = CampusFileService(rag_agent=self)
        if self.file_planner is not None:
            return service.execute_with_llm(
                query,
                self.file_planner,
                uploaded_files=uploads,
                **options,
            )
        return service.execute(query, route=route, **options)

    @staticmethod
    def tool_schemas() -> list[dict[str, Any]]:
        from .file_tools import CampusToolRouter

        return CampusToolRouter.tool_schemas()

    def warmup_full_path(self) -> dict[str, Any]:
        """Preload and exercise the frozen encoder before accepting user traffic."""
        started = time.perf_counter()
        dense = self.retriever._get_dense()
        self.retriever._encode_subqueries(dense, ("清华大学校园事务",))
        return {
            "status": "READY", "component": "dense_retriever",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }
