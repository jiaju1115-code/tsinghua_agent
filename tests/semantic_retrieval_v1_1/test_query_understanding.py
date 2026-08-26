from src.semantic_retrieval_v1_1 import QueryUnderstandingV1_1


def test_obvious_campus_paraphrases_route_to_rag_without_answers():
    for query in ["我的爸妈怎么预约入校", "C楼怎么订", "图书馆几点关", "奖学金咋搞", "校内出行"]:
        result = QueryUnderstandingV1_1.resolve(query)
        assert result.route == "CAMPUS_RAG"
        assert result.original_query == query
        assert "答案" not in result.expanded_retrieval_query


def test_short_follow_up_uses_explicit_session_context_only():
    result = QueryUnderstandingV1_1.resolve("本科生的", ["奖学金怎么申请？"])
    assert result.context_used is True
    assert "奖学金" in result.expanded_retrieval_query
