"""Regression tests for read-only Repair Advisor."""

import unittest

from sireh_doctor.diagnostics.repair_advisor import build_plan


class RepairAdvisorTests(unittest.TestCase):

    def test_empty_results_remain_unassessed(self):
        plan = build_plan({})
        self.assertEqual(plan["assessed_sources"], 0)
        self.assertEqual(len(plan["unassessed_sources"]), 6)
        self.assertEqual(plan["findings"], [])

    def test_smart_assessment_is_normalized(self):
        plan = build_plan({
            "storage": {
                "/dev/example": {
                    "collection": {"status": "AVAILABLE"},
                    "assessment": {
                        "status": "WARN",
                        "summary": "Pending sectors reported",
                        "recommendation": "Protect important data",
                    },
                }
            }
        })
        self.assertEqual(plan["assessed_sources"], 1)
        self.assertEqual(plan["findings"][0]["status"], "WARN")
        self.assertEqual(
            plan["findings"][0]["source"], "Storage Doctor"
        )

    def test_priority_and_unknown(self):
        plan = build_plan({
            "osboot": {
                "missing": {
                    "status": "UNKNOWN",
                    "summary": "No evidence",
                },
                "boot": {
                    "status": "FAIL",
                    "summary": "Boot failure evidence",
                },
            },
            "security": {
                "firewall": {
                    "status": "PASS",
                    "summary": "Available",
                }
            },
        })
        self.assertEqual(
            [item["status"] for item in plan["findings"]],
            ["FAIL", "UNKNOWN"]
        )

    def test_data_rescue_discovery_not_health(self):
        plan = build_plan({
            "rescue": {
                "discovery": {
                    "devices": [{"rescue_eligible": False}]
                }
            }
        })
        self.assertIn("Data Rescue", plan["unassessed_sources"])
        self.assertEqual(plan["findings"], [])

    def test_hardware_finding(self):
        plan = build_plan({
            "hardware": {
                "thermal": {
                    "status": "WARN",
                    "summary": "Reduced thermal headroom",
                }
            }
        })
        self.assertEqual(plan["assessed_sources"], 1)
        self.assertEqual(
            plan["findings"][0]["source"], "Hardware Doctor"
        )


if __name__ == "__main__":
    unittest.main()
