"""Regression tests for Hardware Doctor summary logic."""

import unittest

from sireh_doctor.diagnostics.hardware_health import summarize_findings


class HardwareSummaryTests(unittest.TestCase):

    def test_empty_findings(self):
        result = summarize_findings([])

        self.assertEqual(result["total_checks"], 0)
        self.assertEqual(
            result["counts"],
            {
                "PASS": 0,
                "WARN": 0,
                "FAIL": 0,
                "INFO": 0,
                "UNKNOWN": 0,
            },
        )

    def test_all_supported_statuses(self):
        findings = [
            {"status": "PASS"},
            {"status": "PASS"},
            {"status": "WARN"},
            {"status": "FAIL"},
            {"status": "INFO"},
            {"status": "UNKNOWN"},
        ]

        result = summarize_findings(findings)

        self.assertEqual(result["total_checks"], 6)
        self.assertEqual(result["counts"]["PASS"], 2)
        self.assertEqual(result["counts"]["WARN"], 1)
        self.assertEqual(result["counts"]["FAIL"], 1)
        self.assertEqual(result["counts"]["INFO"], 1)
        self.assertEqual(result["counts"]["UNKNOWN"], 1)

    def test_unrecognized_status_is_unknown(self):
        result = summarize_findings([
            {"status": "UNSUPPORTED"},
            {},
        ])

        self.assertEqual(result["total_checks"], 2)
        self.assertEqual(result["counts"]["UNKNOWN"], 2)

    def test_no_overall_health_certification(self):
        result = summarize_findings([{"status": "PASS"}])

        self.assertFalse(result["overall_health_certified"])
        self.assertEqual(
            result["scope"], "IMPLEMENTED_CHECKS_ONLY"
        )


if __name__ == "__main__":
    unittest.main()
