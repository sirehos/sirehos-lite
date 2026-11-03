"""Regression tests for available-memory assessment."""

import unittest

from sireh_doctor.diagnostics.hardware_health import assess_memory


class MemoryHealthTests(unittest.TestCase):

    def assess(self, total, available):
        return assess_memory({
            "memory": {
                "total": total,
                "available": available,
            }
        })

    def test_normal_memory(self):
        result = self.assess("8000000 kB", "5600000 kB")
        self.assertEqual(result["status"], "PASS")
        self.assertIn("70.0%", result["summary"])

    def test_twenty_percent_boundary(self):
        self.assertEqual(
            self.assess("1000 kB", "200 kB")["status"],
            "PASS",
        )

    def test_below_twenty_percent(self):
        self.assertEqual(
            self.assess("1000 kB", "199 kB")["status"],
            "WARN",
        )

    def test_ten_percent_boundary(self):
        result = self.assess("1000 kB", "100 kB")
        self.assertEqual(result["status"], "WARN")
        self.assertIn("reduced", result["recommendation"])

    def test_below_ten_percent(self):
        result = self.assess("1000 kB", "99 kB")
        self.assertEqual(result["status"], "WARN")
        self.assertIn("Very little", result["recommendation"])

    def test_zero_available_memory(self):
        self.assertEqual(
            self.assess("1000 kB", "0 kB")["status"],
            "WARN",
        )

    def test_missing_memory(self):
        self.assertEqual(
            self.assess(None, None)["status"],
            "UNKNOWN",
        )

    def test_zero_total_memory(self):
        self.assertEqual(
            self.assess("0 kB", "0 kB")["status"],
            "UNKNOWN",
        )

    def test_available_exceeds_total(self):
        self.assertEqual(
            self.assess("1000 kB", "1200 kB")["status"],
            "UNKNOWN",
        )

    def test_negative_available_memory(self):
        self.assertEqual(
            self.assess("1000 kB", "-1 kB")["status"],
            "UNKNOWN",
        )

    def test_invalid_memory_string(self):
        self.assertEqual(
            self.assess("invalid", "500 kB")["status"],
            "UNKNOWN",
        )

    def test_no_ram_integrity_claim(self):
        result = self.assess("1000 kB", "700 kB")
        self.assertIn(
            "does not test RAM hardware integrity",
            result["recommendation"],
        )


if __name__ == "__main__":
    unittest.main()
