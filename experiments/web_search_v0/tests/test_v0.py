from src.query_rewriter import direct_answer_search_guard, rewrite_academic_query
from src.router import SearchMode, route_query
from src.source_quality import assess_source, authority_for_url

def test_router_modes():
    assert route_query("清华大学图书馆开放时间").mode == SearchMode.CAMPUS_PUBLIC
    assert route_query("泊松分布的期望和方差").mode == SearchMode.ACADEMIC_RETRIEVAL
    assert route_query("2026年人工智能最新新闻").mode == SearchMode.GENERAL_WEB
    assert route_query("1+1等于多少").mode == SearchMode.NO_WEB_NEEDED

def test_academic_rewrite_avoids_full_problem():
    problem="设X服从参数5的泊松分布，求E(X²)。"
    rewrite=rewrite_academic_query(problem)
    assert rewrite.subject == "概率论"
    assert all(problem not in query for query in rewrite.knowledge_queries)

def test_direct_answer_guard_and_quality():
    problem="设X服从参数5的泊松分布，求E(X²)。"
    assert direct_answer_search_guard(problem, problem + "答案", problem)
    assert authority_for_url("https://www.tsinghua.edu.cn/x") == "OFFICIAL_THSINGHUA"
    assert assess_source("https://example.org", "").verdict == "REJECT"
