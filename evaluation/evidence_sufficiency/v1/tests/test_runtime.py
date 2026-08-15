from __future__ import annotations

import copy
import unittest

from src.evidence_sufficiency_v1 import evaluate_evidence
from src.evidence_sufficiency_v1.schema import OUTPUT_FIELDS


FILLER = "\u672c\u6bb5\u5185\u5bb9\u7528\u4e8e\u6784\u9020\u7a33\u5b9a\u7684\u6d4b\u8bd5\u8bc1\u636e\u957f\u5ea6\uff0c\u4e0d\u8868\u793a\u989d\u5916\u4e8b\u5b9e\u6216\u9690\u542b\u652f\u6301\u3002"


def retrieval(*texts: str) -> dict:
    padded = list(texts) + ["\u6821\u56ed\u7eff\u5316\u548c\u666f\u89c2\u4ecb\u7ecd\u3002" + FILLER] * (5 - len(texts))
    return {
        "query": "fixture",
        "case_id": "fixture",
        "retriever_version": "RAG_RETRIEVAL_V1",
        "corpus_version": "KNOWLEDGE_BASE_V1",
        "ordered_top5_chunks": [
            {
                "rank": index,
                "source_id": f"SRC{index}",
                "chunk_id": f"CHK{index}",
                "score": 1.0 / index,
                "title": "\u6e05\u534e\u5927\u5b66\u670d\u52a1\u4fe1\u606f" if index == 1 else "\u6821\u56ed\u4fe1\u606f",
                "url": f"https://example.edu/{index}",
                "category": "service",
                "text": text if len(text) >= 40 else text + FILLER,
            }
            for index, text in enumerate(padded[:5], 1)
        ],
        "error": None,
    }


class RuntimeV1Tests(unittest.TestCase):
    def test_sufficient(self) -> None:
        result = evaluate_evidence(
            "\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f",
            "T-SUFFICIENT",
            retrieval("\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u6bcf\u5929 08:00-22:00\u3002"),
        )
        self.assertEqual(result["decision"], "SUFFICIENT")
        self.assertEqual(result["policy_signal"], "ALLOW_FULL_ANSWER")
        self.assertEqual(set(result), OUTPUT_FIELDS)
        self.assertIsNone(result["confidence"])
        self.assertFalse(result["diagnostics"]["semantic_entailment"])

    def test_partial_multi_point(self) -> None:
        result = evaluate_evidence(
            "\u6e05\u534e\u56fe\u4e66\u9986\u5982\u4f55\u501f\u4e66\u3001\u5f00\u653e\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f",
            "T-PARTIAL",
            retrieval("\u6e05\u534e\u56fe\u4e66\u9986\u501f\u4e66\u6d41\u7a0b\uff1a\u8bfb\u8005\u51ed\u6821\u56ed\u5361\u5728\u670d\u52a1\u53f0\u529e\u7406\u501f\u9605\u3002"),
        )
        self.assertEqual(result["decision"], "PARTIAL")
        self.assertEqual(result["policy_signal"], "ALLOW_PARTIAL_ANSWER")

    def test_insufficient_irrelevant(self) -> None:
        result = evaluate_evidence(
            "\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f",
            "T-IRRELEVANT",
            retrieval("\u5317\u4eac\u5929\u6c14\u548c\u57ce\u5e02\u4ea4\u901a\u7684\u4e00\u822c\u4ecb\u7ecd\u3002"),
        )
        self.assertEqual(result["decision"], "INSUFFICIENT")
        self.assertEqual(result["policy_signal"], "REQUIRE_REFUSAL")
        self.assertIn("EVIDENCE_IRRELEVANT", result["reason_codes"])

    def test_missing_requested_attribute(self) -> None:
        result = evaluate_evidence(
            "\u6e05\u534e\u5927\u5b66\u5956\u5b66\u91d1\u7533\u8bf7\u622a\u6b62\u65f6\u95f4\u662f\u4ec0\u4e48\uff1f",
            "T-MISSING-ATTR",
            retrieval("\u6e05\u534e\u5927\u5b66\u5956\u5b66\u91d1\u7533\u8bf7\u9762\u5411\u5728\u6821\u5b66\u751f\uff0c\u7533\u8bf7\u4eba\u9700\u6ee1\u8db3\u57fa\u672c\u8d44\u683c\u6761\u4ef6\u3002"),
        )
        self.assertNotEqual(result["decision"], "SUFFICIENT")
        self.assertIn("REQUESTED_ATTRIBUTE_MISSING", result["reason_codes"])
        self.assertIn("DEADLINE", {item["attribute"] for item in result["missing_requested_attributes"]})

    def test_optional_only_missing_does_not_block(self) -> None:
        result = evaluate_evidence(
            "\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u4ec0\u4e48\uff0c\u987a\u4fbf\u4ecb\u7ecd\u9986\u53f2",
            "T-OPTIONAL",
            retrieval("\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u6bcf\u5929 08:00-22:00\u3002"),
        )
        self.assertEqual(result["decision"], "SUFFICIENT")
        self.assertTrue(result["optional_information"])

    def test_empty_evidence_fails_closed(self) -> None:
        result = evaluate_evidence("\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\uff1f", "T-EMPTY", retrieval("", "", "", "", ""))
        self.assertEqual(result["decision"], "INSUFFICIENT")
        self.assertIn("NO_USABLE_EVIDENCE", result["reason_codes"])

    def test_conflicting_values_fail_closed(self) -> None:
        result = evaluate_evidence(
            "\u6e05\u534e\u6253\u5370\u670d\u52a1\u8d39\u7528\u662f\u591a\u5c11\u94b1\uff1f",
            "T-CONFLICT",
            retrieval(
                "\u6e05\u534e\u6253\u5370\u670d\u52a1\u8d39\u7528\u662f 100 \u5143\u3002" + FILLER,
                "\u6e05\u534e\u6253\u5370\u670d\u52a1\u8d39\u7528\u662f 200 \u5143\u3002" + FILLER,
            ),
        )
        self.assertEqual(result["decision"], "INSUFFICIENT")
        self.assertIn("EVIDENCE_CONFLICT", result["reason_codes"])

    def test_malformed_input_fails_closed(self) -> None:
        result = evaluate_evidence(
            "query",
            "T-MALFORMED",
            {
                "retriever_version": "RAG_RETRIEVAL_V1",
                "corpus_version": "KNOWLEDGE_BASE_V1",
                "ordered_top5_chunks": [{"rank": 1}],
                "error": None,
            },
        )
        self.assertEqual(result["decision"], "INSUFFICIENT")
        self.assertIn("INPUT_SCHEMA_INVALID", result["reason_codes"])

    def test_version_mismatch_fails_closed(self) -> None:
        value = retrieval("\u6e05\u534e\u56fe\u4e66\u9986\u4fe1\u606f\u3002")
        value["retriever_version"] = "RAG_RETRIEVAL_V0"
        result = evaluate_evidence("\u6e05\u534e\u56fe\u4e66\u9986\u4fe1\u606f\uff1f", "T-VERSION", value)
        self.assertEqual(result["decision"], "INSUFFICIENT")
        self.assertIn("VERSION_MISMATCH", result["reason_codes"])

    def test_repeatability_excluding_latency(self) -> None:
        value = retrieval("\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\u662f\u6bcf\u5929 08:00-22:00\u3002")
        first = evaluate_evidence("\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\uff1f", "T-REPEAT", value)
        second = evaluate_evidence("\u6e05\u534e\u56fe\u4e66\u9986\u5f00\u653e\u65f6\u95f4\uff1f", "T-REPEAT", copy.deepcopy(value))
        first.pop("latency_ms")
        second.pop("latency_ms")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
