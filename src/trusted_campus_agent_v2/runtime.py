from __future__ import annotations

import time
import uuid
from datetime import date
from typing import Any

from .answer_planner import GroundedAnswerPlannerV2
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

    def ask(self, query: str, case_id: str | None = None, as_of: date | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        case_id = case_id or f"LOCAL-{uuid.uuid4().hex[:12]}"
        as_of = as_of or date.today()
        plan = self.planner.plan(query)
        retrieval = self.retriever.retrieve(plan, as_of=as_of)
        evidence = self.gate.evaluate(plan, retrieval, as_of=as_of)
        response = self.composer.compose(plan, evidence)
        return {
            "agent_version": self.VERSION, "case_id": case_id, "query": query,
            "as_of": as_of.isoformat(), "path": plan.path, "query_plan": plan.to_dict(),
            "evidence_status": evidence.status, "evidence": evidence.to_dict(),
            "response": response, "retrieval": retrieval,
            "total_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "candidate_only": True, "published": False,
        }

    def handle(
        self,
        query: str,
        *,
        uploaded_files: list[str] | None = None,
        file_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Route ordinary questions to RAG and file intents to real file tools."""
        from .file_tools import CampusFileService, CampusToolRouter

        uploads = uploaded_files or []
        route = CampusToolRouter().route(query, uploads)
        if route.route == "rag_qa":
            result = self.ask(query)
            result["tool_route"] = route.to_dict()
            return result
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
