from __future__ import annotations

from datetime import date

import numpy as np

from src.trusted_campus_agent_v2.answer_planner import GroundedAnswerPlannerV2
from src.trusted_campus_agent_v2.evidence_gate import EvidenceGateV2, EvidenceResult
from src.trusted_campus_agent_v2.query_planner import CampusQueryPlanner, QueryPlan
from src.trusted_campus_agent_v2.retrieval import TrustedHybridRetrieverV2
from src.trusted_campus_agent_v2.metadata import infer_content_type, infer_topics, load_v1_catalog, policy_key


def plan(path: str = "FAST", subqueries: tuple[str, ...] = ("宿舍申请",), action: bool = False) -> QueryPlan:
    return QueryPlan("宿舍申请", "宿舍申请", subqueries, path, (), {"topics": ["校园生活"], "current_only": False}, (), action)


def hit(source: str = "S1", score: float = 0.9, subqueries: list[int] | None = None, text: str = "申请人应当提交申请表。请于9月1日17:00前登录https://example.edu.cn办理。", policy: str = "p") -> dict:
    return {
        "source_id": source, "chunk_id": f"{source}-C1", "title": "宿舍申请办法", "url": f"https://{source}.tsinghua.edu.cn",
        "text": text, "score": score, "subquery_indices": subqueries if subqueries is not None else [0],
        "metadata": {"authority_level": "official", "policy_key": policy}, "temporal_status": "active",
    }


def test_query_planner_uses_alias_and_fast_full_paths() -> None:
    planner = CampusQueryPlanner()
    fast = planner.plan("GPA是什么意思？")
    assert fast.path == "FAST"
    assert "平均学分绩" in fast.canonical_terms
    full = planner.plan("本科生申请转系需要什么条件、材料和步骤，截止时间是什么？")
    assert full.path == "FULL"
    assert full.wants_action_plan
    assert len(full.subqueries) >= 2


def test_fast_path_never_initializes_dense() -> None:
    chunks = [{"chunk_id": "C1", "canonical_source_id": "S1", "title": "宿舍申请", "url": "https://x.tsinghua.edu.cn", "category": "住宿服务", "text": "宿舍调整申请办理流程"}]
    metadata = {"S1": {"admission_status": "serving", "authority_level": "official", "topics": ["校园生活"], "audience": ["全校学生"], "effective_date": None, "expiry_date": None}}
    retriever = TrustedHybridRetrieverV2(chunks=chunks, metadata=metadata, dense_factory=lambda: (_ for _ in ()).throw(AssertionError("dense loaded")))
    result = retriever.retrieve(plan())
    assert not result["dense_enabled"]
    assert result["results"][0]["source_id"] == "S1"


class DenseStub:
    embeddings = np.asarray([[1.0, 0.0]], dtype=np.float32)

    @staticmethod
    def _encode_query(query: str) -> np.ndarray:
        return np.asarray([1.0, 0.0], dtype=np.float32)


def test_full_path_uses_dense_and_bm25() -> None:
    chunks = [{"chunk_id": "C1", "canonical_source_id": "S1", "title": "转专业办法", "url": "https://x.tsinghua.edu.cn", "category": "教务与学籍", "text": "转专业申请条件和办理步骤"}]
    metadata = {"S1": {"admission_status": "serving", "authority_level": "official", "topics": ["教务"], "audience": ["本科生"], "effective_date": "2026-01-01", "expiry_date": None}}
    query_plan = QueryPlan("如何转系", "如何转专业", ("转专业条件", "转专业步骤"), "FULL", ("actionable_procedure",), {"topics": ["教务"]}, ("转专业",), True)
    result = TrustedHybridRetrieverV2(chunks=chunks, metadata=metadata, dense_factory=DenseStub).retrieve(query_plan, as_of=date(2026, 8, 30))
    assert result["dense_enabled"]
    assert result["results"][0]["retrieval_methods"] == ["bm25", "dense"]


def test_evidence_gate_has_all_four_states() -> None:
    gate = EvidenceGateV2(min_score=0.4)
    assert gate.evaluate(plan(), {"results": [hit()]}).status == "SUPPORTED"
    two = plan("FULL", ("条件", "材料"))
    assert gate.evaluate(two, {"results": [hit(subqueries=[0])]}).status == "PARTIAL"
    assert gate.evaluate(plan(), {"results": []}).status == "NOT_SUPPORTED"
    conflict_rows = [
        hit("S1", text="截止时间为9月1日17:00。", policy="same"),
        hit("S2", text="截止时间为9月3日17:00。", policy="same"),
    ]
    assert gate.evaluate(plan(), {"results": conflict_rows}).status == "CONFLICT"


def test_action_plan_is_evidence_bound() -> None:
    evidence = EvidenceResult("SUPPORTED", (0,), (), (hit(),), (), (), ("ALL_SUBQUERIES_AUTHORITATIVELY_SUPPORTED",))
    response = GroundedAnswerPlannerV2().compose(plan(action=True), evidence)
    assert response["action_plan"]["materials"]
    assert response["action_plan"]["deadlines"]
    assert response["citations"][0]["source_id"] == "S1"


def test_declared_deadline_without_deadline_evidence_is_partial() -> None:
    deadline_plan = plan("FULL", ("宿舍申请的截止时间",))
    no_deadline = hit(text="申请人应当在线提交申请表。")
    result = EvidenceGateV2(min_score=0.4).evaluate(deadline_plan, {"results": [no_deadline]})
    assert result.status == "PARTIAL"
    assert result.unsupported_subqueries == (0,)


def test_expired_evidence_is_history_not_current_support() -> None:
    expired = hit()
    expired["temporal_status"] = "expired"
    result = EvidenceGateV2(min_score=0.4).evaluate(plan(), {"results": [expired]})
    assert result.status == "NOT_SUPPORTED"
    assert result.historical_versions[0]["source_id"] == "S1"


def test_newer_dated_policy_supersedes_older_active_source() -> None:
    old = hit("OLD", text="申请截止时间为9月1日17:00。", policy="same")
    old["metadata"]["effective_date"] = "2023-01-01"
    new = hit("NEW", text="申请截止时间为9月3日17:00。", policy="same")
    new["metadata"]["effective_date"] = "2025-01-01"
    result = EvidenceGateV2(min_score=0.4).evaluate(plan(), {"results": [old, new]})
    assert result.status == "SUPPORTED"
    assert {row["source_id"] for row in result.supporting_hits} == {"NEW"}
    assert result.historical_versions[0]["source_id"] == "OLD"


def test_restricted_source_is_not_retrieved_without_authorization() -> None:
    chunks = [{"chunk_id": "C1", "canonical_source_id": "S1", "title": "内部办理", "url": "https://info.tsinghua.edu.cn/private", "category": "学生事务", "text": "内部办理申请流程"}]
    metadata = {"S1": {"admission_status": "serving", "access_level": "restricted", "authority_level": "official_internal", "topics": ["学生事务"], "audience": ["全校学生"], "effective_date": None, "expiry_date": None}}
    restricted_plan = QueryPlan("内部办理", "内部办理", ("内部办理",), "FAST", (), {"topics": ["学生事务"]}, (), True)
    result = TrustedHybridRetrieverV2(chunks=chunks, metadata=metadata).retrieve(restricted_plan)
    assert result["results"] == []


def test_crawl_metadata_classifies_all_affairs_signals_without_default_pollution() -> None:
    topics = infer_topics("校园相关", "2026届毕业生就业手续办理通知", "三方协议、档案和户口迁移办理流程")
    assert "就业" in topics
    assert "毕业" in topics
    assert infer_content_type("交换生申请指南", "申请条件、材料、步骤和截止时间") == "procedure_guide"


def test_crawl_metadata_recognizes_research_policy() -> None:
    topics = infer_topics("规章制度", "清华大学实验室安全准入实施细则", "科研实验人员须完成安全考试")
    assert "科研实践" in topics
    assert infer_content_type("清华大学实验室安全准入实施细则", "第一条 本细则适用于所有人员") == "policy"


def test_policy_key_groups_document_number_and_site_suffix_versions() -> None:
    latest = "《清华大学实验室安全准入实施细则》_清实发〔2025〕1号"
    historical = "清华大学实验室安全准入实施细则-清华大学环境科学与工程实验实践教学中心"
    assert policy_key(latest) == policy_key(historical)


def test_v1_catalog_can_be_derived_without_v2_candidate_assets() -> None:
    catalog = load_v1_catalog()
    assert catalog
    assert all(item.get("source_version") == "KNOWLEDGE_BASE_V1" for item in catalog.values())
    assert any(item.get("access_level") == "public" for item in catalog.values())
