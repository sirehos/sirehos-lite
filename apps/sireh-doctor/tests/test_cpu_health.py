"""Regression tests for CPU thermal and throttling assessments."""

import unittest

from sireh_doctor.diagnostics.hardware_health import (
    assess_cpu_thermal,
    assess_cpu_throttling,
)


class CpuHealthTests(unittest.TestCase):

    def thermal(self, current=None, critical=None, alarm=None):
        return assess_cpu_thermal({
            "thermal_evidence": {
                "package_c": current,
                "critical_c": critical,
                "critical_alarm": alarm,
            }
        })

    def throttling(self, counters):
        return assess_cpu_throttling({
            "thermal_evidence": {
                "throttle_counts": counters,
            }
        })

    def test_normal_temperature(self):
        result = self.thermal(50, 105)
        self.assertEqual(result["status"], "PASS")

    def test_twenty_degree_boundary(self):
        self.assertEqual(
            self.thermal(85, 105)["status"], "PASS"
        )

    def test_low_thermal_headroom(self):
        self.assertEqual(
            self.thermal(90, 105)["status"], "WARN"
        )

    def test_critical_temperature(self):
        self.assertEqual(
            self.thermal(105, 105)["status"], "FAIL"
        )

    def test_above_critical_temperature(self):
        self.assertEqual(
            self.thermal(110, 105)["status"], "FAIL"
        )

    def test_critical_alarm(self):
        result = self.thermal(50, 105, alarm=True)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("alarm", result["summary"])

    def test_missing_temperature(self):
        self.assertEqual(
            self.thermal(None, 105)["status"], "UNKNOWN"
        )

    def test_missing_critical_limit(self):
        self.assertEqual(
            self.thermal(50, None)["status"], "UNKNOWN"
        )

    def test_invalid_critical_limit(self):
        self.assertEqual(
            self.thermal(50, 0)["status"], "UNKNOWN"
        )

    def test_zero_throttling_counters(self):
        result = self.throttling({
            "cpu0": {
                "core": 0,
                "package": 0,
            }
        })
        self.assertEqual(result["status"], "PASS")

    def test_historical_throttling_event(self):
        result = self.throttling({
            "cpu0": {
                "core": 2,
                "package": 0,
            }
        })
        self.assertEqual(result["status"], "WARN")
        self.assertIn("earlier events", result["summary"])

    def test_missing_throttling_counters(self):
        self.assertEqual(
            self.throttling({})["status"], "UNKNOWN"
        )

    def test_negative_counter_ignored(self):
        self.assertEqual(
            self.throttling({
                "cpu0": {"core": -1}
            })["status"],
            "UNKNOWN",
        )


    def test_invalid_temperature_values(self):
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
            True,
            False,
        ):
            with self.subTest(value=repr(value)):
                result = self.thermal(value, 105)
                self.assertEqual(result["status"], "UNKNOWN")

    def test_invalid_critical_limit_values(self):
        for value in (
            float("nan"),
            float("inf"),
            float("-inf"),
            True,
            False,
        ):
            with self.subTest(value=repr(value)):
                result = self.thermal(50, value)
                self.assertEqual(result["status"], "UNKNOWN")

    def test_boolean_throttling_counter(self):
        result = self.throttling({
            "cpu0": {"core": True}
        })
        self.assertEqual(result["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
