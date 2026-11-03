"""Regression tests for battery capacity assessment."""

import unittest

from sireh_doctor.diagnostics.hardware_health import assess_battery


class BatteryHealthTests(unittest.TestCase):

    def check_status(self, health, expected):
        finding = assess_battery({
            "name": "TESTBAT",
            "health_percent": health,
        })

        self.assertEqual(finding["status"], expected)
        self.assertEqual(finding["component"], "TESTBAT")
        self.assertEqual(
            finding["check"], "Battery capacity retention"
        )

        return finding

    def test_healthy_capacity(self):
        self.check_status(100, "PASS")
        self.check_status(85, "PASS")

    def test_pass_boundary(self):
        self.check_status(80, "PASS")
        self.check_status(79.9, "WARN")

    def test_reduced_capacity(self):
        self.check_status(74.5, "WARN")
        self.check_status(62.4, "WARN")

    def test_low_capacity(self):
        finding = self.check_status(45, "WARN")
        self.assertIn("substantially reduced", finding["summary"])

    def test_sixty_percent_boundary(self):
        self.check_status(60, "WARN")
        finding = self.check_status(59.9, "WARN")
        self.assertIn("substantially reduced", finding["summary"])

    def test_missing_capacity(self):
        self.check_status(None, "UNKNOWN")

    def test_invalid_capacity(self):
        for value in (-1, 121, "85", True, float("nan")):
            with self.subTest(value=repr(value)):
                self.check_status(value, "UNKNOWN")

    def test_above_design_capacity(self):
        self.check_status(105, "PASS")
        self.check_status(120, "PASS")

    def test_low_capacity_is_not_safety_failure(self):
        finding = self.check_status(30, "WARN")
        self.assertIn(
            "does not establish a safety fault",
            finding["recommendation"],
        )


if __name__ == "__main__":
    unittest.main()
