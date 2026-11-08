"""SD-10 report regression tests."""

import unittest

from sireh_doctor.diagnostics.health_report import (
    build_report, render_report,
)


class HealthReportTests(unittest.TestCase):
    def test_no_results_are_not_healthy(self):
        report = build_report({}, "2026-11-08T18:00:00+01:00")
        self.assertEqual(report["assessed"], 0)
        self.assertEqual(len(report["unassessed"]), 6)
        self.assertEqual(report["counts"]["PASS"], 0)
        self.assertIn(
            "NOT ASSESSED", render_report(report)
        )

    def test_priority_and_storage_assessment(self):
        report = build_report({
            "hardware": {
                "cpu": {"status": "PASS", "summary": "OK"},
                "memory": {
                    "status": "WARN",
                    "summary": "Review memory",
                },
            },
            "storage": {
                "disk0": {
                    "assessment": {
                        "status": "FAIL",
                        "summary": "Drive problem",
                    },
                },
            },
        })
        self.assertEqual(report["counts"]["FAIL"], 1)
        self.assertEqual(report["counts"]["WARN"], 1)
        self.assertEqual(report["counts"]["PASS"], 1)
        self.assertEqual(
            report["sections"][1]["status"], "FAIL"
        )

    def test_unknown_is_not_pass(self):
        report = build_report({
            "security": {
                "ssh": {
                    "status": "ERROR",
                    "message": "Unavailable",
                },
            },
        })
        self.assertEqual(report["counts"]["UNKNOWN"], 1)
        self.assertEqual(report["counts"]["PASS"], 0)

    def test_text_and_markdown(self):
        report = build_report({})
        self.assertIn(
            "EXECUTIVE SUMMARY", render_report(report)
        )
        self.assertTrue(
            render_report(report, markdown=True).startswith("# ")
        )


if __name__ == "__main__":
    unittest.main()
