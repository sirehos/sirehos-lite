"""Regression tests for individual hardware check dispatch."""

import unittest

from sireh_doctor.diagnostics.hardware_checks import (
    CHECKS,
    run_check,
)


class HardwareCheckDispatcherTests(unittest.TestCase):

    def setUp(self):
        self.data = {
            "cpu": {},
            "memory": {},
            "temperature": {},
            "thermal_evidence": {},
            "fan": {"fans": [{"rpm": 2200}]},
            "power": {
                "supplies": [
                    {
                        "type": "Mains",
                        "name": "AC",
                        "online": "1",
                    },
                    {
                        "type": "Battery",
                        "name": "BAT0",
                        "health_percent": 90.0,
                    },
                    {
                        "type": "Battery",
                        "name": "BAT1",
                        "health_percent": 65.0,
                    },
                ]
            },
        }

    def test_five_standard_checks_registered(self):
        self.assertEqual(
            set(CHECKS),
            {
                "cpu_thermal",
                "cpu_throttling",
                "memory",
                "cooling_fan",
                "ac_power",
            },
        )

    def test_cpu_thermal_dispatch(self):
        result = run_check("cpu_thermal", self.data)
        self.assertEqual(result["component"], "CPU")

    def test_cpu_throttling_dispatch(self):
        result = run_check("cpu_throttling", self.data)
        self.assertIn("status", result)

    def test_memory_dispatch(self):
        result = run_check("memory", self.data)
        self.assertIn("status", result)

    def test_cooling_fan_dispatch(self):
        result = run_check("cooling_fan", self.data)
        self.assertEqual(result["status"], "PASS")

    def test_ac_power_dispatch(self):
        result = run_check("ac_power", self.data)
        self.assertEqual(result["status"], "PASS")

    def test_bat0_isolation(self):
        result = run_check("battery:BAT0", self.data)
        self.assertEqual(result["component"], "BAT0")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["measured_percent"], 90.0)

    def test_bat1_isolation(self):
        result = run_check("battery:BAT1", self.data)
        self.assertEqual(result["component"], "BAT1")
        self.assertEqual(result["status"], "WARN")
        self.assertEqual(result["measured_percent"], 65.0)

    def test_missing_battery(self):
        result = run_check("battery:BAT9", self.data)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["component"], "BAT9")

    def test_invalid_check_id(self):
        with self.assertRaises(ValueError):
            run_check("unsupported_check", self.data)


if __name__ == "__main__":
    unittest.main()
