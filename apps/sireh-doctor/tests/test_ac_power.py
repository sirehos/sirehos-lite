"""Regression tests for external-power assessment."""

import unittest

from sireh_doctor.diagnostics.hardware_health import assess_ac_power


class ACPowerTests(unittest.TestCase):

    def assess(self, supplies):
        return assess_ac_power({
            "power": {"supplies": supplies}
        })

    def test_connected_adapter(self):
        result = self.assess([
            {"type": "Mains", "online": "1"}
        ])
        self.assertEqual(result["status"], "PASS")

    def test_disconnected_adapter(self):
        result = self.assess([
            {"type": "Mains", "online": "0"}
        ])
        self.assertEqual(result["status"], "INFO")

    def test_integer_connected(self):
        result = self.assess([
            {"type": "Mains", "online": 1}
        ])
        self.assertEqual(result["status"], "PASS")

    def test_integer_disconnected(self):
        result = self.assess([
            {"type": "Mains", "online": 0}
        ])
        self.assertEqual(result["status"], "INFO")

    def test_missing_adapter(self):
        self.assertEqual(
            self.assess([])["status"], "UNKNOWN"
        )

    def test_missing_online_reading(self):
        self.assertEqual(
            self.assess([
                {"type": "Mains"}
            ])["status"],
            "UNKNOWN",
        )

    def test_invalid_online_reading(self):
        self.assertEqual(
            self.assess([
                {"type": "Mains", "online": "invalid"}
            ])["status"],
            "UNKNOWN",
        )

    def test_boolean_online_reading(self):
        self.assertEqual(
            self.assess([
                {"type": "Mains", "online": True}
            ])["status"],
            "UNKNOWN",
        )

    def test_battery_not_treated_as_adapter(self):
        self.assertEqual(
            self.assess([
                {"type": "Battery", "online": "1"}
            ])["status"],
            "UNKNOWN",
        )

    def test_multiple_adapters_one_connected(self):
        result = self.assess([
            {"type": "Mains", "online": "0"},
            {"type": "Mains", "online": "1"},
        ])
        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
