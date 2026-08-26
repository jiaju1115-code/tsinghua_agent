import unittest

try:
    from .evidence_validator import EvidenceStatus, validate_payload
except ImportError:  # Support direct execution from the v2 directory.
    from evidence_validator import EvidenceStatus, validate_payload


class EvidenceValidatorTests(unittest.TestCase):
    def test_sufficient(self):
        result = validate_payload(
            {
                "status": "SUFFICIENT",
                "requested_points": ["steps"],
                "supported_points": ["steps"],
                "missing_points": [],
                "evidence_ids": ["e1"],
                "reason_codes": [],
            },
            ["e1"],
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.status, EvidenceStatus.SUFFICIENT)

    def test_partial(self):
        result = validate_payload(
            {
                "status": "PARTIAL",
                "requested_points": ["eligibility", "deadline"],
                "supported_points": ["eligibility"],
                "missing_points": ["deadline"],
                "evidence_ids": ["e1"],
                "reason_codes": ["REQUESTED_ATTRIBUTE_MISSING"],
            },
            ["e1"],
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.missing_points, ("deadline",))

    def test_invalid_json_fails_closed(self):
        result = validate_payload("not-json", ["e1"])
        self.assertFalse(result.valid)
        self.assertEqual(result.status, EvidenceStatus.INSUFFICIENT)

    def test_unknown_evidence_fails_closed(self):
        result = validate_payload(
            {
                "status": "SUFFICIENT",
                "requested_points": ["place"],
                "supported_points": ["place"],
                "missing_points": [],
                "evidence_ids": ["invented"],
                "reason_codes": [],
            },
            ["real"],
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason_codes, ("VALIDATOR_UNKNOWN_EVIDENCE_ID",))

    def test_insufficient_cannot_claim_support(self):
        result = validate_payload(
            {
                "status": "INSUFFICIENT",
                "requested_points": ["today_hours"],
                "supported_points": ["today_hours"],
                "missing_points": [],
                "evidence_ids": ["e1"],
                "reason_codes": [],
            },
            ["e1"],
        )
        self.assertFalse(result.valid)


if __name__ == "__main__":
    unittest.main()
