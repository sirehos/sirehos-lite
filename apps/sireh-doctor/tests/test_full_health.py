"""SD-01 pure diagnostic aggregation regression tests."""

import unittest
from unittest.mock import patch

from sireh_doctor.diagnostics.full_health import (
    AREAS, outcome, summarize, tasks, run_task,
)


class FullHealthTests(unittest.TestCase):
    def test_all_required_areas_present(self):
        self.assertEqual(len(AREAS), 5)
        self.assertEqual(
            {area for area, _, _ in tasks()},
            {key for _, key in AREAS},
        )

    def test_empty_is_not_assessed(self):
        counts, areas = summarize({})
        self.assertEqual(sum(counts.values()), 0)
        self.assertTrue(
            all(s == "NOT ASSESSED" for s in areas.values())
        )

    def test_unknown_not_pass(self):
        counts, areas = summarize({
            "storage": {
                "inventory": outcome(
                    "UNKNOWN", "SMART not assessed."
                )
            }
        })
        self.assertEqual(counts["PASS"], 0)
        self.assertEqual(areas["Storage Doctor"], "UNKNOWN")

    def test_severity_priority(self):
        counts, areas = summarize({
            "crash": {
                "a": outcome("PASS", "Available."),
                "b": outcome("WARN", "Needs review."),
                "c": outcome("FAIL", "Failure."),
            }
        })
        self.assertEqual(areas["Crash Detective"], "FAIL")
        self.assertEqual(counts["FAIL"], 1)

    @patch(
        "sireh_doctor.diagnostics.full_health."
        "storage_inventory.collect_storage_inventory"
    )
    def test_inventory_never_certifies_smart(self, mock_inventory):
        mock_inventory.return_value = {
            "status": "AVAILABLE",
            "devices": [{"path": "/dev/sda"}],
        }
        result = run_task("storage", "inventory")
        self.assertEqual(
            result["inventory"]["status"], "UNKNOWN"
        )
        self.assertIn(
            "SMART", result["inventory"]["summary"]
        )
