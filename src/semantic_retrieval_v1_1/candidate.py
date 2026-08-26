"""RAG_RETRIEVAL_V1_1_CANDIDATE.

This module is deliberately outside the frozen Runtime V1 path.  It reads the
approved V1.1 portability loader, adds query understanding and a transient
BM25/RRF candidate pool, and returns traces.  It never generates an answer or
changes Evidence/Citation policy.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from src.runtime_v1.freeze_loader_v1_1 import build_dense_retriever_v1


VERSION = "RAG_RETRIEVAL_V1_1_CANDIDATE"
_TOKEN = re.compile(r"[\u3400-\u9fff]|[A-Za-z0-9_]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass(frozen=True)
class QueryUnderstandingV1_1:
    original_query: str
    normalized_query: str
    expanded_retrieval_query: str
    route: str
    intent: str | None
    entities: list[str]
    context_used: bool

    @classmethod
    def resolve(cls, query: str, context: list[str] | None = None) -> "QueryUnderstandingV1_1":
        original = query.strip()
        prior = " ".join((context or [])[-2:])
        q = original.replace("爸妈", "父母").replace("咋", "怎么").replace("订", "预约")
        q = q.replace("进学校", "入校").replace("进清华", "入校").replace("几点关", "闭馆时间")
        entities: list[str] = []
        intent = None
        # These are retrieval vocabulary mappings, not answers or facts.
        rules = [
            (("父母", "家长", "爸妈", "家属", "校友"), "VISITOR_ENTRY", ["家长", "父母", "校外访客", "入校", "预约", "参观"]),
            (("教室", "场地", "c楼", "C楼"), "ROOM_BOOKING", ["教室", "场地", "预约", "预订", "使用"]),
            (("食堂", "餐厅", "吃饭"), "DINING", ["食堂", "餐厅", "餐饮"]),
            (("图书馆", "闭馆", "开馆"), "LIBRARY_HOURS", ["图书馆", "开放时间", "闭馆时间"]),
            (("奖学金", "奖助", "奖助学金"), "SCHOLARSHIP", ["本科生", "奖学金", "奖助", "申请", "条件", "时间", "流程"]),
            (("宿舍", "住宿", "公寓"), "ACCOMMODATION", ["宿舍", "住宿", "申请", "管理"]),
            (("校园卡", "一卡通", "学生卡", "办卡"), "CAMPUS_CARD", ["校园卡", "一卡通", "办理", "使用"]),
            (("网络", "wifi", "WiFi", "校园网"), "NETWORK", ["校园网", "网络", "服务"]),
            (("校医院", "医院", "医疗", "看病", "就诊"), "MEDICAL", ["校医院", "医疗", "就诊"]),
            (("班车", "交通", "校车", "校内出行"), "TRANSPORT", ["校园", "交通", "班车"]),
            (("请假", "处分", "学籍", "助学贷款", "学生事务"), "STUDENT_AFFAIRS", ["学生", "事务", "申请", "管理"]),
            (("实验室", "科研", "仪器", "设备"), "RESEARCH_RESOURCES", ["科研", "实验室", "仪器", "设备", "预约"]),
            (("教学楼", "上课楼", "场地"), "TEACHING_SPACE", ["教学楼", "教室", "场地", "使用"]),
        ]
        lower = (original + " " + prior).lower()
        additions: list[str] = []
        for markers, rule_intent, words in rules:
            if any(marker.lower() in lower for marker in markers):
                intent = intent or rule_intent
                additions.extend(words)
        if not intent and re.search(r"\b[abc]楼\b", original, re.I):
            intent, additions = "ROOM_BOOKING", ["教室", "场地", "预约", "预订", "使用"]
        if intent:
            entities = list(dict.fromkeys(additions))
        context_used = bool(prior and intent and not any(word in original for word in ("奖学金", "父母", "爸妈", "家长", "图书馆", "食堂", "教室", "C楼", "c楼")))
        if context_used:
            q = f"{prior} {q}"
        expanded = " ".join(dict.fromkeys(["清华大学", q, *additions]))
        return cls(original, q, expanded, "CAMPUS_RAG" if intent else "GENERAL_OR_CLARIFY", intent, entities, context_used)


class _BM25:
    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.2, b: float = 0.75) -> None:
        self.chunks, self.k1, self.b = chunks, k1, b
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.lengths: list[int] = []
        for index, chunk in enumerate(chunks):
            terms = _tokens(f"{chunk['title']}\n{chunk['text']}")
            self.lengths.append(len(terms))
            for term, count in Counter(terms).items():
                self.postings[term].append((index, count))
        self.avg = sum(self.lengths) / len(self.lengths)

    def search(self, query: str, limit: int) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term, qtf in Counter(_tokens(query)).items():
            posting = self.postings.get(term, [])
            if not posting:
                continue
            idf = math.log(1 + (len(self.chunks) - len(posting) + .5) / (len(posting) + .5))
            for index, tf in posting:
                norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.avg)
                scores[index] += qtf * idf * tf * (self.k1 + 1) / (tf + norm)
        return sorted(scores.items(), key=lambda x: (-x[1], self.chunks[x[0]]["chunk_id"]))[:limit]


class CandidateRetrieverV1_1:
    """Multi-query Dense + BM25 + deterministic RRF, candidate-only."""
    def __init__(self, dense: Any | None = None) -> None:
        self.dense = dense if dense is not None else build_dense_retriever_v1()
        self.chunks = self.dense.chunks
        self.bm25 = _BM25(self.chunks)

    def _row(self, index: int, score: float, rank: int) -> dict[str, Any]:
        chunk = self.chunks[index]
        return {"rank": rank, "chunk_id": chunk["chunk_id"], "source_id": chunk["canonical_source_id"], "title": chunk["title"], "score": round(float(score), 7), "text_snippet": chunk["text"].replace("\n", " ")[:240], "url": chunk.get("url", "")}

    def _dense(self, query: str, limit: int) -> list[tuple[int, float]]:
        scores = np.asarray(self.dense.embeddings @ self.dense._encode_query(query))
        order = sorted(range(len(self.chunks)), key=lambda i: (-float(scores[i]), self.chunks[i]["chunk_id"]))[:limit]
        return [(i, float(scores[i])) for i in order]

    def trace(self, query: str, context: list[str] | None = None, candidate_pool: int = 20) -> dict[str, Any]:
        understanding = QueryUnderstandingV1_1.resolve(query, context)
        base = {"retriever_version": VERSION, "query_understanding": asdict(understanding), "retrieval_invoked": understanding.route == "CAMPUS_RAG"}
        if not base["retrieval_invoked"]:
            return {**base, "dense_top20": [], "bm25_top20": [], "hybrid_top20": [], "final_top5": [], "evidence_status": "NOT_INVOKED", "citation_status": "NOT_INVOKED"}
        query_variants = list(dict.fromkeys([understanding.original_query, understanding.normalized_query, understanding.expanded_retrieval_query]))
        dense_lists = [("dense", value, self._dense(value, candidate_pool)) for value in query_variants]
        bm25_lists = [("bm25", value, self.bm25.search(value, candidate_pool)) for value in query_variants]
        fused: dict[int, float] = defaultdict(float)
        for _method, _variant, rows in [*dense_lists, *bm25_lists]:
            for rank, (index, _score) in enumerate(rows, 1):
                fused[index] += 1.0 / (60 + rank)
        hybrid = sorted(fused.items(), key=lambda x: (-x[1], self.chunks[x[0]]["chunk_id"]))[:candidate_pool]
        first_dense = dense_lists[0][2]
        first_bm25 = bm25_lists[0][2]
        return {**base, "query_variants": query_variants,
                "dense_top20": [self._row(i, s, r) for r, (i, s) in enumerate(first_dense, 1)],
                "bm25_top20": [self._row(i, s, r) for r, (i, s) in enumerate(first_bm25, 1)],
                "hybrid_top20": [self._row(i, s, r) for r, (i, s) in enumerate(hybrid, 1)],
                "final_top5": [self._row(i, s, r) for r, (i, s) in enumerate(hybrid[:5], 1)],
                "evidence_status": "NOT_EVALUATED_CANDIDATE_NOT_INTEGRATED", "citation_status": "NOT_EVALUATED_CANDIDATE_NOT_INTEGRATED"}
