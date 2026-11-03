"""Regression tests for cooling-fan assessment."""

import unittest

from sireh_doctor.diagnostics.hardware_health import assess_cooling_fan


class CoolingFanTests(unittest.TestCase):

    def assess(self, fans):
        return assess_cooling_fan({
            "fan": {"fans": fans}
        })

    def test_rotating_fan(self):
        result = self.assess([{"rpm": 2500}])
        self.assertEqual(result["status"], "PASS")
        self.assertIn("2,500 RPM", result["summary"])

    def test_zero_rpm_is_not_failure(self):
        result = self.assess([{"rpm": 0}])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("0 RPM", result["summary"])

    def test_missing_fan_sensors(self):
        result = self.assess([])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_missing_rpm(self):
        result = self.assess([{"name": "fan1"}])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_multiple_rotating_fans(self):
        result = self.assess([
            {"rpm": 1800},
            {"rpm": 3200},
        ])
        self.assertEqual(result["status"], "PASS")
        self.assertIn("3,200 RPM", result["summary"])

    def test_mixed_rotating_and_stopped(self):
        result = self.assess([
            {"rpm": 0},
            {"rpm": 2100},
        ])
        self.assertEqual(result["status"], "PASS")

    def test_all_fans_stopped(self):
        result = self.assess([
            {"rpm": 0},
            {"rpm": 0},
        ])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_negative_rpm(self):
        result = self.assess([{"rpm": -100}])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_boolean_rpm(self):
        result = self.assess([{"rpm": True}])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_string_rpm(self):
        result = self.assess([{"rpm": "2500"}])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_invalid_sensor_with_valid_sensor(self):
        result = self.assess([
            {"rpm": -1},
            {"rpm": 1500},
        ])
        self.assertEqual(result["status"], "PASS")

    def test_rotation_does_not_certify_cooling(self):
        result = self.assess([{"rpm": 2000}])
        self.assertIn(
            "Cooling effectiveness",
            result["recommendation"],
        )


if __name__ == "__main__":
    unittest.main()
