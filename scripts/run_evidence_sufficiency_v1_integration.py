from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence_sufficiency_v1 import evaluate_evidence
from src.evidence_sufficiency_v1.schema import OUTPUT_FIELDS
from src.retrieval_v1 import DenseRetrieverV1


QUERIES = (
    ("INT-001", "\u6e05\u534e\u5927\u5b66\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f"),
    ("INT-002", "\u6e05\u534e\u5927\u5b66\u672c\u79d1\u751f\u5956\u5b66\u91d1\u7533\u8bf7\u6761\u4ef6\u548c\u622a\u6b62\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f"),
    ("INT-003", "\u6e05\u534e\u5927\u5b66\u6821\u533b\u9662\u7684\u5c31\u8bca\u6d41\u7a0b\u5982\u4f55\uff1f"),
)


def stable_evidence(result: dict) -> dict:
    value = copy.deepcopy(result)
    value.pop("latency_ms", None)
    return value


def stable_retrieval(result: dict) -> dict:
    value = copy.deepcopy(result)
    value.pop("latency_ms", None)
    return value


def main() -> None:
    retriever = DenseRetrieverV1()
    cases = []
    all_pass = True
    for case_id, query in QUERIES:
        retrieved = retriever.retrieve(query, case_id)
        evidence_first = evaluate_evidence(query, case_id, retrieved)
        evidence_second = evaluate_evidence(query, case_id, copy.deepcopy(retrieved))
        checks = {
            "retrieval_error_is_null": retrieved.get("error") is None,
            "retriever_version_match": retrieved.get("retriever_version") == "RAG_RETRIEVAL_V1",
            "corpus_version_match": retrieved.get("corpus_version") == "KNOWLEDGE_BASE_V1",
            "top5_count_is_five": len(retrieved.get("ordered_top5_chunks", [])) == 5,
            "evidence_error_is_null": evidence_first.get("error") is None,
            "evidence_version_match": evidence_first.get("evidence_sufficiency_version") == "EVIDENCE_SUFFICIENCY_V1",
            "output_schema_exact": set(evidence_first) == OUTPUT_FIELDS,
            "evidence_repeatability_excluding_latency": stable_evidence(evidence_first) == stable_evidence(evidence_second),
        }
        passed = all(checks.values())
        all_pass = all_pass and passed
        cases.append(
            {
                "case_id": case_id,
                "query": query,
                "checks": checks,
                "passed": passed,
                "retrieved_chunk_ids": retrieved.get("chunk_ids", []),
                "retrieved_source_ids": retrieved.get("source_ids", []),
                "retrieval_scores": [round(score, 8) for score in retrieved.get("scores", [])],
                "evidence_decision": evidence_first["decision"],
                "policy_signal": evidence_first["policy_signal"],
                "reason_codes": evidence_first["reason_codes"],
                "supporting_chunk_ids": evidence_first["supporting_chunk_ids"],
                "supporting_source_ids": evidence_first["supporting_source_ids"],
            }
        )

    repeat_case_id, repeat_query = QUERIES[0]
    repeat_first = retriever.retrieve(repeat_query, repeat_case_id)
    repeat_second = retriever.retrieve(repeat_query, repeat_case_id)
    retrieval_repeatable = stable_retrieval(repeat_first) == stable_retrieval(repeat_second)
    all_pass = all_pass and retrieval_repeatable
    payload = {
        "artifact": "Evidence Sufficiency Runtime V1 interface integration test",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "chain": "query -> RAG Retrieval V1 Top-5 -> Evidence Sufficiency Runtime V1 -> structured decision",
        "answer_generation_called": False,
        "citation_runtime_called": False,
        "case_count": len(cases),
        "cases": cases,
        "retrieval_repeatability_excluding_latency": retrieval_repeatable,
        "overall_status": "PASS" if all_pass else "FAIL",
    }
    target = ROOT / "evaluation" / "evidence_sufficiency" / "v1" / "tests" / "integration_results.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
