"""Regression tests for conservative SMART health interpretation."""

import unittest

from sireh_doctor.diagnostics.storage_smart_health import assess_smart


def available(data):
    return {"status": "AVAILABLE", "data": data}


class SmartHealthTests(unittest.TestCase):

    def test_sata_overall_pass(self):
        result = assess_smart(available({
            "smart_status": {"passed": True}
        }))
        self.assertEqual(result["status"], "PASS")

    def test_sata_overall_failure(self):
        result = assess_smart(available({
            "smart_status": {"passed": False}
        }))
        self.assertEqual(result["status"], "FAIL")

    def test_nvme_critical_warning(self):
        result = assess_smart(available({
            "nvme_smart_health_information_log": {
                "critical_warning": 1
            }
        }))
        self.assertEqual(result["status"], "FAIL")

    def test_nvme_zero_warning(self):
        result = assess_smart(available({
            "nvme_smart_health_information_log": {
                "critical_warning": 0
            }
        }))
        self.assertEqual(result["status"], "PASS")

    def test_nvme_media_errors(self):
        result = assess_smart(available({
            "nvme_smart_health_information_log": {
                "critical_warning": 0,
                "media_errors": 4,
            }
        }))
        self.assertEqual(result["status"], "WARN")
        self.assertEqual(
            result["metrics"]["nvme_media_errors"], 4
        )

    def test_nvme_endurance_threshold(self):
        result = assess_smart(available({
            "nvme_smart_health_information_log": {
                "critical_warning": 0,
                "percentage_used": 100,
            }
        }))
        self.assertEqual(result["status"], "WARN")

    def test_nvme_endurance_below_threshold(self):
        result = assess_smart(available({
            "nvme_smart_health_information_log": {
                "critical_warning": 0,
                "percentage_used": 50,
            }
        }))
        self.assertEqual(result["status"], "PASS")

    def test_failure_overrides_warning(self):
        result = assess_smart(available({
            "smart_status": {"passed": False},
            "nvme_smart_health_information_log": {
                "critical_warning": 0,
                "media_errors": 8,
            },
        }))
        self.assertEqual(result["status"], "FAIL")

    def test_warning_overrides_pass(self):
        result = assess_smart(available({
            "smart_status": {"passed": True},
            "nvme_smart_health_information_log": {
                "media_errors": 2,
            },
        }))
        self.assertEqual(result["status"], "WARN")

    def test_permission_required(self):
        result = assess_smart({
            "status": "PERMISSION_REQUIRED",
            "error": "Administrator permission required",
            "data": None,
        })
        self.assertEqual(result["status"], "UNKNOWN")

    def test_invalid_collection(self):
        self.assertEqual(
            assess_smart(None)["status"], "UNKNOWN"
        )

    def test_invalid_data(self):
        self.assertEqual(
            assess_smart(available([]))["status"], "UNKNOWN"
        )

    def test_missing_indicators(self):
        self.assertEqual(
            assess_smart(available({}))["status"], "UNKNOWN"
        )

    def test_boolean_media_errors_rejected(self):
        result = assess_smart(available({
            "nvme_smart_health_information_log": {
                "media_errors": True
            }
        }))
        self.assertEqual(result["status"], "UNKNOWN")

    def test_negative_critical_warning_rejected(self):
        result = assess_smart(available({
            "nvme_smart_health_information_log": {
                "critical_warning": -1
            }
        }))
        self.assertEqual(result["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
